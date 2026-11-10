"""Issue Report feature — flag a photo as wrongly defined with corrected
Position/Type/Color values, and generate a Markdown report listing issues
found in the pack: manually flagged photos, auto-detected Position / Pack
Type mismatches, orphaned files, and broken references.

Flagged photos store their correction on the photo dict:
    photo["issue_flag"] = True
    photo["issue_note"] = "free-text description of what's wrong"
    photo["issue_correction"] = {"position": "...", "type": "...", "color": "..."}

Export (``import_export._write_pack_ini``) writes the corrected values instead
of the original ones for any photo with ``issue_flag`` set.
"""

import datetime
import os

from PyQt6.QtWidgets import (  # type: ignore
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QComboBox,
    QPlainTextEdit, QPushButton, QCheckBox, QLabel,
)

from app_debug import dlog as _dlog
from modules.position_rules import position_mismatch

_CORRECTION_KEYS = ("position", "type", "color")


def effective_photo_traits(photo: dict) -> dict:
    """Return photo's position/type/color, replaced by its issue correction
    (when flagged) for export purposes. Original photo dict is left untouched."""
    traits = {k: photo.get(k) for k in _CORRECTION_KEYS}
    if photo.get("issue_flag"):
        correction = photo.get("issue_correction") or {}
        for k in _CORRECTION_KEYS:
            if correction.get(k):
                traits[k] = correction[k]
    return traits


