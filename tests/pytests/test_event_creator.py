"""Tests for the native city-event builder's VIDE scene generator."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from modules.event_creator import (
    EventBuilderDialog,
    build_event_dialog_data,
    suggest_dialog_id,
    suggest_photo_name,
    suggest_scene_name,
)
from modules.event_widget import EventWidget, _extract_nodes
from modules.pack_manager import PackManager


def test_suggest_scene_name_uses_first_available_name():
    events = [
        {"type": "dialog", "name": "CityEvent1"},
        {"type": "background", "name": "CityEvent2"},
    ]
    assert suggest_scene_name(events) == "CityEvent2"


def test_suggest_dialog_id_uses_pack_range_and_skips_existing_ids():
    events = [
        {"type": "dialog", "content": '{"dID": 120050}'},
        {"type": "dialog", "content": '{"dID": 120051}'},
        {"type": "background", "content": ""},
    ]
    assert suggest_dialog_id({"id_range": "120050-120149", "events": events}) == 120052


def test_suggest_dialog_id_uses_default_when_range_is_missing():
    assert suggest_dialog_id({"events": []}) == 130000


def test_suggest_photo_name_sanitizes_prefix_and_avoids_collisions():
    photos = [{"name": "mypack1"}, {"name": "mypack2"}]
    assert suggest_photo_name("my-pack", photos) == "mypack3"


def test_builder_dialog_defaults_to_unused_scene_and_dialog_id(qtbot):
    pack_data = {
        "id_range": "120050-120149",
        "event_type": "explosion",
        "events": [
            {"type": "dialog", "name": "CityEvent1", "content": '{"dID": 120050}'},
        ],
    }
    dialog = EventBuilderDialog(pack_data)
    qtbot.addWidget(dialog)
    assert dialog._name.text() == "CityEvent2"
    assert dialog._dialog_id == 120051
    assert dialog._sound.isEnabled()


def test_city_events_widget_exposes_builder_action(qtbot):
    widget = EventWidget(PackManager())
    qtbot.addWidget(widget)
    assert widget._btn_build_event.text() == "Build Event…"


def test_built_scene_has_two_valid_choices_and_closes():
    data = build_event_dialog_data(
        120050, "Aya", "Use the lens?", "Use it", "Walk away", "Goodbye"
    )
    nodes = _extract_nodes(data)
    assert data["dID"] == 120050
    assert len(nodes) == 5
    assert nodes[1]["oSet"] == 0
    assert nodes[2]["oNPC"] == nodes[3]["oNPC"] == 4
    assert nodes[4]["vars"] == [{"key": "endEvent", "val": ""}]
    assert data["pd_comSize_0"] == 2
    assert data["pd_0_com_0oAns"] == 2
    assert data["pd_0_com_1oAns"] == 3


def test_explosion_scene_includes_builtin_visuals_and_optional_sound():
    data = build_event_dialog_data(
        130000, "Aya", "What happened?", "Look", "Leave", "All clear",
        event_type="explosion", sound_name="boom",
    )
    nodes = _extract_nodes(data)
    assert nodes[0]["vars"] == [
        {"key": "showImage", "val": "event_explosionLens_background"},
        {"key": "pulseBackground", "val": ""},
        {"key": "playSound", "val": "boom"},
    ]


def test_photo_reward_is_unlocked_on_first_choice_only():
    data = build_event_dialog_data(
        130000, "Aya", "Take a photo?", "Take it", "Leave", "Done",
        photo_name="mypack1",
    )
    nodes = _extract_nodes(data)
    assert nodes[2]["vars"] == [
        {"key": "showEventPhoto", "val": "mypack1"},
        {"key": "mod_addEventSellablePhoto", "val": "mypack1"},
    ]
    assert nodes[3]["vars"] == []
