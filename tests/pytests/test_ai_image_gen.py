"""Tests for ai_image_gen — type/modifier dictionaries and dialog logic (no network)."""

import pytest


# ── Module fixture ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def aig(qapp):  # noqa: ARG001
    import modules.ai_image_gen as m
    return m


# ── PHOTO_TYPES ───────────────────────────────────────────────────────────────

def test_photo_types_has_upskirt(aig):
    assert "upskirt" in aig.PHOTO_TYPES


def test_photo_types_all_have_label_and_prompt(aig):
    for key, info in aig.PHOTO_TYPES.items():
        assert "label" in info, f"PHOTO_TYPES[{key!r}] missing 'label'"
        assert "prompt_enhancement" in info, f"PHOTO_TYPES[{key!r}] missing 'prompt_enhancement'"


# ── LEWD_SHORES_PHOTO_TYPES ───────────────────────────────────────────────────

def test_lewd_shores_photo_types_not_empty(aig):
    assert len(aig.LEWD_SHORES_PHOTO_TYPES) >= 1


def test_lewd_shores_photo_types_all_have_label_and_prompt(aig):
    for key, info in aig.LEWD_SHORES_PHOTO_TYPES.items():
        assert "label" in info
        assert "prompt_enhancement" in info


# ── SNAPSHOT_PHOTO_MODIFIERS ──────────────────────────────────────────────────

def test_snapshot_photo_modifiers_has_plain(aig):
    assert "plain" in aig.SNAPSHOT_PHOTO_MODIFIERS


def test_snapshot_photo_modifiers_keys_match_snapshot_types(aig):
    from modules.picture_widget import SNAPSHOT_TYPES
    for key in aig.SNAPSHOT_PHOTO_MODIFIERS:
        assert key in SNAPSHOT_TYPES, f"modifier key {key!r} not in SNAPSHOT_TYPES"


# ── LEWD_SHORES_PHOTO_MODIFIERS ───────────────────────────────────────────────

def test_lewd_shores_photo_modifiers_keys_match_lewd_types(aig):
    from modules.picture_widget import LEWD_TYPES
    for key in aig.LEWD_SHORES_PHOTO_MODIFIERS:
        assert key in LEWD_TYPES, f"modifier key {key!r} not in LEWD_TYPES"


# ── WIDGET_TYPES routing ──────────────────────────────────────────────────────

def test_widget_types_photos_entry(aig):
    assert aig.WIDGET_TYPES["photos"] is aig.PHOTO_TYPES


def test_widget_types_photos_lewdshores_entry(aig):
    assert aig.WIDGET_TYPES["photos_lewdshores"] is aig.LEWD_SHORES_PHOTO_TYPES


def test_widget_types_love_lens_entry(aig):
    assert aig.WIDGET_TYPES["love_lens"] is aig.LOVE_LENS_TYPES


def test_widget_types_events_entry(aig):
    assert aig.WIDGET_TYPES["events"] is aig.EVENT_TYPES


# ── PHOTO_MODIFIER_TYPES routing ──────────────────────────────────────────────

def test_photo_modifier_types_photos_entry(aig):
    assert aig.PHOTO_MODIFIER_TYPES["photos"] is aig.SNAPSHOT_PHOTO_MODIFIERS


def test_photo_modifier_types_lewdshores_entry(aig):
    assert aig.PHOTO_MODIFIER_TYPES["photos_lewdshores"] is aig.LEWD_SHORES_PHOTO_MODIFIERS


# ── AiImageGenDialog — form builds without error ──────────────────────────────

@pytest.fixture()
def dialog_photos(qtbot):
    from modules.ai_image_gen import AiImageGenDialog
    dlg = AiImageGenDialog(None, "photos", lambda d: None)
    qtbot.addWidget(dlg)
    return dlg


@pytest.fixture()
def dialog_lewdshores(qtbot):
    from modules.ai_image_gen import AiImageGenDialog
    dlg = AiImageGenDialog(None, "photos_lewdshores", lambda d: None)
    qtbot.addWidget(dlg)
    return dlg


def test_dialog_photos_modifier_combo_has_any(dialog_photos):
    assert dialog_photos._cmb_modifier is not None
    assert dialog_photos._cmb_modifier.itemData(0) == ""
    assert dialog_photos._cmb_modifier.itemText(0) == "(any)"


