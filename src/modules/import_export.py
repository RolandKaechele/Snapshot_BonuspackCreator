"""Import / Export bonus content — reads and writes game BonusContent folders."""

import os
import re
import shutil
import configparser
import traceback
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFileDialog #type: ignore

from app_debug import dlog as _dlog
from ui.dialogs import show_warning, show_error, show_info, show_confirm

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QMainWindow#type: ignore
    from modules.pack_manager import PackManager


class ImportExportManager:
    def __init__(self, parent: "QMainWindow") -> None:
        self._parent = parent

    # ── Import ──────────────────────────────────────────────────────────────

    def run_import(self) -> None:
        from ui.dialogs import show_confirm  # local import to avoid circular at module level
        pm: "PackManager" = self._parent._pack_manager
        if pm.is_dirty:
            if not show_confirm(self._parent, "Import Bonus Content",
                                "This will clear the current pack. Continue?",
                                tag="ImportExportManager.run_import"):
                return
        folder = QFileDialog.getExistingDirectory(
            self._parent,
            "Select Bonus Content Pack Folder",
            "",
        )
        if not folder:
            return
        ini_paths = _resolve_ini_paths(folder, self._parent)
        if not ini_paths:
            return
        # Clear views now that a valid folder is confirmed — before parsing starts
        pm.new_pack()
        self._parent._refresh_all()
        try:
            pack_data = _read_pack_ini(ini_paths[0], folder)
            # Capture per-part traits before merging so export can restore them per-part
            types_parts  = [list(pack_data.get("special_types",  []))]
            colors_parts = [list(pack_data.get("special_colors", []))]
            for extra_ini in ini_paths[1:]:
                extra = _read_pack_ini(extra_ini, folder)
                types_parts.append(list(extra.get("special_types",  [])))
                colors_parts.append(list(extra.get("special_colors", [])))
                pack_data.setdefault("photos", []).extend(extra.get("photos", []))
                # Merge per-part trait lists without duplicates
                for key in ("special_types", "special_colors"):
                    seen = set(pack_data.get(key, []))
                    for entry in extra.get(key, []):
                        if entry not in seen:
                            pack_data.setdefault(key, []).append(entry)
                            seen.add(entry)
            if len(ini_paths) > 1:
                # Strip trailing digit(s) added by the per-part split, e.g. "mpack1" → "mpack"
                raw_id = pack_data.get("id", "")
                pack_data["id"] = raw_id.rstrip("0123456789") or raw_id
                # Strip " Part N" suffix from title, e.g. "My Pack Part 1" → "My Pack"
                pack_data["title"] = re.sub(r"\s+[Pp]art\s+\d+\s*$", "", pack_data.get("title", "")).strip()
                pack_data["special_types_parts"]  = types_parts
                pack_data["special_colors_parts"] = colors_parts
            pm.data.update(pack_data)
            pm.data["source_folder"] = folder  # used by orphaned-files tab
            self._parent._refresh_all()
            self._parent.status().set_ok(f"Imported: {os.path.basename(folder)}")
            _dlog("ImportExportManager.run_import", f"Imported {folder} ({len(ini_paths)} ini files)")
        except Exception as exc:
            show_error(self._parent, "Import Error", str(exc), exc=exc,
                       tag="ImportExportManager.run_import")
            self._parent.status().set_error(f"Import failed: {exc}")

    # ── Export ──────────────────────────────────────────────────────────────

    def run_export(self) -> None:
        parent_folder = QFileDialog.getExistingDirectory(
            self._parent,
            "Select Output Parent Folder",
            "",
        )
        if not parent_folder:
            return
        pm: "PackManager" = self._parent._pack_manager

        # Validate dialog scenes before touching the filesystem
        from modules.event_widget import validate_events
        issues = validate_events(pm.data.get("events", []))
        errors   = [i for i in issues if i[0] == "error"]
        warnings = [i for i in issues if i[0] == "warning"]

        def _fmt(lst):
            return "\n".join(
                f"  \u2022 [{i[1]}] node #{i[2]}: {i[3]}" if i[2] is not None
                else f"  \u2022 [{i[1]}]: {i[3]}"
                for i in lst
            )

        if errors:
            show_error(self._parent, "Export Blocked — Validation Errors",
                       "Fix these errors before exporting:\n\n" + _fmt(errors),
                       tag="ImportExportManager.run_export")
            self._parent.status().set_error("Export blocked: validation errors")
            return

        if warnings:
            endevent_warns = [w for w in warnings
                              if "endEvent" in w[3]]
            has_endevent_warns = bool(endevent_warns)
            from ui.dialogs import show_confirm_with_checkbox
            proceed, auto_fix = show_confirm_with_checkbox(
                self._parent, "Export Warnings",
                "The following warnings were found:\n\n" + _fmt(warnings)
                + "\n\nExport anyway?",
                checkbox_label="Add endEvent to affected scenes automatically"
                               if has_endevent_warns else "",
                tag="ImportExportManager.run_export",
            )
            if not proceed:
                return
            if auto_fix and has_endevent_warns:
                _inject_end_events(pm.data, {w[1] for w in endevent_warns})
                self._parent._event_widget.refresh()
        pack_id = pm.get("id") or "mypack"
        game = pm.get("game", "snapshot")
        pack_type_val = pm.get("pack_type", "photos")
        folder_kind = "EventPack" if pack_type_val == "events" else "BonusPack"
        game_prefix = "LewdShores" if game == "lewdshores" else "Snapshot"
        prefix = f"{game_prefix}_{folder_kind}"
        pack_folder = os.path.join(parent_folder, f"{prefix}_{pack_id}")
        data_folder = os.path.join(pack_folder, "Data")
        os.makedirs(data_folder, exist_ok=True)

        try:
            _write_pack_ini(pack_folder, pm.data)
            _export_photo_files(data_folder, pm.data)
            self._parent.status().set_ok(f"Exported to: {pack_folder}")
            show_info(self._parent, "Export Complete",
                      f"Pack exported to:\n{pack_folder}",
                      tag="ImportExportManager.run_export")
            _dlog("ImportExportManager.run_export", f"Exported {pack_folder}")
        except Exception as exc:
            show_error(self._parent, "Export Error", str(exc), exc=exc,
                       tag="ImportExportManager.run_export")
            self._parent.status().set_error(f"Export failed: {exc}")


