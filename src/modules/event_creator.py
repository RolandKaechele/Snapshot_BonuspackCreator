"""Native starter workflow for building a branched city-event scene."""

import json
import os
import re

from PyQt6.QtWidgets import (  # type: ignore
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QPlainTextEdit,
    QVBoxLayout,
)

from modules.image_utils import ASSET_FILTER
from modules.picture_widget import SNAPSHOT_COLORS, SNAPSHOT_TYPES
from ui.dialogs import show_warning


def suggest_scene_name(events: list[dict]) -> str:
    """Return the first unused CityEvent name."""
    names = {
        event.get("name", "").casefold()
        for event in events
        if event.get("type") == "dialog"
    }
    index = 1
    while f"CityEvent{index}".casefold() in names:
        index += 1
    return f"CityEvent{index}"


def suggest_dialog_id(pack_data: dict) -> int:
    """Choose an unused dialogue ID starting at the pack's reserved range."""
    try:
        candidate = int(str(pack_data.get("id_range", "")).split("-", 1)[0])
    except (TypeError, ValueError):
        candidate = 130000

    used_ids = set()
    for event in pack_data.get("events", []):
        if event.get("type") != "dialog":
            continue
        try:
            dialog = json.loads(event.get("content", "") or "{}")
            used_ids.add(int(dialog["dID"]))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
    while candidate in used_ids:
        candidate += 1
    return candidate


def suggest_photo_name(pack_id: str, photos: list[dict]) -> str:
    """Return an unused pack-prefixed photo filename stem."""
    prefix = re.sub(r"[^A-Za-z0-9_]", "", pack_id or "event") or "event"
    used_names = {photo.get("name", "") for photo in photos}
    index = 1
    while f"{prefix}{index}" in used_names:
        index += 1
    return f"{prefix}{index}"


def build_event_dialog_data(
    dialog_id: int,
    speaker: str,
    prompt: str,
    first_choice: str,
    second_choice: str,
    closing_line: str,
    event_type: str = "normal",
    photo_name: str = "",
    sound_name: str = "",
) -> dict:
    """Create a flat VIDE dialogue with a two-option branch and closing node."""
    opening_commands = []
    if event_type == "explosion":
        opening_commands = [
            {"key": "showImage", "val": "event_explosionLens_background"},
            {"key": "pulseBackground", "val": ""},
        ]
        if sound_name.strip():
            opening_commands.append({"key": "playSound", "val": sound_name.strip()})

    reward_commands = []
    if photo_name:
        reward_commands = [
            {"key": "showEventPhoto", "val": photo_name},
            {"key": "mod_addEventSellablePhoto", "val": photo_name},
        ]

    nodes = [
        {
            "tag": "SKIP", "text": "", "extraData": "",
            "oNPC": 1, "oSet": -1, "oAct": -1,
            "vars": opening_commands,
        },
        {
            "tag": speaker, "text": prompt, "extraData": "",
            "oNPC": -1, "oSet": 0, "oAct": -1,
            "vars": [],
        },
        {
            "tag": "You", "text": first_choice, "extraData": "",
            "oNPC": 4, "oSet": -1, "oAct": -1,
            "vars": reward_commands,
        },
        {
            "tag": "You", "text": second_choice, "extraData": "",
            "oNPC": 4, "oSet": -1, "oAct": -1,
            "vars": [],
        },
        {
            "tag": speaker, "text": closing_line, "extraData": "",
            "oNPC": -1, "oSet": -1, "oAct": -1,
            "vars": [{"key": "endEvent", "val": ""}],
        },
    ]

    result = {
        "dID": int(dialog_id),
        "startPoint": 0,
        "loadTag": "",
        "previewPanning": False,
        "showSettings": True,
        "npcDiags": len(nodes),
        "playerDiags": 1,
        "actionNodes": 0,
    }
    for index, node in enumerate(nodes):
        result.update({
            f"nd_ID_{index}": index,
            f"nd_tag_{index}": node["tag"],
            f"nd_text_{index}": node["text"],
            f"nd_extraData_{index}": node["extraData"],
            f"nd_oNPC_{index}": node["oNPC"],
            f"nd_oSet_{index}": node["oSet"],
            f"nd_oAct_{index}": node["oAct"],
            f"nd_expand_{index}": True,
            f"nd_rect_{index}": [180 + index * 220, 180],
            f"nd_vars{index}": len(node["vars"]),
        })
        for var_index, command in enumerate(node["vars"]):
            result[f"nd_varKey_{index}_{var_index}"] = command["key"]
            result[f"nd_var_{index}_{var_index}"] = command["val"]

    result.update({
        "pd_ID_0": 0,
        "pd_pTag_0": "",
        "pd_rect_0": [680, 610],
        "pd_expand_0": True,
        "pd_vars0": 0,
        "pd_comSize_0": 2,
    })
    for index, (text, answer_node) in enumerate((
        (first_choice, 2),
        (second_choice, 3),
    )):
        result.update({
            f"pd_0_com_{index}iSet": 0,
            f"pd_0_com_{index}oAns": answer_node,
            f"pd_0_com_{index}oAct": -1,
            f"pd_0_com_{index}text": text,
            f"pd_0_com_{index}extraD": "",
        })
    return result