class FlagWrongDialog(QDialog):
    """Lets the user mark a photo as wrongly defined and provide corrected
    Position/Type/Color values plus a free-text note."""

    def __init__(self, parent, photo: dict, positions: list, types: list, colors: list) -> None:
        super().__init__(parent)
        self.setWindowTitle("Flag Photo as Wrong")
        self.setMinimumWidth(420)
        self._photo = photo

        layout = QVBoxLayout(self)

        self._chk_flag = QCheckBox("This photo is wrongly defined")
        self._chk_flag.setChecked(bool(photo.get("issue_flag")))
        layout.addWidget(self._chk_flag)

        form = QFormLayout()
        correction = photo.get("issue_correction") or {}

        self._cmb_position = QComboBox()
        self._cmb_position.setEditable(True)
        for val, label in positions:
            self._cmb_position.addItem(label, val)
        self._set_combo_value(self._cmb_position, positions,
                              correction.get("position") or photo.get("position", ""))

        self._cmb_type = QComboBox()
        self._cmb_type.setEditable(True)
        self._cmb_type.addItems(types)
        self._set_plain_combo_value(self._cmb_type, correction.get("type") or photo.get("type", ""))

        self._cmb_color = QComboBox()
        self._cmb_color.setEditable(True)
        self._cmb_color.addItems(colors)
        self._set_plain_combo_value(self._cmb_color, correction.get("color") or photo.get("color", ""))

        form.addRow("Corrected Position:", self._cmb_position)
        form.addRow("Corrected Type:", self._cmb_type)
        form.addRow("Corrected Color/Special:", self._cmb_color)
        layout.addLayout(form)

        layout.addWidget(QLabel("Note (what is wrong, for the issue report):"))
        self._txt_note = QPlainTextEdit()
        self._txt_note.setPlainText(photo.get("issue_note", ""))
        self._txt_note.setMinimumHeight(80)
        layout.addWidget(self._txt_note)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.setDefault(True)
        btn_cancel = QPushButton("Cancel")
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

    @staticmethod
    def _set_combo_value(combo: QComboBox, positions: list, value: str) -> None:
        idx = next((i for i, (v, _label) in enumerate(positions) if v == value), -1)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            combo.setCurrentIndex(-1)
            combo.setEditText(value)

    @staticmethod
    def _set_plain_combo_value(combo: QComboBox, value: str) -> None:
        idx = combo.findText(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            combo.setCurrentIndex(-1)
            combo.setEditText(value)

    def _resolve_position(self) -> str:
        cur_text = self._cmb_position.currentText().strip()
        idx = self._cmb_position.currentIndex()
        if idx >= 0:
            data = self._cmb_position.currentData()
            if data:
                return data
        return cur_text

    def apply_to_photo(self) -> None:
        """Write the dialog's state back onto the photo dict passed to __init__."""
        self._photo["issue_flag"] = self._chk_flag.isChecked()
        self._photo["issue_note"] = self._txt_note.toPlainText().strip()
        self._photo["issue_correction"] = {
            "position": self._resolve_position(),
            "type": self._cmb_type.currentText().strip(),
            "color": self._cmb_color.currentText().strip(),
        }
        _dlog("FlagWrongDialog.apply_to_photo",
              f"name={self._photo.get('name')!r} issue_flag={self._photo['issue_flag']}")


def detect_position_mismatches(pack_data: dict) -> list[dict]:
    """Return a list of {'name', 'position', 'expected_pack_type'} for photos
    whose Position value is reserved for a different Pack Type than the one
    currently set on the pack (e.g. a Love Lens position inside a Photos pack)."""
    pack_type = pack_data.get("pack_type", "photos")
    results: list[dict] = []
    for photo in pack_data.get("photos", []):
        position = photo.get("position", "")
        restriction = position_mismatch(position, pack_type)
        if restriction:
            results.append({
                "name": photo.get("name", "(unnamed)"),
                "position": position,
                "expected_pack_type": restriction,
            })
    return results


def detect_id_range_too_small(pack_data: dict) -> dict | None:
    """Return ``{'id_range', 'range_width', 'photo_count'}`` when the declared
    ``idrange`` is narrower than the pack's photo count (photos beyond the
    range would collide with the next pack's reserved IDs), else ``None``.

    Skipped for already-split multi-ini imports (``special_types_parts`` /
    ``special_colors_parts`` present): there, ``id_range`` only reflects the
    first part's range while photos span every part, each with its own
    (separately valid) range that isn't retained on ``pack_data``.
    """
    if "special_types_parts" in pack_data or "special_colors_parts" in pack_data:
        return None

    from modules.photo_registry import parse_id_range

    photo_count = len([p for p in pack_data.get("photos", []) if p.get("name")])
    if photo_count == 0:
        return None
    id_range = pack_data.get("id_range", "").strip()
    parsed = parse_id_range(id_range)
    if parsed is None:
        return None
    start, end = parsed
    range_width = end - start + 1
    if range_width < photo_count:
        return {"id_range": id_range, "range_width": range_width, "photo_count": photo_count}
    return None


def detect_rare_photo_cap_exceeded(pack_data: dict) -> dict | None:
    """Return ``{'rare_count', 'limit', 'photo_count', 'rare_photos'}`` when more
    photos are marked ``'rare'`` than the game allows (``ceil(photo_count / 10)``),
    else ``None``. ``rare_photos`` lists the name of every photo marked 'rare'.
    Only enforced by Snapshot! and Naughty Nightmares photo packs — mirrors
    ``modules.picture_widget.get_rare_photo_warning``."""
    if pack_data.get("game", "snapshot") not in ("snapshot", "naughtynightmares"):
        return None
    if pack_data.get("pack_type", "photos") != "photos":
        return None
    import math
    photos = pack_data.get("photos", [])
    total = len(photos)
    if total == 0:
        return None
    limit = math.ceil(total / 10)
    rare_photos = [p.get("name", "") for p in photos if p.get("color") == "rare"]
    rare_count = len(rare_photos)
    if rare_count <= limit:
        return None
    return {
        "rare_count": rare_count, "limit": limit, "photo_count": total,
        "rare_photos": rare_photos,
    }


def detect_id_conflicts(pack_data: dict) -> tuple[list[dict], bool]:
    """Return (conflicts, registry_available). Each conflict dict has
    'photo_id', 'photo_name', 'other_pack_name' — IDs this pack would assign
    that are already recorded in the photo ID registry under a different pack."""
    from modules.photo_registry import (
        default_registry_path, load_registry, compute_photo_ids, find_conflicts,
    )

    registry_path = default_registry_path()
    registry_available = os.path.exists(registry_path)

    game = pack_data.get("game", "snapshot")
    pack_name = pack_data.get("id", "").strip()
    id_range = pack_data.get("id_range", "").strip()
    photo_names = [p.get("name", "") for p in pack_data.get("photos", []) if p.get("name")]

    if not registry_available or not pack_name or not id_range:
        return [], registry_available

    photo_ids = compute_photo_ids(id_range, photo_names)
    if not photo_ids:
        return [], registry_available

    registry = load_registry(registry_path)
    raw_conflicts = find_conflicts(registry, game, pack_name, photo_ids)
    conflicts = [
        {
            "photo_id": c["photo_id"],
            "photo_name": c["photo_name"],
            "other_pack_name": c["pack_name"],
        }
        for c in raw_conflicts
    ]
    return conflicts, registry_available


def generate_issue_report_markdown(pack_data: dict) -> str:
    """Return a Markdown report covering all known pack issues: manually
    flagged photos, auto-detected Position / Pack Type mismatches, orphaned
    files on disk, and broken (missing) references."""
    from modules.warnings_tab import (
        _collect_referenced, _collect_disk_assets, _collect_broken, _collect_broken_scene_assets,
    )

    title = pack_data.get("title", "").strip('"') or pack_data.get("id", "pack")
    photos = pack_data.get("photos", [])
    flagged = [p for p in photos if p.get("issue_flag")]
    mismatches = detect_position_mismatches(pack_data)

    source_folder = pack_data.get("source_folder", "")
    orphaned: list[str] = []
    if source_folder and os.path.isdir(source_folder):
        referenced = _collect_referenced(pack_data)
        orphaned = sorted(
            os.path.basename(p) for p in _collect_disk_assets(source_folder)
            if os.path.splitext(os.path.basename(p))[0].lower() not in referenced
        )
    broken = sorted(set(_collect_broken(pack_data) + _collect_broken_scene_assets(pack_data, source_folder)))
    id_conflicts, registry_available = detect_id_conflicts(pack_data)
    range_too_small = detect_id_range_too_small(pack_data)
    rare_cap_exceeded = detect_rare_photo_cap_exceeded(pack_data)

    lines: list[str] = []
    lines.append(f"# Issue Report — {title}")
    lines.append("")
    lines.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Pack ID: `{pack_data.get('id', '')}`")
    lines.append(f"Game: `{pack_data.get('game', '')}`")
    lines.append(f"Pack Type: `{pack_data.get('pack_type', 'photos')}`")
    lines.append("")

    if mismatches:
        lines.append(f"## Position / Pack Type Mismatches ({len(mismatches)})")
        lines.append("")
        lines.append(
            "These photos use a Position value that is reserved for a different "
            "Pack Type and will not work correctly here:")
        lines.append("")
        lines.append("| Photo | Position | Reserved for Pack Type |")
        lines.append("|---|---|---|")
        for m in mismatches:
            lines.append(f"| {m['name']} | {m['position']} | {m['expected_pack_type']} |")
        lines.append("")

    if id_conflicts:
        lines.append(f"## ID Conflicts ({len(id_conflicts)})")
        lines.append("")
        lines.append(
            "These photo IDs are already assigned to a different pack in the photo ID registry:")
        lines.append("")
        lines.append("| Photo ID | This Pack's Photo | Already Used By Pack |")
        lines.append("|---|---|---|")
        for c in id_conflicts:
            lines.append(f"| {c['photo_id']} | {c['photo_name']} | {c['other_pack_name']} |")
        lines.append("")
    elif not registry_available:
        lines.append("## ID Conflicts")
        lines.append("")
        lines.append(
            "Skipped: no photo ID registry found. Run `tools\\scan_photo_registry.py` to build one.")
        lines.append("")

    if range_too_small:
        lines.append("## ID Range Too Small")
        lines.append("")
        lines.append(
            f"Declared `idrange={range_too_small['id_range']}` only covers "
            f"{range_too_small['range_width']} ID(s), but the pack has "
            f"{range_too_small['photo_count']} photo(s). Photos beyond the range will "
            "receive IDs that collide with whatever pack reserves the next range.")
        lines.append("")

    if rare_cap_exceeded:
        lines.append("## Rare Photo Cap Exceeded")
        lines.append("")
        lines.append(
            f"{rare_cap_exceeded['rare_count']} photo(s) are marked 'rare', but this pack "
            f"only allows {rare_cap_exceeded['limit']} "
            f"(ceil({rare_cap_exceeded['photo_count']} photos / 10)). "
            "Excess rare photos will be silently downgraded to 'none' by the game.")
        lines.append("")
        lines.append("All photos currently marked 'rare':")
        lines.append("")
        lines.extend(f"- {name}" for name in rare_cap_exceeded["rare_photos"])
        lines.append("")

    if broken:
        lines.append(f"## Broken References ({len(broken)})")
        lines.append("")
        lines.append("Referenced in the pack but missing on disk:")
        lines.append("")
        lines.extend(f"- {label}" for label in broken)
        lines.append("")

    if orphaned:
        lines.append(f"## Orphaned Files ({len(orphaned)})")
        lines.append("")
        lines.append("Present on disk but not referenced by any photo, event, overlay, texture or dialog:")
        lines.append("")
        lines.extend(f"- {name}" for name in orphaned)
        lines.append("")

    if flagged:
        lines.append(f"## Flagged Photos ({len(flagged)})")
        lines.append("")
        for photo in flagged:
            name = photo.get("name", "(unnamed)")
            source = photo.get("source") or ""
            filename = os.path.basename(source) if source else "(missing file)"
            correction = photo.get("issue_correction") or {}
            note = photo.get("issue_note", "").strip()

            lines.append(f"## {name}")
            lines.append("")
            lines.append(f"- File: `{filename}`")
            lines.append("| Field | Original | Corrected |")
            lines.append("|---|---|---|")
            for key, field_label in (("position", "Position"), ("type", "Type"), ("color", "Color/Special")):
                original = photo.get(key, "")
                corrected = correction.get(key, "")
                marker = " \u2705" if corrected and corrected != original else ""
                lines.append(f"| {field_label} | {original} | {corrected}{marker} |")
            if note:
                lines.append("")
                lines.append(f"**Note:** {note}")
            lines.append("")

    if not (mismatches or id_conflicts or range_too_small or rare_cap_exceeded or broken or orphaned or flagged):
        lines.append("No issues found.")
        lines.append("")

    return "\n".join(lines)


def write_issue_report(pack_data: dict, path: str) -> None:
    content = generate_issue_report_markdown(pack_data)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    _dlog("issue_report.write_issue_report", f"Wrote {path}")