# ── pack.ini helpers ────────────────────────────────────────────────────────

def _inject_end_events(pack_data: dict, scene_names: set) -> None:
    """Append an endEvent var to the last node of each named dialog scene."""
    import json as _json
    from modules.event_widget import _extract_nodes, _write_nodes
    for ev in pack_data.get("events", []):
        if ev.get("type") != "dialog" or ev.get("name") not in scene_names:
            continue
        try:
            data = _json.loads(ev.get("content", "{}"))
        except Exception:
            continue
        nodes = _extract_nodes(data)
        if not nodes:
            continue
        last = nodes[-1]
        if not any(v.get("key") == "endEvent" for v in last.get("vars", [])):
            last.setdefault("vars", []).append({"key": "endEvent", "val": ""})
            _write_nodes(data, nodes)
            ev["content"] = _json.dumps(data)


def _resolve_ini_paths(folder: str, parent) -> list[str]:
    """Return all .ini paths to import from *folder*.

    pack.ini is always first when present; remaining .ini files follow sorted.
    Returns an empty list (and shows a warning) when none exist.
    """
    preferred = os.path.join(folder, "pack.ini")
    others = sorted(
        os.path.join(folder, f) for f in os.listdir(folder)
        if f.lower().endswith(".ini") and f.lower() != "pack.ini"
    )

    if os.path.exists(preferred):
        candidates = [preferred] + others
    else:
        candidates = others

    if not candidates:
        show_warning(parent, "Import Failed",
                     f"No .ini file found in:\n{folder}",
                     tag="ImportExportManager._resolve_ini_paths")
        return []

    if len(candidates) > 1:
        _dlog("ImportExportManager._resolve_ini_paths",
              f"importing {len(candidates)} ini files")
    return candidates