class EventBuilderDialog(QDialog):
    """Collect event details and optional photo metadata for a starter scene."""

    def __init__(self, pack_data: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Build City Event")
        self.setMinimumWidth(480)
        self._pack_data = pack_data
        events = pack_data.get("events", [])
        self._existing_names = {
            event.get("name", "").casefold()
            for event in events
            if event.get("type") == "dialog"
        }
        self._dialog_id = suggest_dialog_id(pack_data)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self._name = QLineEdit(suggest_scene_name(self._pack_data.get("events", [])))
        self._type = QComboBox()
        self._type.addItems(["normal", "explosion"])
        current_type = self._pack_data.get("event_type", "normal")
        self._type.setCurrentIndex(max(self._type.findText(current_type), 0))
        self._speaker = QLineEdit("Aya")
        self._prompt = QPlainTextEdit("Do you want to use the lens?")
        self._prompt.setMaximumHeight(72)
        self._first_choice = QLineEdit("Use the lens")
        self._second_choice = QLineEdit("Walk away")
        self._closing = QLineEdit("See you around!")
        self._sound = QLineEdit("boom")
        self._type.currentTextChanged.connect(
            lambda value: self._sound.setEnabled(value == "explosion")
        )
        self._sound.setEnabled(current_type == "explosion")

        form.addRow("Scene name:", self._name)
        form.addRow("Event type:", self._type)
        form.addRow("Speaker:", self._speaker)
        form.addRow("Dialogue:", self._prompt)
        form.addRow("First choice:", self._first_choice)
        form.addRow("Second choice:", self._second_choice)
        form.addRow("Closing line:", self._closing)
        form.addRow("Explosion sound:", self._sound)
        form.addRow("Dialogue ID:", QLabel(str(self._dialog_id)))

        photo_row = QHBoxLayout()
        self._photo_path = QLineEdit()
        self._photo_path.setReadOnly(True)
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self._browse_photo)
        photo_row.addWidget(self._photo_path, 1)
        photo_row.addWidget(btn_browse)
        form.addRow("Reward photo (optional):", photo_row)

        traits_row = QHBoxLayout()
        self._photo_type = QComboBox()
        self._photo_type.addItems(SNAPSHOT_TYPES)
        self._photo_type.setCurrentText("nude")
        self._photo_color = QComboBox()
        self._photo_color.addItems(SNAPSHOT_COLORS)
        self._photo_color.setCurrentText("red")
        traits_row.addWidget(QLabel("Type:"))
        traits_row.addWidget(self._photo_type)
        traits_row.addWidget(QLabel("Color:"))
        traits_row.addWidget(self._photo_color)
        form.addRow("Photo traits:", traits_row)

        note = QLabel(
            "Creates a five-node scene with a two-answer branch and an endEvent. "
            "If a reward photo is selected, it is added to the pack and unlocked "
            "by the first choice."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_photo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Event Reward Photo", "", ASSET_FILTER
        )
        if path:
            self._photo_path.setText(path)

    def _accept_if_valid(self) -> None:
        name = self._name.text().strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            show_warning(
                self, "Invalid Scene Name",
                "Use only letters, numbers, underscores, and hyphens.",
                tag="EventBuilderDialog._accept_if_valid",
            )
            return
        if name.casefold() in self._existing_names:
            show_warning(
                self, "Scene Already Exists",
                "Choose a name that is not already used by another dialog scene.",
                tag="EventBuilderDialog._accept_if_valid",
            )
            return
        required = (
            self._prompt.toPlainText().strip(),
            self._first_choice.text().strip(),
            self._second_choice.text().strip(),
            self._closing.text().strip(),
        )
        if not all(required):
            show_warning(
                self, "Missing Event Text",
                "Dialogue, both choices, and the closing line are required.",
                tag="EventBuilderDialog._accept_if_valid",
            )
            return
        photo_path = self._photo_path.text().strip()
        if photo_path and not os.path.isfile(photo_path):
            show_warning(
                self, "Reward Photo Not Found",
                "The selected photo no longer exists. Select another file or clear the field.",
                tag="EventBuilderDialog._accept_if_valid",
            )
            return
        self.accept()

    def event_data(self) -> dict:
        """Return validated form values after the dialog is accepted."""
        return {
            "name": self._name.text().strip(),
            "event_type": self._type.currentText(),
            "speaker": self._speaker.text().strip(),
            "prompt": self._prompt.toPlainText().strip(),
            "first_choice": self._first_choice.text().strip(),
            "second_choice": self._second_choice.text().strip(),
            "closing_line": self._closing.text().strip(),
            "sound_name": self._sound.text().strip(),
            "dialog_id": self._dialog_id,
            "photo_path": self._photo_path.text().strip(),
            "photo_type": self._photo_type.currentText(),
            "photo_color": self._photo_color.currentText(),
        }