def test_dialog_photos_modifier_combo_count(dialog_photos, aig):
    # (any) + one entry per modifier
    expected = 1 + len(aig.SNAPSHOT_PHOTO_MODIFIERS)
    assert dialog_photos._cmb_modifier.count() == expected


def test_dialog_lewdshores_modifier_combo_count(dialog_lewdshores, aig):
    expected = 1 + len(aig.LEWD_SHORES_PHOTO_MODIFIERS)
    assert dialog_lewdshores._cmb_modifier.count() == expected


# ── prompts.json loading / negative_prompt overrides ──────────────────────────

def test_negative_prompt_is_nonempty_string(aig):
    assert isinstance(aig.NEGATIVE_PROMPT, str)
    assert aig.NEGATIVE_PROMPT


def test_default_prompt_file_points_at_src_prompts_json(aig):
    path = aig.default_prompt_file()
    assert path.endswith("prompts.json")


@pytest.mark.parametrize("category", [
    "PHOTO_TYPES", "LOVE_LENS_TYPES", "EVENT_TYPES", "LOVE_LENS_OVERLAY_TYPES",
    "LEWD_SHORES_PHOTO_TYPES", "SNAPSHOT_PHOTO_MODIFIERS", "LEWD_SHORES_PHOTO_MODIFIERS",
])
def test_all_entries_have_negative_prompt_key(aig, category):
    entries = getattr(aig, category)
    for key, info in entries.items():
        assert "negative_prompt" in info, f"{category}[{key!r}] missing 'negative_prompt'"


def test_reload_prompts_overrides_in_place(aig, tmp_path):
    original = dict(aig.PHOTO_TYPES["upskirt"])
    custom_path = tmp_path / "custom_prompts.json"
    custom_path.write_text(
        '{"NEGATIVE_PROMPT": "custom neg", '
        '"PHOTO_TYPES": {"upskirt": {"label": "Custom", '
        '"prompt_enhancement": "custom prompt", "negative_prompt": "custom neg override"}}}',
        encoding="utf-8",
    )
    try:
        aig.reload_prompts(str(custom_path))
        assert aig.PHOTO_TYPES["upskirt"]["label"] == "Custom"
        assert aig.PHOTO_TYPES["upskirt"]["negative_prompt"] == "custom neg override"
        assert aig.NEGATIVE_PROMPT == "custom neg"
        # WIDGET_TYPES still references the same (mutated) dict object
        assert aig.WIDGET_TYPES["photos"] is aig.PHOTO_TYPES
    finally:
        # Restore defaults so later tests in this module see the original data
        aig.PHOTO_TYPES["upskirt"].clear()
        aig.PHOTO_TYPES["upskirt"].update(original)
        aig.reload_prompts()


def test_reload_prompts_ignores_missing_file(aig):
    before = dict(aig.PHOTO_TYPES["upskirt"])
    aig.reload_prompts("/nonexistent/path/prompts.json")
    assert aig.PHOTO_TYPES["upskirt"] == before


def test_dialog_events_has_no_modifier_combo(qtbot, aig):
    from modules.ai_image_gen import AiImageGenDialog
    dlg = AiImageGenDialog(None, "events", lambda d: None)
    qtbot.addWidget(dlg)
    assert dlg._cmb_modifier is None


# ── _save_to_temp / _VerifySessionDialog ──────────────────────────────────────
# Moved to plugins/perchance_diffusion/tests/test_perchance_diffusion.py — this
# behavior now lives in plugins/perchance_diffusion/__init__.py, and its tests
# travel with the plugin rather than the core app test suite.


# ── Diffusion backend registry ────────────────────────────────────────────────

@pytest.fixture()
def clean_backend(aig):
    """Snapshot/restore DIFFUSION_BACKENDS around the test so it's isolated
    from real plugins (e.g. anima_diffusion) that may have registered
    themselves earlier in the same pytest session."""
    saved = dict(aig.DIFFUSION_BACKENDS)
    aig.DIFFUSION_BACKENDS.clear()
    yield
    aig.DIFFUSION_BACKENDS.clear()
    aig.DIFFUSION_BACKENDS.update(saved)


