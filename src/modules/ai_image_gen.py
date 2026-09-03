"""AI Image Generator — dialog host for diffusion backend plugins.

Opens a prompt dialog from Pictures, Love Lens, and Events widgets; delegates
actual image generation to whichever diffusion backend plugin(s) are
registered (see plugins/perchance_diffusion, plugins/anythingxl_diffusion),
then shows a selection picker so the user can choose which images to keep.
"""

import os
import random
import sys
import tempfile
import time
import json
from typing import Callable

from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QSlider, QListWidget, QListWidgetItem,
    QSplitter, QWidget, QGroupBox, QFormLayout,
    QDialogButtonBox, QProgressBar, QStackedWidget, QSizePolicy,
    QFileDialog, QScrollArea,
)

from app_debug import dlog as _dlog, is_debug as _is_debug
from ui.dialogs import show_error

# ─── Type / prompt-enhancement dictionaries per widget ───────────────────────

PHOTO_TYPES: dict[str, dict] = {
    "upskirt": {
        "label": "Upskirt Shot",
        "prompt_enhancement": (
            "nsfw, "
            "low angle upskirt shot, panties clearly visible, "
            "short pleated skirt, anime style, high quality"
        ),
    },
    "jogger": {
        "label": "Jogger Photo",
        "prompt_enhancement": (
            "nsfw, "
            "jogging pose, sports bra, spandex shorts, dynamic running motion, "
            "anime style, high quality"
        ),
    },
    "xray": {
        "label": "X-Ray Upskirt",
        "prompt_enhancement": (
            "nsfw, "
            "x-ray vision style, see-through skirt, panties visible, "
            "anime style, high quality"
        ),
    },
    "bench": {
        "label": "Bench Photo",
        "prompt_enhancement": (
            "nsfw, "
            "sitting on park bench, legs together, short skirt, "
            "anime style, high quality"
        ),
    },
    "bar": {
        "label": "Bar Photo (Barstool)",
        "prompt_enhancement": (
            "nsfw, "
            "sitting on barstool at bar counter, cocktail dress, "
            "anime style, high quality"
        ),
    },
    "photoBooth": {
        "label": "Photo Booth",
        "prompt_enhancement": (
            "nsfw, "
            "inside photo booth, striped curtain background, cute pose, "
            "anime style, high quality"
        ),
    },
    "event": {
        "label": "City Event Photo",
        "prompt_enhancement": (
            "nsfw, "
            "outdoor city event, crowd in background, casual clothing, "
            "anime style, high quality"
        ),
    },
    "hypno": {
        "label": "Love Lens / Hypno Photo",
        "prompt_enhancement": (
            "nsfw, "
            "hypnotic spiral eyes, dazed blissful expression, standing pose, "
            "anime style, high quality"
        ),
    },
    "police": {
        "label": "Police Upskirt",
        "prompt_enhancement": (
            "nsfw, "
            "female police officer uniform, skirt, upskirt angle, "
            "anime style, high quality"
        ),
    },
    "flasher": {
        "label": "Flasher (Yoruko Task)",
        "prompt_enhancement": (
            "nsfw, "
            "opening coat to flash, mischievous smile, trench coat, "
            "anime style, high quality"
            "naked body, exposed breasts, exposed genitals"
        ),
    },
    "window": {
        "label": "Window (Yoruko Task)",
        "prompt_enhancement": (
            "nsfw, "
            "standing at open window, "
            "anime style, high quality"
            "naked body, exposed breasts, exposed genitals"
            "caught in the act, surprised expression, looking outside, "
            "sex tools"
        ),
    },
}

LOVE_LENS_TYPES: dict[str, dict] = {
    "standing_topless": {
        "label": "Standing Topless",
        "prompt_enhancement": (
            "nsfw, "
            "standing upright, topless, bare chest, confident pose, "
            "full body, anime style, high quality"
        ),
    },
    "standing_nude": {
        "label": "Standing Nude",
        "prompt_enhancement": (
            "nsfw, "
            "standing upright, fully nude, tasteful pose, "
            "full body, anime style, high quality"
        ),
    },
    "kneeling_cum_mouth": {
        "label": "Kneeling – Cum in Mouth",
        "prompt_enhancement": (
            "nsfw, "
            "kneeling pose, mouth open, ahegao expression, cum in mouth, "
            "anime style, high quality"
        ),
    },
    "kneeling_cum_face": {
        "label": "Kneeling – Cum on Face",
        "prompt_enhancement": (
            "nsfw, "
            "kneeling pose, cum on face, satisfied expression, "
            "anime style, high quality"
        ),
    },
    "leaning_cum_butt": {
        "label": "Leaning – Cum on Butt",
        "prompt_enhancement": (
            "nsfw, "
            "leaning forward, cum dripping on buttocks, rear view, "
            "anime style, high quality"
        ),
    },
    "leaning_cum_vagina": {
        "label": "Leaning – Cum in Vagina",
        "prompt_enhancement": (
            "nsfw, "
            "leaning forward pose, cum dripping from vagina, rear view, "
            "anime style, high quality"
        ),
    },
    "leaning_cum_anus": {
        "label": "Leaning – Cum in Anus",
        "prompt_enhancement": (
            "nsfw, "
            "leaning forward pose, cum dripping from anus, rear view, "
            "anime style, high quality"
        ),
    },
}

EVENT_TYPES: dict[str, dict] = {
    "alley_night": {
        "label": "Dark Alley – Night",
        "prompt_enhancement": (
            "nsfw, "
            "dark alley, night-time, neon signs reflected on wet pavement, "
            "cyberpunk atmosphere, anime background, no characters, high quality"
        ),
    },
    "city_street_day": {
        "label": "City Street – Day",
        "prompt_enhancement": (
            "nsfw, "
            "busy city street, daytime, shop-lined sidewalk, pedestrians, "
            "anime background, no characters in foreground, high quality"
        ),
    },
    "park_day": {
        "label": "Park – Day",
        "prompt_enhancement": (
            "nsfw, "
            "city park, sunny day, trees, park benches, birds, "
            "anime background, no characters, high quality"
        ),
    },
    "school_grounds": {
        "label": "School Grounds",
        "prompt_enhancement": (
            "nsfw, "
            "schoolyard, outside school building, sakura trees, "
            "anime background, no characters, high quality"
        ),
    },
    "bar_interior": {
        "label": "Bar Interior",
        "prompt_enhancement": (
            "nsfw, "
            "bar interior, dim lighting, neon signs, bottles on shelves, "
            "bar counter, anime background, no characters, high quality"
        ),
    },
    "office_interior": {
        "label": "Office Interior",
        "prompt_enhancement": (
            "nsfw, "
            "office interior, desks, computer monitors, city view window, "
            "anime background, no characters, high quality"
        ),
    },
    "beach_daytime": {
        "label": "Beach – Daytime",
        "prompt_enhancement": (
            "nsfw, "
            "beach, ocean waves, white sand, palm trees, sunny sky, "
            "anime background, no characters, high quality"
        ),
    },
    "rooftop_night": {
        "label": "Rooftop – Night",
        "prompt_enhancement": (
            "nsfw, "
            "city rooftop, night-time, glittering skyline, starry sky, "
            "anime background, no characters, high quality"
        ),
    },
}