def _read_pack_ini(ini_path: str, folder: str) -> dict:
    with open(ini_path, encoding="utf-8", errors="replace") as f:
        raw_lines = f.readlines()

    # Fix bare continuation lines so configparser can parse them.
    fixed: list[str] = []
    for line in raw_lines:
        stripped = line.lstrip()
        is_section = stripped.startswith("[")
        is_comment = stripped.startswith(("#", ";"))
        has_key = "=" in line.split(";")[0] or ":" in line.split(";")[0]
        if fixed and not is_section and not is_comment and not has_key and stripped:
            line = "\t" + line.lstrip()
        fixed.append(line)

    # Sections regenerated by the app on export — not passed through verbatim.
    REGEN_SECTIONS = {
        "mod", "pack",
        "defaults",
        "special category",
        "special traits", "special type", "create your own traits",
        "events",
        "photos",
    }

    # Walk raw lines once: build passthrough blocks and collect Special Traits.
    special_types: list[str] = []
    special_colors: list[str] = []
    passthrough_sections: list[tuple[str, list[str]]] = []  # (header_line, content_lines)

    current_header: str | None = None
    current_sec_name: str = ""
    current_lines: list[str] = []

    for line in raw_lines:
        s = line.strip()
        if s.startswith("[") and "]" in s:
            # Flush previous section.
            if current_header is not None and current_sec_name not in REGEN_SECTIONS:
                passthrough_sections.append((current_header, list(current_lines)))
            current_header = s[:s.index("]") + 1]  # e.g. "[Hypnosis]"
            current_sec_name = current_header[1:current_header.index("]")].lower()
            current_lines = []
            continue

        if current_sec_name in ("special traits", "special type", "create your own traits"):
            if s and not s.startswith((";", "#")):
                low = s.lower()
                if low.startswith("specialtype="):
                    special_types.append(s[len("specialtype="):])
                elif low.startswith("specialcolor="):
                    special_colors.append(s[len("specialcolor="):])
                elif low.startswith("newtype="):
                    special_types.append(s[len("newtype="):])
                elif low.startswith("newspecial="):
                    special_colors.append(s[len("newspecial="):])
        elif current_header is not None and current_sec_name not in REGEN_SECTIONS:
            current_lines.append(line)

    # Flush last section.
    if current_header is not None and current_sec_name not in REGEN_SECTIONS:
        passthrough_sections.append((current_header, list(current_lines)))

    cfg = configparser.RawConfigParser(strict=False)  # some packs have duplicate keys
    cfg.read_string("".join(fixed))
    data: dict = {}

    # Determine game: check [Mod] (snapshot) and [Pack] (lewdshores)
    game = "snapshot"
    for _sec in ("Mod", "Pack"):
        if cfg.has_option(_sec, "gameid") or cfg.has_option(_sec, "gameID"):
            _gid = (cfg.get(_sec, "gameid") if cfg.has_option(_sec, "gameid")
                    else cfg.get(_sec, "gameID"))
            if _gid.lower() == "lewdshores":
                game = "lewdshores"
                break
    data["game"] = game

    section = "Mod" if game == "snapshot" else "Pack"
    if cfg.has_option(section, "id"):
        data["id"] = cfg.get(section, "id")
    if cfg.has_option(section, "idrange"):
        data["id_range"] = cfg.get(section, "idrange")
    if cfg.has_option(section, "title"):
        data["title"] = cfg.get(section, "title").strip('"')
    if cfg.has_option(section, "category"):
        data["defaults_category"] = cfg.get(section, "category")

    pack_type = "photos"
    if cfg.has_option(section, "type"):
        if cfg.get(section, "type") == "events":
            pack_type = "events"
    if cfg.has_section("Hypnosis"):
        pack_type = "lovelens"
    data["pack_type"] = pack_type

    # [Defaults] — read into structured fields, not passthrough
    if cfg.has_section("Defaults"):
        # Snapshot! keys
        if cfg.has_option("Defaults", "position"):
            data["defaults_position"] = cfg.get("Defaults", "position")
        if cfg.has_option("Defaults", "type"):
            data["defaults_type"] = cfg.get("Defaults", "type")
        if cfg.has_option("Defaults", "color"):
            data["defaults_color"] = cfg.get("Defaults", "color")
        # Lewd Shores keys
        if cfg.has_option("Defaults", "photoposition"):
            data["defaults_photo_position"] = cfg.get("Defaults", "photoposition")
        if cfg.has_option("Defaults", "special"):
            data["defaults_special"] = cfg.get("Defaults", "special")
        if cfg.has_option("Defaults", "category"):
            data["defaults_category"] = cfg.get("Defaults", "category")
        if cfg.has_option("Defaults", "packtheme"):
            data["defaults_pack_theme"] = cfg.get("Defaults", "packtheme").strip('"')
        if cfg.has_option("Defaults", "themecolor"):
            data["defaults_theme_color"] = cfg.get("Defaults", "themecolor")
        # ls_type mirrors type for round-tripping
        if "defaults_photo_position" in data and "defaults_type" not in data:
            if cfg.has_option("Defaults", "type"):
                data["defaults_ls_type"] = cfg.get("Defaults", "type")
        elif "defaults_photo_position" in data and "defaults_type" in data:
            data["defaults_ls_type"] = data["defaults_type"]

    if cfg.has_section("Special Category"):
        if cfg.has_option("Special Category", "specialcategory"):
            data["special_category"] = cfg.get("Special Category", "specialcategory").strip('"')
        if cfg.has_option("Special Category", "specialcategorycolor"):
            data["special_category_color"] = "#" + cfg.get("Special Category", "specialcategorycolor").lstrip("#")

    if special_types:
        data["special_types"] = special_types
    if special_colors:
        data["special_colors"] = special_colors

    _ASSET_EXTS = (".dat", ".jpa", ".pna", ".png", ".jpg", ".jpeg", ".bytes")

    def _resolve_asset(name: str) -> str:
        from modules.image_utils import resolve_asset
        return resolve_asset(name, folder)

    # Parse [Hypnosis] and [Hypnosis Textures] into structured fields.
    # [Hypnosis Text] (complex dialogue tree) stays as passthrough.
    remaining_pt: list = []
    for header, content_lines in passthrough_sections:
        sec_name = header[1:header.index("]")].lower().strip()
        if sec_name == "hypnosis":
            ll: dict = {}
            overlays_import: dict = {}
            for raw in content_lines:
                s = raw.strip()
                if not s or s.startswith((";", "#")) or "=" not in s:
                    continue
                k, _, v = s.partition("=")
                k = k.strip()
                v = v.split(";")[0].strip()
                kl = k.lower()
                if kl in ("model", "hairstyle", "accessories", "haircolor", "eyecolor"):
                    camel = {"hairstyle": "hairStyle", "haircolor": "hairColor",
                             "eyecolor": "eyeColor"}.get(kl, kl)
                    ll[camel] = v
                elif kl.startswith("overlay"):
                    overlays_import[k] = [_resolve_asset(n.strip())
                                          for n in v.split(",") if n.strip()]
            if ll:
                data["love_lens"] = ll
            if overlays_import:
                data["overlays"] = overlays_import
        elif sec_name == "hypnosis textures":
            textures_import: dict = {}
            for raw in content_lines:
                s = raw.strip()
                if not s or s.startswith((";", "#")) or "=" not in s:
                    continue
                k, _, v = s.partition("=")
                k = k.strip()
                v = v.split(";")[0].strip()
                textures_import[k] = [_resolve_asset(n.strip())
                                      for n in v.split(",") if n.strip()]
            if textures_import:
                data["textures"] = textures_import
        else:
            remaining_pt.append((header, content_lines))

    if remaining_pt:
        data["passthrough_sections"] = remaining_pt

    # [Events] — read into structured events list
    if cfg.has_section("Events"):
        if cfg.has_option("Events", "eventtype"):
            data["event_type"] = cfg.get("Events", "eventtype")
        existing_events: list = []
        def _parse_names(raw: str) -> list[str]:
            return [n.strip() for n in raw.split(",") if n.strip()]
        if cfg.has_option("Events", "backgrounds"):
            for n in _parse_names(cfg.get("Events", "backgrounds")):
                existing_events.append({"type": "background", "name": n, "source": None})
        if cfg.has_option("Events", "overlays"):
            for n in _parse_names(cfg.get("Events", "overlays")):
                existing_events.append({"type": "overlay", "name": n, "source": None})
        if cfg.has_option("Events", "dialogs"):
            for n in _parse_names(cfg.get("Events", "dialogs")):
                existing_events.append({"type": "dialog", "name": n, "source": None,
                                        "content": _find_json_content(folder, n)})
        # Resolve image sources from the pack folder
        for ev in existing_events:
            if ev.get("type") in ("background", "overlay") and not ev.get("source"):
                n = ev["name"]
                for d in (os.path.join(folder, "Data"), folder):
                    for ext in (".png", ".jpg", ".jpeg", ".mp4", ".bytes", ".dat"):
                        p = os.path.join(d, f"{n}{ext}")
                        if os.path.exists(p):
                            ev["source"] = p
                            break
                    if ev.get("source"):
                        break
        data["events"] = existing_events

    # Photos — image search order mirrors the game: modFolder/Data, modFolder, nested same-name dir
    photos = []
    if cfg.has_option("Photos", "names"):
        names = [n.strip() for n in cfg.get("Photos", "names").split(",") if n.strip()]
        nested = os.path.join(folder, os.path.basename(folder))
        search_dirs = [
            os.path.join(folder, "Data"),
            folder,
            os.path.join(nested, "Data"),
            nested,
        ]
        for name in names:
            entry: dict = {"name": name, "source": None}
            for search_dir in search_dirs:
                if not os.path.isdir(search_dir):
                    continue
                for ext in (".png", ".jpg", ".jpeg", ".pna", ".jpa", ".bytes", ".dat"):
                    candidate = os.path.join(search_dir, f"{name}{ext}")
                    if os.path.exists(candidate):
                        entry["source"] = candidate
                        break
                if entry["source"]:
                    break
            for key in ("position", "type", "color", "hypnoType",
                        "hypnosisType", "sequenceType", "photoPosition", "special"):
                opt = f"{name}.{key}"
                if cfg.has_option("Photos", opt):
                    entry[key] = cfg.get("Photos", opt)
            # LS per-photo type alias — record original key name for roundtrip fidelity
            if "type" not in entry and cfg.has_option("Photos", f"{name}.newType"):
                entry["type"] = cfg.get("Photos", f"{name}.newType")
                entry["_type_key"] = "newType"
            # Per-photo SpecialType alias override
            if cfg.has_option("Photos", f"{name}.SpecialType"):
                entry["specialType"] = cfg.get("Photos", f"{name}.SpecialType")
            photos.append(entry)
    data["photos"] = photos

    return data