def test_register_diffusion_backend_stores_entry(aig, clean_backend):  # noqa: ARG001
    worker_factory = lambda *a, **kw: None  # noqa: E731
    aig.register_diffusion_backend(
        "_test_backend", "Test Backend",
        worker_factory=worker_factory,
        is_available=lambda: True,
        supports_ip_adapter=True,
        get_device_info=lambda: "cpu",
    )
    entry = aig.DIFFUSION_BACKENDS["_test_backend"]
    assert entry["label"] == "Test Backend"
    assert entry["worker_factory"] is worker_factory
    assert entry["supports_ip_adapter"] is True
    assert entry["get_device_info"]() == "cpu"
    assert entry["verify_dialog_cls"] is None
    assert entry["ref_gen_dialog_cls"] is None


def test_register_diffusion_backend_defaults(aig, clean_backend):  # noqa: ARG001
    aig.register_diffusion_backend("_test_backend", "Test Backend", worker_factory=lambda: None)
    entry = aig.DIFFUSION_BACKENDS["_test_backend"]
    assert entry["is_available"]() is True
    assert entry["supports_ip_adapter"] is False
    assert entry["get_device_info"]() == ""


def test_available_backends_filters_by_is_available(aig, clean_backend):  # noqa: ARG001
    aig.register_diffusion_backend(
        "_test_backend", "Test Backend",
        worker_factory=lambda: None, is_available=lambda: False,
    )
    assert "_test_backend" not in aig.available_backends()
    aig.DIFFUSION_BACKENDS["_test_backend"]["is_available"] = lambda: True
    assert "_test_backend" in aig.available_backends()


def test_has_any_backend_true_when_one_available(aig, clean_backend):  # noqa: ARG001
    aig.register_diffusion_backend(
        "_test_backend", "Test Backend",
        worker_factory=lambda: None, is_available=lambda: True,
    )
    assert aig.has_any_backend() is True


def test_has_any_backend_false_when_none_available(aig):
    saved = dict(aig.DIFFUSION_BACKENDS)
    aig.DIFFUSION_BACKENDS.clear()
    try:
        assert aig.has_any_backend() is False
    finally:
        aig.DIFFUSION_BACKENDS.clear()
        aig.DIFFUSION_BACKENDS.update(saved)


def test_get_torch_info_returns_first_nonempty(aig, clean_backend):  # noqa: ARG001
    aig.register_diffusion_backend(
        "_test_backend", "Test Backend",
        worker_factory=lambda: None, is_available=lambda: True,
        get_device_info=lambda: "torch 2.0 | CPU",
    )
    assert aig.get_torch_info() == "torch 2.0 | CPU"


def test_get_torch_info_empty_when_no_backend_reports_info(aig):
    saved = dict(aig.DIFFUSION_BACKENDS)
    aig.DIFFUSION_BACKENDS.clear()
    try:
        assert aig.get_torch_info() == ""
    finally:
        aig.DIFFUSION_BACKENDS.clear()
        aig.DIFFUSION_BACKENDS.update(saved)


# ── LoRA add-on registry ───────────────────────────────────────────────────────

@pytest.fixture()
def clean_lora_addons(aig):
    """Ensure the "_test_backend" LoRA add-on list is absent before and after each test."""
    aig.LORA_ADDONS.pop("_test_backend", None)
    yield
    aig.LORA_ADDONS.pop("_test_backend", None)


def test_get_lora_addons_empty_when_none_registered(aig, clean_lora_addons):  # noqa: ARG001
    assert aig.get_lora_addons("_test_backend") == []


def test_register_lora_addon_appends_entry(aig, clean_lora_addons):  # noqa: ARG001
    aig.register_lora_addon("_test_backend", "/path/to/lora.safetensors", "My LoRA")
    assert aig.get_lora_addons("_test_backend") == [
        {"path": "/path/to/lora.safetensors", "label": "My LoRA"}
    ]


def test_register_lora_addon_supports_multiple_entries(aig, clean_lora_addons):  # noqa: ARG001
    aig.register_lora_addon("_test_backend", "/a.safetensors", "A")
    aig.register_lora_addon("_test_backend", "/b.safetensors", "B")
    addons = aig.get_lora_addons("_test_backend")
    assert [a["label"] for a in addons] == ["A", "B"]


def test_get_lora_addons_returns_a_copy(aig, clean_lora_addons):  # noqa: ARG001
    aig.register_lora_addon("_test_backend", "/a.safetensors", "A")
    addons = aig.get_lora_addons("_test_backend")
    addons.append({"path": "/b.safetensors", "label": "B"})
    assert len(aig.get_lora_addons("_test_backend")) == 1