LOVE_LENS_OVERLAY_TYPES: dict[str, dict] = {
    "overlayStart": {
        "label": "Overlay – Start",
        "prompt_enhancement": (
            "nsfw, "
            "standing, hypnotic dazed expression, arms relaxed, "
            "full body front view, anime style, high quality, transparent background"
        ),
    },
    "overlayBoob": {
        "label": "Overlay – Grabbing Breasts",
        "prompt_enhancement": (
            "nsfw, "
            "topless, hands cupping own breasts, ahegao expression, "
            "full body front view, anime style, high quality, transparent background"
        ),
    },
    "overlayPussy": {
        "label": "Overlay – Grabbing Vagina",
        "prompt_enhancement": (
            "nsfw, "
            "nude, hand between legs touching vagina, blissful expression, "
            "full body front view, anime style, high quality, transparent background"
        ),
    },
    "overlayButt": {
        "label": "Overlay – Grabbing Butt",
        "prompt_enhancement": (
            "nsfw, "
            "nude, hands on own buttocks, ahegao expression, "
            "full body rear view, anime style, high quality, transparent background"
        ),
    },
    "overlayVaginalStart": {
        "label": "Overlay – Vaginal Start",
        "prompt_enhancement": (
            "nsfw, "
            "nude, legs slightly apart, anticipating blissful expression, "
            "full body front view, anime style, high quality, transparent background"
        ),
    },
    "overlayVaginalPenetration": {
        "label": "Overlay – Vaginal Penetration",
        "prompt_enhancement": (
            "nsfw, "
            "nude, vaginal penetration pose, ahegao expression, "
            "full body front view, anime style, high quality, transparent background"
        ),
    },
    "overlayVaginalCum": {
        "label": "Overlay – Vaginal Cum",
        "prompt_enhancement": (
            "nsfw, "
            "nude, cum dripping from vagina, satisfied ahegao expression, "
            "full body front view, anime style, high quality, transparent background"
        ),
    },
    "overlayAnalStart": {
        "label": "Overlay – Anal Start",
        "prompt_enhancement": (
            "nsfw, "
            "nude, bent forward slightly, anticipating expression, "
            "full body rear view, anime style, high quality, transparent background"
        ),
    },
    "overlayAnalPenetration": {
        "label": "Overlay – Anal Penetration",
        "prompt_enhancement": (
            "nsfw, "
            "nude, anal penetration pose, ahegao expression, "
            "full body rear view, anime style, high quality, transparent background"
        ),
    },
    "overlayAnalCum": {
        "label": "Overlay – Anal Cum",
        "prompt_enhancement": (
            "nsfw, "
            "nude, cum dripping from anus, satisfied ahegao expression, "
            "full body rear view, anime style, high quality, transparent background"
        ),
    },
}

LEWD_SHORES_PHOTO_TYPES: dict[str, dict] = {
    "beachFront": {
        "label": "Beach – Front",
        "prompt_enhancement": (
            "nsfw, "
            "standing on beach, ocean background, bikini or swimsuit, "
            "front view, anime style, high quality"
        ),
    },
    "beachBack": {
        "label": "Beach – Back",
        "prompt_enhancement": (
            "nsfw, "
            "standing on beach, ocean background, bikini or swimsuit, "
            "rear view, anime style, high quality"
        ),
    },
    "exposedFront": {
        "label": "Exposed – Front",
        "prompt_enhancement": (
            "nsfw, "
            "outdoor beach setting, topless or nude, "
            "front view, anime style, high quality"
        ),
    },
    "exposedBack": {
        "label": "Exposed – Back",
        "prompt_enhancement": (
            "nsfw, "
            "outdoor beach setting, topless or nude, "
            "rear view, anime style, high quality"
        ),
    },
    "yoga": {
        "label": "Yoga",
        "prompt_enhancement": (
            "nsfw, "
            "yoga pose, sports bra, yoga pants, "
            "anime style, high quality"
        ),
    },
    "shower": {
        "label": "Shower",
        "prompt_enhancement": (
            "nsfw, "
            "standing in shower, wet body, water droplets, "
            "anime style, high quality, "
            "sex"
        ),
    },
    "wc": {
        "label": "WC",
        "prompt_enhancement": (
            "nsfw, "
            "sitting on toilet, bathroom setting, panties around ankles, "
            "anime style, high quality, "
            "peeing, urination"
        ),
    },
    "mermaid": {
        "label": "Mermaid (Lying on Stomach)",
        "prompt_enhancement": (
            "nsfw, "
            "lying on stomach on beach sand, mermaid pose, "
            "bikini or topless, rear view, anime style, high quality"
        ),
    },
    "underwater": {
        "label": "Underwater",
        "prompt_enhancement": (
            "nsfw, "
            "underwater scene, swimming, bubbles, bikini, "
            "anime style, high quality, "
            "sex"
        ),
    },
    "police": {
        "label": "Lifeguard",
        "prompt_enhancement": (
            "nsfw, "
            "lifeguard uniform, standing on beach, confident pose, "
            "anime style, high quality"
        ),
    },
    "sPolice": {
        "label": "Sitting Lifeguard",
        "prompt_enhancement": (
            "nsfw, "
            "lifeguard uniform, sitting on lifeguard tower, relaxed pose, "
            "anime style, high quality"
        ),
    },
    "booth": {
        "label": "Booth",
        "prompt_enhancement": (
            "nsfw, "
            "inside changing booth, undressing, swimsuit, "
            "anime style, high quality"
        ),
    },
    "angry": {
        "label": "Busted",
        "prompt_enhancement": (
            "nsfw, "
            "caught in the act, surprised or embarrassed expression, "
            "anime style, high quality"
        ),
    },
}