def _write_pack_ini(pack_folder: str, data: dict) -> None:
    game = data.get("game", "snapshot")
    pack_type = data.get("pack_type", "photos")
    pack_id = data.get("id", "mypack")
    title = data.get("title", "").strip('"')
    id_range = data.get("id_range", "")
    photos: list[dict] = data.get("photos", [])
    passthrough: list[tuple[str, list[str]]] = data.get("passthrough_sections", [])

    range_start: int | None = None
    try:
        range_start = int(id_range.split("-")[0])
    except (ValueError, AttributeError):
        pass

    chunks = [photos[i:i + 100] for i in range(0, max(len(photos), 1), 100)]
    multi = len(chunks) > 1

    for part_idx, chunk in enumerate(chunks):
        part_num = part_idx + 1
        part_id = f"{pack_id}{part_num}" if multi else pack_id
        part_title = f"{title} Part {part_num}" if multi else title
        if range_start is not None:
            part_start = range_start + part_idx * 100
            part_range = f"{part_start}-{part_start + 99}"
        else:
            part_range = id_range

        lines: list[str] = []
        if game == "lewdshores":
            lines += [
                "[Pack]",
                "gameID=lewdshores",
                f"id={part_id}",
                f"idrange={part_range}",
                f'title="{part_title}"',
                "",
            ]
        else:
            lines += [
                "[Mod]",
                "plugID=snapshot",  # BUG-4 fix: real packs use plugID, not gameID
                f"id={part_id}",
                f"idrange={part_range}",
                f'title="{part_title}"',
            ]
            if pack_type == "events":
                lines.append("type=events")
            elif pack_type == "lovelens":
                lines.append("hypnosis=true")
            lines.append("")

        # Passthrough sections (Hypnosis Text dialogue, unknown sections) — written verbatim.
        for header, content_lines in passthrough:
            lines.append(header)
            lines.extend(l.rstrip("\n") for l in content_lines)
            if lines[-1].strip():
                lines.append("")

        # [Hypnosis] and [Hypnosis Textures] — generated from structured data
        if pack_type == "lovelens":
            ll_out: dict = data.get("love_lens", {})
            overlays_out: dict = data.get("overlays", {})
            hypno_body: list[str] = []
            for field in ("model", "hairStyle", "accessories", "hairColor", "eyeColor"):
                if field in ll_out and ll_out[field]:
                    hypno_body.append(f"{field}={ll_out[field]}")
            for key, items in overlays_out.items():
                names = [os.path.splitext(os.path.basename(p))[0] for p in items if p]
                if names:
                    hypno_body.append(f"{key}={','.join(names)}")
            if hypno_body:
                lines.append("[Hypnosis]")
                lines.extend(hypno_body)
                lines.append("")
            textures_out: dict = data.get("textures", {})
            tex_body: list[str] = []
            for key, items in textures_out.items():
                names = [os.path.splitext(os.path.basename(p))[0] for p in items if p]
                if names:
                    tex_body.append(f"{key}={','.join(names)}")
            if tex_body:
                lines.append("[Hypnosis Textures]")
                lines.extend(tex_body)
                lines.append("")

        # BUG-2 fix: write game-correct [Defaults] keys
        if game == "lewdshores":
            def_photo_pos = data.get("defaults_photo_position", "beachFront")
            def_ls_type   = data.get("defaults_ls_type", data.get("defaults_type", "front view"))
            def_special   = data.get("defaults_special", "none")
            def_category  = data.get("defaults_category", "")
            def_pack_theme = data.get("defaults_pack_theme", "")
            def_theme_color = data.get("defaults_theme_color", "")
            ls_def: list[str] = [f"photoPosition={def_photo_pos}"]
            if def_category:
                ls_def.append(f"category={def_category}")
            if def_pack_theme:
                ls_def.append(f'packTheme="{def_pack_theme}"')
            if def_theme_color:
                ls_def.append(f"themeColor={def_theme_color.lstrip('#')}")
            ls_def += [f"type={def_ls_type}", f"special={def_special}"]
            lines += ["[Defaults]"] + ls_def + [""]
        else:
            def_pos      = data.get("defaults_position", "upskirt")
            def_type     = data.get("defaults_type", "plain")
            def_color    = data.get("defaults_color", "white")
            def_cat      = data.get("defaults_category", "")
            def_special  = data.get("defaults_special", "")
            snap_def: list[str] = []
            if def_cat:
                snap_def.append(f"category={def_cat}")
            if data.get("defaults_position") is not None:
                snap_def.append(f"position={def_pos}")
            if data.get("defaults_type") is not None:
                snap_def.append(f"type={def_type}")
            if data.get("defaults_color") is not None:
                snap_def.append(f"color={def_color}")
            if def_special:
                snap_def.append(f"special={def_special}")
            if snap_def:
                lines += ["[Defaults]"] + snap_def + [""]

        # BUG-5 fix: [Special Category] only for Snapshot!
        special_cat = data.get("special_category", "")
        special_color = data.get("special_category_color", "#dea3a5").lstrip("#")
        if special_cat and game == "snapshot":
            lines += [
                "[Special Category]",
                f'specialCategory="{special_cat}"',
                f"specialCategoryColor={special_color}",
                "",
            ]

        # BUG-3 fix: use [Create your own traits]/newType/newSpecial for Lewd Shores
        types_parts  = data.get("special_types_parts")
        colors_parts = data.get("special_colors_parts")
        special_types  = types_parts[part_idx]  if types_parts  and part_idx < len(types_parts)  else data.get("special_types",  [])
        special_colors = colors_parts[part_idx] if colors_parts and part_idx < len(colors_parts) else data.get("special_colors", [])
        if special_types or special_colors:
            if game == "lewdshores":
                lines += ["[Create your own traits]", ""]
                for entry in special_types:
                    lines.append(f"newType={entry}")
                for entry in special_colors:
                    lines.append(f"newSpecial={entry}")
            else:
                lines += ["[Special Traits]", ""]
                for entry in special_types:
                    lines.append(f"specialType={entry}")
                for entry in special_colors:
                    lines.append(f"specialColor={entry}")
            lines.append("")

        # Write [Events] section for events packs (only in first part)
        if pack_type == "events" and part_idx == 0:
            events_list: list[dict] = data.get("events", [])
            bgs = [e.get("name", "") for e in events_list if e.get("type") == "background" and e.get("name")]
            ovs = [e.get("name", "") for e in events_list if e.get("type") == "overlay" and e.get("name")]
            dlgs = [e.get("name", "") for e in events_list if e.get("type") == "dialog" and e.get("name")]
            event_type_val = data.get("event_type", "normal")
            if bgs or ovs or dlgs or event_type_val != "normal":
                lines.append("[Events]")
                if event_type_val != "normal":
                    lines.append(f"eventtype={event_type_val}")
                lines.append(f"backgrounds={','.join(bgs)}")
                lines.append(f"Overlays={','.join(ovs)}")
                if dlgs:
                    lines.append(f"dialogs={','.join(dlgs)}")
                lines.append("")

        if chunk:
            names_val = ",".join(p.get("name", "") for p in chunk)
            lines += ["[Photos]", f"names={names_val}", ""]
            for photo in chunk:
                n = photo.get("name", "")
                type_key = photo.get("_type_key", "type")
                for key in ("position", "type", "color",
                            "hypnoType", "hypnosisType", "sequenceType", "photoPosition", "special", "specialType"):
                    if key in photo and photo[key]:
                        out_key = type_key if key == "type" else key
                        lines.append(f"{n}.{out_key}={photo[key]}")
            lines.append("")

        filename = f"{pack_id}{part_num}.ini" if multi else "pack.ini"
        ini_path = os.path.join(pack_folder, filename)
        with open(ini_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


def _find_json_content(folder: str, base_name: str) -> str:
    """Return contents of <base_name>.json found in folder or folder/Data, or empty string."""
    for search_dir in (os.path.join(folder, "Data"), folder):
        p = os.path.join(search_dir, f"{base_name}.json")
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    return f.read()
            except OSError:
                pass
    return ""


def _export_photo_files(data_folder: str, data: dict) -> None:
    for photo in data.get("photos", []):
        src = photo.get("source")
        name = photo.get("name")
        if src and name and os.path.exists(src):
            ext = os.path.splitext(src)[1] or ".dat"
            dst = os.path.join(data_folder, f"{name}{ext}")
            shutil.copy2(src, dst)

    # Copy [Hypnosis] overlay files and [Hypnosis Textures] files
    for items in data.get("overlays", {}).values():
        for src in items:
            if src and os.path.exists(src):
                shutil.copy2(src, os.path.join(data_folder, os.path.basename(src)))
    for items in data.get("textures", {}).values():
        for src in items:
            if src and os.path.exists(src):
                shutil.copy2(src, os.path.join(data_folder, os.path.basename(src)))

    # Copy event backgrounds, overlays, and dialog JSONs
    for event in data.get("events", []):
        src = event.get("source")
        name = event.get("name")
        if not name:
            continue
        if event.get("type") == "dialog":
            content = event.get("content", "")
            if content:
                dst = os.path.join(data_folder, f"{name}.json")
                with open(dst, "w", encoding="utf-8") as f:
                    f.write(content)
        elif src and os.path.exists(src):
            ext = os.path.splitext(src)[1]
            dst = os.path.join(data_folder, f"{name}{ext}")
            shutil.copy2(src, dst)

    # Copy orphaned files (on disk in source folder but not referenced by the pack)
    from modules.orphaned_files import _collect_referenced, _collect_disk_assets
    source_folder = data.get("source_folder", "")
    if source_folder and os.path.isdir(source_folder):
        referenced = _collect_referenced(data)
        for path in _collect_disk_assets(source_folder):
            stem = os.path.splitext(os.path.basename(path))[0].lower()
            if stem not in referenced:
                shutil.copy2(path, os.path.join(data_folder, os.path.basename(path)))