SNAPSHOT_PHOTO_MODIFIERS: dict[str, dict] = {
    "plain": {
        "label": "Plain",
        "prompt_enhancement": "plain cotton panties",
    },
    "stripes": {
        "label": "Stripes",
        "prompt_enhancement": "striped panties",
    },
    "dots": {
        "label": "Dots",
        "prompt_enhancement": "polka dot panties",
    },
    "frill": {
        "label": "Frill",
        "prompt_enhancement": "frilly lace panties",
    },
    "kinky": {
        "label": "Kinky",
        "prompt_enhancement": "kinky harness straps, erotic underwear",
    },
    "none": {
        "label": "None (no underwear)",
        "prompt_enhancement": "no underwear, bare skin",
    },
    "plug": {
        "label": "Plug",
        "prompt_enhancement": "butt plug visible",
    },
    "piercing": {
        "label": "Piercing",
        "prompt_enhancement": "genital piercing visible",
    },
    "cum": {
        "label": "Cum",
        "prompt_enhancement": "cum on panties",
    },
    "nude": {
        "label": "Nude",
        "prompt_enhancement": "fully nude, no clothing",
    },
    "flashing": {
        "label": "Flashing",
        "prompt_enhancement": "flashing, lifting skirt, exposing self",
    },
    "sex": {
        "label": "Sex",
        "prompt_enhancement": "nsfw explicit, sexual intercourse",
    },
    "topless": {
        "label": "Topless",
        "prompt_enhancement": "topless, bare breasts exposed",
    },
    "dildo": {
        "label": "Dildo",
        "prompt_enhancement": "using a dildo",
    },
    "mastubrate": {
        "label": "Masturbate",
        "prompt_enhancement": "masturbating, hand between legs",
    },
    "front": {
        "label": "Front view",
        "prompt_enhancement": "front view",
    },
    "back": {
        "label": "Back view",
        "prompt_enhancement": "rear view, back to camera",
    },
    "goth": {
        "label": "Goth",
        "prompt_enhancement": "gothic style, black lace lingerie, dark aesthetic",
    },
}

LEWD_SHORES_PHOTO_MODIFIERS: dict[str, dict] = {
    "front view": {
        "label": "Front View",
        "prompt_enhancement": "facing camera, front view",
    },
    "back view": {
        "label": "Back View",
        "prompt_enhancement": "back to camera, rear view",
    },
    "butt view": {
        "label": "Butt View",
        "prompt_enhancement": "buttocks facing camera, rear view",
    },
    "changing": {
        "label": "Changing",
        "prompt_enhancement": "mid-change, removing swimsuit",
    },
    "cameltoe": {
        "label": "Cameltoe",
        "prompt_enhancement": "cameltoe visible through tight swimsuit",
    },
    "flashing": {
        "label": "Flashing",
        "prompt_enhancement": "flashing, pulling aside swimsuit",
    },
    "yoga": {
        "label": "Yoga Pose",
        "prompt_enhancement": "yoga pose, flexible stretch",
    },
    "mermaid": {
        "label": "Mermaid (Lying)",
        "prompt_enhancement": "lying on stomach, mermaid pose",
    },
    "booth": {
        "label": "Booth",
        "prompt_enhancement": "inside changing booth, curtain visible",
    },
    "none": {
        "label": "None",
        "prompt_enhancement": "",
    },
}

PHOTO_MODIFIER_TYPES: dict[str, dict[str, dict]] = {
    "photos": SNAPSHOT_PHOTO_MODIFIERS,
    "photos_lewdshores": LEWD_SHORES_PHOTO_MODIFIERS,
}

WIDGET_TYPES: dict[str, dict[str, dict]] = {
    "photos": PHOTO_TYPES,
    "photos_lewdshores": LEWD_SHORES_PHOTO_TYPES,
    "love_lens": LOVE_LENS_TYPES,
    "love_lens_overlays": LOVE_LENS_OVERLAY_TYPES,
    "events": EVENT_TYPES,
}

# Single shared negative prompt sent with every perchance.org generation request.
NEGATIVE_PROMPT: str = (
    "ugly, bad anatomy, blurry, low quality, watermark, text, logo, "
    "2girls, 2boys, multiple girls, multiple boys, group, crowd, "
    "extra people, background characters"
)

# ─── Prompt data loaded from an external JSON file (editable by end users) ───

# Categories above; kept in sync with the "prompts.json" schema. Dicts are
# mutated in-place on reload so existing references (e.g. WIDGET_TYPES) stay valid.
_PROMPT_CATEGORIES: dict[str, dict] = {
    "PHOTO_TYPES": PHOTO_TYPES,
    "LOVE_LENS_TYPES": LOVE_LENS_TYPES,
    "EVENT_TYPES": EVENT_TYPES,
    "LOVE_LENS_OVERLAY_TYPES": LOVE_LENS_OVERLAY_TYPES,
    "LEWD_SHORES_PHOTO_TYPES": LEWD_SHORES_PHOTO_TYPES,
    "SNAPSHOT_PHOTO_MODIFIERS": SNAPSHOT_PHOTO_MODIFIERS,
    "LEWD_SHORES_PHOTO_MODIFIERS": LEWD_SHORES_PHOTO_MODIFIERS,
}


def default_prompt_file() -> str:
    """Return the default prompts.json path: beside main.py, or beside the exe when frozen."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # src/
    return os.path.join(base, "prompts.json")


def reload_prompts(path: str | None = None) -> None:
    """(Re)load prompt-enhancement data from a JSON file into the module-level dicts.

    Silently keeps the built-in defaults when the file is missing or invalid,
    so this is always safe to call.
    """
    path = path or default_prompt_file()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        _dlog("ai_image_gen.reload_prompts", f"could not load {path!r}: {exc}")
        return
    for name, target in _PROMPT_CATEGORIES.items():
        new_values = data.get(name)
        if isinstance(new_values, dict):
            target.clear()
            target.update(new_values)
    new_negative = data.get("NEGATIVE_PROMPT")
    if isinstance(new_negative, str) and new_negative:
        global NEGATIVE_PROMPT
        NEGATIVE_PROMPT = new_negative
    _dlog("ai_image_gen.reload_prompts", f"loaded prompts from {path!r}")


# Load the default prompt file (if present) at import time so the built-in
# dict literals above act as a fallback when no external file exists.
reload_prompts()

# Widget types that generate character images (solo prefix is injected automatically).
_CHAR_WIDGET_TYPES: frozenset[str] = frozenset(
    {"photos", "photos_lewdshores", "love_lens", "love_lens_overlays"}
)

# ─── Perchance API helpers ────────────────────────────────────────────────────

# ─── Diffusion backend plugin registry ───────────────────────────────────────
#
# Diffusion backends (Perchance.org online, AnythingXL local, …) are provided
# by plugins in plugins/ that call register_diffusion_backend() from their
# register(app) entry point. See plugins/perchance_diffusion and
# plugins/anythingxl_diffusion for the reference implementations.

DIFFUSION_BACKENDS: dict[str, dict] = {}


def register_diffusion_backend(
    key: str,
    label: str,
    *,
    worker_factory: Callable,
    is_available: Callable[[], bool] = lambda: True,
    supports_ip_adapter: bool = False,
    get_device_info: Callable[[], str] = lambda: "",
    verify_dialog_cls=None,
    ref_gen_dialog_cls=None,
) -> None:
    """Register a diffusion backend plugin.

    worker_factory(prompts, n, output_dir, **kwargs) must return a QThread with
    progress/image_ready/finished/error pyqtSignals and an abort() method.
    Local backends may additionally accept ref_image_path, ip_adapter_scale,
    base_image_path, img2img_strength, base_image_map keyword arguments.
    """
    DIFFUSION_BACKENDS[key] = {
        "label": label,
        "worker_factory": worker_factory,
        "is_available": is_available,
        "supports_ip_adapter": supports_ip_adapter,
        "get_device_info": get_device_info,
        "verify_dialog_cls": verify_dialog_cls,
        "ref_gen_dialog_cls": ref_gen_dialog_cls,
    }
    _dlog("ai_image_gen.register_diffusion_backend", f"registered {key!r} ({label})")


def available_backends() -> dict[str, dict]:
    """Return the subset of registered backends whose is_available() is True."""
    return {k: v for k, v in DIFFUSION_BACKENDS.items() if v["is_available"]()}


def has_any_backend() -> bool:
    """Return True when at least one diffusion backend plugin is available."""
    return bool(available_backends())


def get_torch_info() -> str:
    """Return the device info string from the first available backend, or ''.

    Called at startup so the info appears in the main window title.
    """
    for entry in available_backends().values():
        info = entry["get_device_info"]()
        if info:
            return info
    return ""


# ─── Image Picker Dialog ──────────────────────────────────────────────────────

class ImagePickerDialog(QDialog):
    """Shows generated images; user selects which to keep."""

    def __init__(
        self,
        parent: QWidget,
        paths: list[str],
        on_accepted: Callable[[dict], None],
        type_map: dict[str, tuple[str, str]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select AI-Generated Images")
        self.resize(860, 560)
        self._paths = list(paths)
        self._on_accepted = on_accepted
        self._type_map: dict[str, tuple[str, str]] = type_map or {}
        self._build_ui()
        self._populate(paths)

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.resize(680, 600)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        root.addWidget(QLabel("Select the images to add to the pack:"))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        # Thumbnail list
        self._list = QListWidget()
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setIconSize(QSize(120, 120))
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._list)

        # Large preview
        self._preview = QLabel("Select an image to preview")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumWidth(320)
        splitter.addWidget(self._preview)
        splitter.setSizes([420, 400])

        # Select-all / deselect-all helpers
        sel_row = QHBoxLayout()
        btn_all = QPushButton("Select All")
        btn_none = QPushButton("Deselect All")
        btn_all.setFixedWidth(90)
        btn_none.setFixedWidth(90)
        btn_all.clicked.connect(self._list.selectAll)
        btn_none.clicked.connect(self._list.clearSelection)
        sel_row.addWidget(btn_all)
        sel_row.addWidget(btn_none)
        sel_row.addStretch()
        self._lbl_count = QLabel("0 selected")
        sel_row.addWidget(self._lbl_count)
        root.addLayout(sel_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _populate(self, paths: list[str]) -> None:
        for path in paths:
            self._add_item(path)

    def add_path(self, path: str) -> None:
        """Called live when the worker delivers an extra image."""
        self._paths.append(path)
        self._add_item(path)

    def _add_item(self, path: str) -> None:
        px = QPixmap(path)
        item = QListWidgetItem(os.path.basename(path))
        if not px.isNull():
            from PyQt6.QtGui import QIcon
            item.setIcon(QIcon(px.scaled(
                120, 120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )))
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setSelected(True)
        self._list.addItem(item)
        self._update_count()

    def _on_selection_changed(self) -> None:
        self._update_count()
        selected = self._list.selectedItems()
        if not selected:
            self._preview.setPixmap(QPixmap())
            self._preview.setText("Select an image to preview")
            return
        path = selected[-1].data(Qt.ItemDataRole.UserRole)
        px = QPixmap(path)
        if px.isNull():
            self._preview.setText("Cannot preview")
            return
        w = max(self._preview.width(), 300)
        h = max(self._preview.height(), 300)
        self._preview.setPixmap(
            px.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _update_count(self) -> None:
        n = len(self._list.selectedItems())
        self._lbl_count.setText(f"{n} selected")

    def _on_ok(self) -> None:
        selected_paths = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._list.selectedItems()
        ]
        self.accept()
        if selected_paths:
            self._on_accepted({p: self._type_map.get(p, ("", "")) for p in selected_paths})


# ─── Main AI Generate Dialog ──────────────────────────────────────────────────

class AiImageGenDialog(QDialog):
    """
    Prompt editor + generate trigger for the perchance.org txt2img service.

    widget_type  : "photos" | "love_lens" | "events"
    on_accepted  : called with list[str] of selected temp-file paths
    """

    def __init__(
        self,
        parent: QWidget,
        widget_type: str,
        on_accepted: Callable[[dict], None],
        output_dir: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._widget_type = widget_type
        self._type_map: dict[str, dict] = WIDGET_TYPES.get(widget_type, {})
        self._modifier_map: dict[str, dict] = PHOTO_MODIFIER_TYPES.get(widget_type, {})
        self._on_accepted = on_accepted
        self._output_dir = output_dir
        self._worker = None
        self._picker: ImagePickerDialog | None = None
        self._ref_image_path: str = ""
        self._base_image_path: str = ""
        self._build_ui()
        self._update_title()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.resize(680, 600)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._stack.addWidget(self._build_form_page())   # 0
        self._stack.addWidget(self._build_progress_page())  # 1
        self._stack.setCurrentIndex(0)

    def _build_form_page(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        # ── Backend selector ──────────────────────────────────────────────
        # Populated dynamically from diffusion backend plugins registered via
        # register_diffusion_backend() (see plugins/*_diffusion).
        self._backends = available_backends()
        if len(self._backends) > 1:
            backend_group = QGroupBox("Backend")
            backend_form = QFormLayout(backend_group)
            self._cmb_backend = QComboBox()
            for key, entry in self._backends.items():
                self._cmb_backend.addItem(entry["label"], key)
            self._cmb_backend.setToolTip(
                "Choose which installed diffusion plugin generates the images."
            )
            backend_form.addRow("Source:", self._cmb_backend)
            layout.addWidget(backend_group)
            self._cmb_backend.currentIndexChanged.connect(self._update_title)
        else:
            self._cmb_backend = None

        # ── Type selector ─────────────────────────────────────────────────
        type_group = QGroupBox("Image Type")
        type_form = QFormLayout(type_group)
        self._cmb_type = QComboBox()
        for key, info in self._type_map.items():
            self._cmb_type.addItem(info["label"], key)
        self._cmb_type.currentIndexChanged.connect(self._on_type_changed)
        self._cmb_type.setToolTip("Character position in the scene. Selects the prompt enhancement and the blueprint reference image.")
        type_form.addRow("Position:", self._cmb_type)
        if self._modifier_map:
            self._cmb_modifier = QComboBox()
            self._cmb_modifier.addItem("(any)", "")
            for key, info in self._modifier_map.items():
                self._cmb_modifier.addItem(info["label"], key)
            self._cmb_modifier.currentIndexChanged.connect(self._on_type_changed)
            self._cmb_modifier.setToolTip(
                "(any): generate images per photo type in a single run.\n"
                "Specific type: generate only that type and enables the blueprint base image."
            )
            type_form.addRow("Photo Type:", self._cmb_modifier)
        else:
            self._cmb_modifier = None
        layout.addWidget(type_group)

        # ── Base prompt ───────────────────────────────────────────────────
        prompt_group = QGroupBox("Base Prompt")
        prompt_layout = QVBoxLayout(prompt_group)
        self._edit_prompt = QTextEdit()
        self._edit_prompt.setPlaceholderText(
            "Describe the subject/character, e.g. "
            '"anime girl, black hair, school uniform"'
        )
        self._edit_prompt.setFixedHeight(70)
        self._edit_prompt.setToolTip(
            "Free-text description of the character or scene.\n"
            "This is appended to the type-specific prompt enhancement."
        )
        prompt_layout.addWidget(self._edit_prompt)
        layout.addWidget(prompt_group)

        # ── Prompt enhancement ────────────────────────────────────────────
        enh_group = QGroupBox("Prompt Enhancement  (pre-filled by type; expand freely)")
        enh_layout = QVBoxLayout(enh_group)
        self._edit_enhancement = QTextEdit()
        self._edit_enhancement.setFixedHeight(90)
        self._edit_enhancement.setToolTip(
            "Auto-filled from the selected position/type. You can freely edit or extend it.\n"
            "These keywords steer composition, lighting and mood before your base prompt."
        )
        enh_layout.addWidget(self._edit_enhancement)
        layout.addWidget(enh_group)

        # ── Image count slider ────────────────────────────────────────────
        count_group = QGroupBox("Number of Images")
        count_layout = QHBoxLayout(count_group)
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(1, 16)
        self._slider.setValue(4)
        self._slider.setTickInterval(1)
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._slider.setToolTip(
            "How many images to generate per prompt.\n"
            "Higher values take proportionally longer but give more results to choose from."
        )
        self._lbl_n = QLabel("4")
        self._lbl_n.setFixedWidth(24)
        self._slider.valueChanged.connect(
            lambda v: self._lbl_n.setText(str(v))
        )
        count_layout.addWidget(self._slider)
        count_layout.addWidget(self._lbl_n)
        layout.addWidget(count_group)

        # ── Character reference image (IP-Adapter, local backend only) ────
        self._ref_group = QGroupBox("Base Image + Character Reference  (IP-Adapter)")
        ref_layout = QVBoxLayout(self._ref_group)

        # Row 1 — Base image (blueprint → img2img structure)
        self._base_row_widget = QWidget()
        base_row = QHBoxLayout(self._base_row_widget)
        base_row.setContentsMargins(0, 0, 0, 0)
        self._lbl_base_thumb = QLabel()
        self._lbl_base_thumb.setFixedSize(64, 64)
        self._lbl_base_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_base_thumb.setStyleSheet("background:#222; border:1px solid #555;")
        base_row.addWidget(self._lbl_base_thumb)
        base_info = QVBoxLayout()
        base_hdr = QLabel("Base image (blueprint):")
        base_hdr.setStyleSheet("font-weight:bold;")
        base_info.addWidget(base_hdr)
        self._lbl_base_path = QLabel("None")
        self._lbl_base_path.setStyleSheet("color: gray;")
        self._lbl_base_path.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        base_info.addWidget(self._lbl_base_path)
        self._btn_base_randomize = QPushButton("Randomize")
        self._btn_base_randomize.setFixedWidth(85)
        self._btn_base_randomize.clicked.connect(self._on_base_randomize)
        self._btn_base_randomize.setToolTip(
            "Pick a different random blueprint for the current position + type.\n"
            "The blueprint defines the composition and pose via img2img."
        )
        base_info.addWidget(self._btn_base_randomize)
        base_row.addLayout(base_info)
        ref_layout.addWidget(self._base_row_widget)

        # Row 2 — Character image (IP-Adapter appearance)
        char_row = QHBoxLayout()
        self._lbl_ref_thumb = QLabel()
        self._lbl_ref_thumb.setFixedSize(64, 64)
        self._lbl_ref_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_ref_thumb.setStyleSheet("background:#222; border:1px solid #555;")
        char_row.addWidget(self._lbl_ref_thumb)
        char_info = QVBoxLayout()
        char_hdr = QLabel("Character image (IP-Adapter):")
        char_hdr.setStyleSheet("font-weight:bold;")
        char_info.addWidget(char_hdr)
        self._lbl_ref_path = QLabel("No image selected")
        self._lbl_ref_path.setStyleSheet("color: gray;")
        self._lbl_ref_path.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        char_info.addWidget(self._lbl_ref_path)
        char_btns = QHBoxLayout()
        self._btn_ref_browse = QPushButton("Browse\u2026")
        self._btn_ref_browse.setFixedWidth(75)
        self._btn_ref_browse.clicked.connect(self._on_ref_browse)
        self._btn_ref_browse.setToolTip("Load any image file as the character appearance reference for IP-Adapter.")
        self._btn_ref_clear = QPushButton("Clear")
        self._btn_ref_clear.setFixedWidth(55)
        self._btn_ref_clear.clicked.connect(self._on_ref_clear)
        self._btn_ref_clear.setToolTip("Remove the character reference image. IP-Adapter will be disabled.")
        char_btns.addWidget(self._btn_ref_browse)
        char_btns.addWidget(self._btn_ref_clear)
        char_btns.addStretch()
        char_info.addLayout(char_btns)
        char_row.addLayout(char_info)
        ref_layout.addLayout(char_row)

        # IP-Adapter scale slider
        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("IP-Adapter scale:"))
        self._slider_ipa = QSlider(Qt.Orientation.Horizontal)
        self._slider_ipa.setRange(10, 100)
        self._slider_ipa.setValue(85)
        self._slider_ipa.setTickInterval(10)
        self._slider_ipa.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._slider_ipa.setToolTip(
            "Controls how strongly the character reference image influences the output (IP-Adapter).\n"
            "0.3\u20130.5 \u2192 loose inspiration (colour palette, rough style).\n"
            "0.6\u20130.8 \u2192 clear character likeness (face shape, hair, outfit).\n"
            "0.9\u20131.0 \u2192 near-copy of the reference (less prompt freedom)."
        )
        self._lbl_ipa_scale = QLabel("0.85")
        self._lbl_ipa_scale.setFixedWidth(36)
        self._slider_ipa.valueChanged.connect(
            lambda v: self._lbl_ipa_scale.setText(f"{v / 100:.2f}")
        )
        scale_row.addWidget(self._slider_ipa)
        scale_row.addWidget(self._lbl_ipa_scale)
        ref_layout.addLayout(scale_row)
        # img2img strength (only relevant when a base image is set)
        str_row = QHBoxLayout()
        str_row.addWidget(QLabel("img2img strength:"))
        self._slider_strength = QSlider(Qt.Orientation.Horizontal)
        self._slider_strength.setRange(20, 95)
        self._slider_strength.setValue(80)
        self._slider_strength.setTickInterval(5)
        self._slider_strength.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._slider_strength.setToolTip(
            "How much noise is added to the blueprint before denoising (img2img strength).\n"
            "0.5\u20130.6 \u2192 output stays close to the blueprint silhouette.\n"
            "0.7\u20130.8 \u2192 balanced: pose is kept, character detail can emerge.\n"
            "0.85\u20130.95 \u2192 mostly re-drawn from prompt + IP-Adapter; blueprint only guides composition."
        )
        self._lbl_strength = QLabel("0.80")
        self._lbl_strength.setFixedWidth(36)
        self._slider_strength.valueChanged.connect(
            lambda v: self._lbl_strength.setText(f"{v / 100:.2f}")
        )
        str_row.addWidget(self._slider_strength)
        str_row.addWidget(self._lbl_strength)
        ref_layout.addLayout(str_row)
        gen_row = QHBoxLayout()
        gen_row.addWidget(QLabel("Count:"))
        self._slider_ref_n = QSlider(Qt.Orientation.Horizontal)
        self._slider_ref_n.setRange(1, 8)
        self._slider_ref_n.setValue(2)
        self._slider_ref_n.setTickInterval(1)
        self._slider_ref_n.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._slider_ref_n.setToolTip("Number of reference images to generate via Perchance. Pick one from the results to use as the character IP-Adapter image.")
        self._lbl_ref_n = QLabel("2")
        self._lbl_ref_n.setFixedWidth(18)
        self._slider_ref_n.valueChanged.connect(lambda v: self._lbl_ref_n.setText(str(v)))
        self._btn_ref_gen = QPushButton("Generate with Perchance\u2026")
        self._btn_ref_gen.clicked.connect(self._on_ref_gen_perchance)
        self._btn_ref_gen.setToolTip(
            "Generate character reference images via Perchance.org using the current prompt.\n"
            "A preview dialog lets you pick the best result as the IP-Adapter character image."
        )
        gen_row.addWidget(self._slider_ref_n)
        gen_row.addWidget(self._lbl_ref_n)
        gen_row.addSpacing(8)
        gen_row.addWidget(self._btn_ref_gen)
        ref_layout.addLayout(gen_row)
        self._btn_ref_gen.setVisible("perchance" in self._backends)
        self._ref_group.setVisible(self._current_backend_supports_ip_adapter())
        layout.addWidget(self._ref_group)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._btn_gen_single = QPushButton("Generate n images  (current type)")
        self._btn_gen_single.clicked.connect(self._on_gen_single)
        self._btn_gen_single.setToolTip(
            "Generate n images for the currently selected position and photo type.\n"
            "Uses the blueprint as the structural base and the character image for appearance (if set)."
        )
        self._btn_gen_all = QPushButton(
            "Generate n \u00d7 types  (all types from table)"
        )
        self._btn_gen_all.clicked.connect(self._on_gen_all)
        self._btn_gen_all.setToolTip(
            "Generate n images for every position/type in the table.\n"
            "Each entry gets its own randomly selected blueprint. The same character reference is used throughout."
        )
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_gen_single)
        btn_row.addWidget(self._btn_gen_all)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        # Pre-fill enhancement for the first type
        self._on_type_changed(0)
        if self._cmb_backend:
            self._cmb_backend.currentIndexChanged.connect(self._on_backend_changed)
        return scroll

    def _current_backend_key(self) -> str:
        if self._cmb_backend:
            return self._cmb_backend.currentData()
        return next(iter(self._backends), "")

    def _current_backend_supports_ip_adapter(self) -> bool:
        entry = self._backends.get(self._current_backend_key())
        return bool(entry and entry["supports_ip_adapter"])

    def _on_backend_changed(self, _index: int = 0) -> None:
        self._ref_group.setVisible(self._current_backend_supports_ip_adapter())
        self._update_title()

    def _build_progress_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addStretch()
        self._lbl_progress = QLabel("Starting…")
        self._lbl_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl_progress)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # indeterminate
        layout.addWidget(self._progress_bar)
        layout.addStretch()

        self._btn_abort = QPushButton("Cancel Generation")
        self._btn_abort.clicked.connect(self._on_abort)
        layout.addWidget(self._btn_abort, 0, Qt.AlignmentFlag.AlignCenter)
        return page

    # ── Slots ──────────────────────────────────────────────────────────────

    def _update_title(self, _index: int = 0) -> None:
        key = self._current_backend_key()
        entry = self._backends.get(key)
        label = entry["label"] if entry else "?"
        device_info = entry["get_device_info"]() if entry else ""
        if device_info:
            self.setWindowTitle(f"AI Image Generator – {label} [{device_info}]")
        else:
            self.setWindowTitle(f"AI Image Generator – {label}")

    def _on_ref_gen_perchance(self) -> None:
        pos_key = self._cmb_type.currentData() or ""
        sel_mod = self._cmb_modifier.currentData() if self._cmb_modifier else ""
        enh = self._edit_enhancement.toPlainText().strip()
        base = self._edit_prompt.toPlainText().strip()
        mod_enh = self._modifier_map.get(sel_mod, {}).get("prompt_enhancement", "") if sel_mod else ""
        prompt = self._assemble_prompt(enh, mod_enh, base)
        if not prompt:
            from ui.dialogs import show_warning
            show_warning(self, "Generate Reference", "Please enter a prompt first.",
                         tag="AiImageGenDialog._on_ref_gen_perchance")
            return
        n = self._slider_ref_n.value()
        _dlog("AiImageGenDialog._on_ref_gen_perchance", f"generating {n} reference image(s) via Perchance")
        neg_override = self._type_map.get(pos_key, {}).get("negative_prompt", "")
        perchance_entry = DIFFUSION_BACKENDS.get("perchance")
        if not perchance_entry or not perchance_entry.get("ref_gen_dialog_cls"):
            from ui.dialogs import show_warning
            show_warning(self, "Generate Reference", "The Perchance plugin is not installed.",
                         tag="AiImageGenDialog._on_ref_gen_perchance")
            return
        dlg = perchance_entry["ref_gen_dialog_cls"](self, [(prompt, pos_key, sel_mod, neg_override)], n)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_path:
            self._set_ref_image(dlg.selected_path)
            _dlog("AiImageGenDialog._on_ref_gen_perchance",
                  f"reference set: {dlg.selected_path!r}")

    def _on_base_randomize(self) -> None:
        key = self._cmb_type.currentData() or ""
        mod_key = self._cmb_modifier.currentData() if self._cmb_modifier else ""
        bp = self._find_blueprint_for(key, mod_key or "")
        if bp:
            self._set_base_image(bp)
            _dlog("AiImageGenDialog._on_base_randomize", f"new base: {bp!r}")

    def _on_ref_browse(self) -> None:
        from modules.image_utils import ASSET_FILTER  # noqa: F401 (already imported)
        path, _ = QFileDialog.getOpenFileName(self, "Select Reference Image", "", ASSET_FILTER)
        if path:
            self._set_ref_image(path)
            _dlog("AiImageGenDialog._on_ref_browse", f"reference image set: {path!r}")

    def _on_ref_clear(self) -> None:
        self._set_ref_image("")
        _dlog("AiImageGenDialog._on_ref_clear", "reference image cleared")

    # Maps widget_type to the game-specific blueprint subfolder name.
    _GAME_BLUEPRINT_SUBDIR: dict[str, str] = {
        "photos": "snapshot",
        "photos_lewdshores": "lewdshores",
    }

    def _find_blueprint_for(self, pos_key: str, mod_key: str) -> str | None:
        """Return a random blueprint PNG for (pos_key, mod_key); fall back to a raw pack asset."""
        import glob as _glob
        bp_root = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "blueprints",
        )

        def _search_dir(bp_dir: str) -> str | None:
            if not os.path.isdir(bp_dir):
                return None
            for pattern in (
                f"{pos_key}_{mod_key}_*.png" if mod_key else None,
                f"{pos_key}_*.png",
            ):
                if pattern is None:
                    continue
                matches = _glob.glob(os.path.join(bp_dir, pattern))
                if matches:
                    return random.choice(matches)
            return None

        # Use only the game-specific subfolder; root is not searched directly.
        game_subdir = self._GAME_BLUEPRINT_SUBDIR.get(self._widget_type)
        if game_subdir:
            result = _search_dir(os.path.join(bp_root, game_subdir))
            if result:
                return result
        # Fallback: scan exported test-pack Data dirs for any image named pos_key* or *_pos_key*
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        asset_roots = [
            os.path.join(project_root, "tests", "bonuscontent", "exported", "Snapshot!"),
            os.path.join(project_root, "tests", "bonuscontent", "exported", "Snapshot! LewdShores"),
        ]
        _EXTS = (".png", ".pna", ".dat", ".jpa")
        candidates: list[str] = []
        for root in asset_roots:
            if not os.path.isdir(root):
                continue
            for pack in os.listdir(root):
                data_dir = os.path.join(root, pack, "Data")
                if not os.path.isdir(data_dir):
                    continue
                for fname in os.listdir(data_dir):
                    stem, ext = os.path.splitext(fname)
                    if ext.lower() not in _EXTS:
                        continue
                    # Accept files whose name starts with pos_key (e.g. "standing_01")
                    if stem.startswith(pos_key):
                        candidates.append(os.path.join(data_dir, fname))
        if candidates:
            return random.choice(candidates)
        return None

    def _set_ref_image(self, path: str) -> None:
        """Update the character reference image thumbnail."""
        self._ref_image_path = path
        if path:
            px = QPixmap(path)
            if not px.isNull():
                self._lbl_ref_thumb.setPixmap(px.scaled(
                    64, 64,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
            else:
                self._lbl_ref_thumb.clear()
            self._lbl_ref_path.setText(os.path.basename(path))
            self._lbl_ref_path.setStyleSheet("")
        else:
            self._lbl_ref_thumb.clear()
            self._lbl_ref_path.setText("No image selected")
            self._lbl_ref_path.setStyleSheet("color: gray;")

    def _set_base_image(self, path: str) -> None:
        """Update the base blueprint image thumbnail."""
        self._base_image_path = path
        if path:
            px = QPixmap(path)
            if not px.isNull():
                self._lbl_base_thumb.setPixmap(px.scaled(
                    64, 64,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
            else:
                self._lbl_base_thumb.clear()
            self._lbl_base_path.setText(os.path.basename(path))
            self._lbl_base_path.setStyleSheet("")
        else:
            self._lbl_base_thumb.clear()
            self._lbl_base_path.setText("None")
            self._lbl_base_path.setStyleSheet("color: gray;")

    def _on_type_changed(self, _index: int) -> None:
        key = self._cmb_type.currentData()
        if key and key in self._type_map:
            self._edit_enhancement.setPlainText(
                self._type_map[key]["prompt_enhancement"]
            )
        mod_key = self._cmb_modifier.currentData() if self._cmb_modifier else ""
        self._base_row_widget.setVisible(mod_key != "")
        bp = self._find_blueprint_for(key or "", mod_key or "")
        if bp and mod_key != "":
            self._set_base_image(bp)
            _dlog("AiImageGenDialog._on_type_changed",
                  f"auto-base: {bp!r}  pos={key!r} mod={mod_key!r}")

    def _build_full_prompt(self, type_key: str) -> str:
        base = self._edit_prompt.toPlainText().strip()
        if type_key in self._type_map:
            enhancement = self._type_map[type_key]["prompt_enhancement"]
        else:
            enhancement = self._edit_enhancement.toPlainText().strip()
        parts = [p for p in [enhancement, base] if p]
        return ", ".join(parts)

    def _assemble_prompt(self, *parts: str) -> str:
        """Join non-empty parts; prepend solo tag for character widget types."""
        filtered = [p for p in parts if p]
        if self._widget_type in _CHAR_WIDGET_TYPES:
            filtered.insert(0, "solo, 1girl")
        return ", ".join(filtered)

    def _on_gen_single(self) -> None:
        pos_key = self._cmb_type.currentData() or ""
        sel_mod = self._cmb_modifier.currentData() if self._cmb_modifier else ""
        enh = self._edit_enhancement.toPlainText().strip()
        base = self._edit_prompt.toPlainText().strip()
        n = self._slider.value()
        neg_override = self._type_map.get(pos_key, {}).get("negative_prompt", "")
        if sel_mod == "" and self._modifier_map:
            # (any) selected — one prompt per modifier type for this position
            prompts: list[tuple[str, str, str, str]] = []
            for mod_key, mod_info in self._modifier_map.items():
                mod_enh = mod_info.get("prompt_enhancement", "")
                prompt = self._assemble_prompt(enh, mod_enh, base)
                if prompt:
                    prompts.append((prompt, pos_key, mod_key, neg_override))
            if not prompts:
                return
            self._start_worker(prompts, n)
        else:
            mod_enh = self._modifier_map.get(sel_mod, {}).get("prompt_enhancement", "") if sel_mod else ""
            prompt = self._assemble_prompt(enh, mod_enh, base)
            if not prompt:
                self._lbl_progress.setText("Please enter a prompt.")
                return
            self._start_worker([(prompt, pos_key, sel_mod, neg_override)], n)

    def _on_gen_all(self) -> None:
        base = self._edit_prompt.toPlainText().strip()
        sel_mod = self._cmb_modifier.currentData() if self._cmb_modifier else ""
        n = self._slider.value()
        prompts: list[tuple[str, str, str, str]] = []
        base_image_map: dict[tuple, str] = {}
        if sel_mod == "" and self._modifier_map:
            # (any) selected — generate for every position × modifier combination
            for pos_key, pos_info in self._type_map.items():
                neg_override = pos_info.get("negative_prompt", "")
                for mod_key, mod_info in self._modifier_map.items():
                    prompt = self._assemble_prompt(
                        pos_info["prompt_enhancement"],
                        mod_info.get("prompt_enhancement", ""),
                        base,
                    )
                    if prompt:
                        prompts.append((prompt, pos_key, mod_key, neg_override))
                        bp = self._find_blueprint_for(pos_key, mod_key)
                        if bp:
                            base_image_map[(pos_key, mod_key)] = bp
        else:
            mod_enh = self._modifier_map.get(sel_mod, {}).get("prompt_enhancement", "") if sel_mod else ""
            for pos_key, pos_info in self._type_map.items():
                prompt = self._assemble_prompt(
                    pos_info["prompt_enhancement"], mod_enh, base
                )
                if prompt:
                    prompts.append((prompt, pos_key, sel_mod, pos_info.get("negative_prompt", "")))
                    bp = self._find_blueprint_for(pos_key, sel_mod or "")
                    if bp:
                        base_image_map[(pos_key, sel_mod)] = bp
        if not prompts:
            return
        self._start_worker(prompts, n, base_image_map=base_image_map or None)

    def _start_worker(self, prompts: list[tuple[str, str, str, str]], n: int,
                      base_image_map: dict | None = None) -> None:
        self._stack.setCurrentIndex(1)
        key = self._current_backend_key()
        entry = self._backends.get(key)
        self._active_backend = key
        if not entry:
            self._on_worker_error(f"No diffusion backend available (requested {key!r}).")
            return
        self._lbl_progress.setText(f"Starting {entry['label']} …")
        ref = self._ref_image_path or None
        scale = self._slider_ipa.value() / 100.0 if hasattr(self, "_slider_ipa") else 0.5
        base = self._base_image_path or None
        strength = self._slider_strength.value() / 100.0 if hasattr(self, "_slider_strength") else 0.6
        worker = entry["worker_factory"](
            prompts, n, self._output_dir,
            ref_image_path=ref, ip_adapter_scale=scale,
            base_image_path=base, img2img_strength=strength,
            base_image_map=base_image_map,
        )
        worker.progress.connect(self._lbl_progress.setText)
        worker.finished.connect(self._on_worker_done)
        worker.error.connect(self._on_worker_error)
        worker.image_ready.connect(
            lambda path, pk, mk: self._on_image_ready(path, pk, mk)
        )
        if hasattr(worker, "session_required"):
            worker.session_required.connect(self._on_session_required)
        self._worker = worker
        worker.start()

    def _on_image_ready(self, path: str, pos_key: str, mod_key: str) -> None:
        if self._picker:
            self._picker.add_path(path)

    def _on_session_required(self) -> None:
        """Show the browser verification dialog when Turnstile blocks the tokenless path."""
        if not self._worker:
            return
        entry = self._backends.get(self._active_backend)
        verify_cls = entry["verify_dialog_cls"] if entry else None
        if not verify_cls:
            self._worker.abort()
            return
        dlg = verify_cls(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if self._worker:
                self._worker.set_session(dlg.user_key, dlg.ad_access_code)
        else:
            if self._worker:
                self._worker.abort()

    def _on_worker_done(self, pairs: list) -> None:
        _dlog("AiImageGenDialog._on_worker_done", f"{len(pairs)} images")
        self._worker = None
        if not pairs:
            label = self._backends.get(self._active_backend, {}).get("label", self._active_backend)
            msg = f"{label} generated no images.\nCheck the debug log or your internet connection."
            show_error(self, "AI Generate", msg, tag="AiImageGenDialog._on_worker_done")
            self._stack.setCurrentIndex(0)
            return
        self.hide()
        paths = [p for p, _, _ in pairs]
        type_map = {p: (pk, mk) for p, pk, mk in pairs}
        picker = ImagePickerDialog(self.parent(), paths, self._on_accepted, type_map)
        picker.exec()
        self.accept()

    def _on_worker_error(self, msg: str) -> None:
        _dlog("AiImageGenDialog._on_worker_error", msg)
        self._worker = None
        label = self._backends.get(self._active_backend, {}).get("label", self._active_backend)
        missing = any(k in msg for k in ("No module named", "ModuleNotFoundError"))
        hint = (
            "\n\nMake sure the required packages for this plugin are installed\n"
            "(run cli.bat to update the venv)."
            if missing else ""
        )
        detail = f"{label} generation failed:\n{msg}{hint}"
        show_error(self, "AI Generate", detail, tag="AiImageGenDialog._on_worker_error")
        self._stack.setCurrentIndex(0)

    def _on_abort(self) -> None:
        if self._worker:
            self._worker.abort()
            self._worker.wait(3000)
            self._worker = None
        self._stack.setCurrentIndex(0)

    def closeEvent(self, event) -> None:
        if self._worker:
            self._worker.abort()
            self._worker.wait(3000)
        super().closeEvent(event)


# ─── Convenience launcher ─────────────────────────────────────────────────────

def open_ai_generate_dialog(
    parent: QWidget,
    widget_type: str,
    on_accepted: Callable[[dict], None],
    output_dir: str | None = None,
) -> None:
    """Show the AI image generation dialog for *widget_type*."""
    if not has_any_backend():
        show_error(
            parent, "AI Generate",
            "No diffusion backend plugin is installed.\n"
            "Drop a plugin such as perchance_diffusion or anythingxl_diffusion into plugins/.",
            tag="open_ai_generate_dialog",
        )
        return
    dlg = AiImageGenDialog(parent, widget_type, on_accepted, output_dir)
    dlg.exec()
