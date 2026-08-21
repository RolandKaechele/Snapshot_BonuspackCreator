"""Tests for event_widget module-level helpers (no Qt required)."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from modules.event_widget import (
    _extract_nodes,
    _node_label,
    _remap_refs,
    _write_nodes,
    validate_events,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _node(tag="", text="", oNPC=-1, oSet=-1, oAct=-1, vars=None):
    return {
        "tag": tag, "text": text, "extraData": "",
        "oNPC": oNPC, "oSet": oSet, "oAct": oAct,
        "expand": True, "rect": [0, 0],
        "vars": vars or [],
    }


def _ev(name, nodes):
    data = {}
    _write_nodes(data, nodes)
    return {"type": "dialog", "name": name, "content": json.dumps(data)}


# ── _extract_nodes / _write_nodes ─────────────────────────────────────────────

def test_extract_empty_dict():
    assert _extract_nodes({}) == []


def test_write_then_extract_roundtrip():
    nodes = [
        _node(tag="Aya", text="Hello"),
        _node(tag="You", text="Hi", vars=[{"key": "endEvent", "val": ""}]),
    ]
    data = {}
    _write_nodes(data, nodes)
    result = _extract_nodes(data)
    assert len(result) == 2
    assert result[0]["tag"] == "Aya"
    assert result[0]["text"] == "Hello"
    assert result[1]["vars"][0]["key"] == "endEvent"


def test_write_sets_node_count():
    nodes = [_node(tag="Aya"), _node(tag="You"), _node(tag="Aya")]
    data = {}
    _write_nodes(data, nodes)
    # _write_nodes serialises all nodes; verify all three are present by key
    assert "nd_ID_0" in data
    assert "nd_ID_1" in data
    assert "nd_ID_2" in data
    assert "nd_ID_3" not in data


def test_write_clears_stale_nd_keys():
    nodes = [_node(tag="x")]
    data = {}
    _write_nodes(data, nodes)
    assert "nd_ID_0" in data
    _write_nodes(data, [])
    assert "nd_ID_0" not in data


def test_write_vars_round_trip():
    vars_ = [{"key": "showImage", "val": "bg01"}, {"key": "endEvent", "val": ""}]
    nodes = [_node(vars=vars_)]
    data = {}
    _write_nodes(data, nodes)
    assert data["nd_vars0"] == 2
    assert data["nd_varKey_0_0"] == "showImage"
    assert data["nd_var_0_0"] == "bg01"


# ── _remap_refs ───────────────────────────────────────────────────────────────

def test_remap_swaps_indices():
    nodes = [_node(oNPC=1), _node(oNPC=0)]
    _remap_refs(nodes, {0: 1, 1: 0})
    assert nodes[0]["oNPC"] == 0
    assert nodes[1]["oNPC"] == 1


def test_remap_removal_sets_minus_one():
    nodes = [_node(oNPC=2, oSet=2)]
    _remap_refs(nodes, {2: -1})
    assert nodes[0]["oNPC"] == -1
    assert nodes[0]["oSet"] == -1


def test_remap_unmapped_ref_unchanged():
    nodes = [_node(oNPC=5)]
    _remap_refs(nodes, {0: 1})
    assert nodes[0]["oNPC"] == 5


def test_remap_all_three_fields():
    nodes = [_node(oNPC=0, oSet=1, oAct=2)]
    _remap_refs(nodes, {0: 10, 1: 11, 2: 12})
    assert nodes[0]["oNPC"] == 10
    assert nodes[0]["oSet"] == 11
    assert nodes[0]["oAct"] == 12


# ── _node_label ───────────────────────────────────────────────────────────────

def test_node_label_bare():
    assert _node_label(0, {}) == "#0"


def test_node_label_with_tag():
    assert _node_label(2, {"tag": "Aya", "text": ""}) == "#2 [Aya]"


def test_node_label_with_text():
    assert _node_label(1, {"tag": "", "text": "Hello"}) == "#1  Hello"


def test_node_label_tag_and_text():
    label = _node_label(3, {"tag": "Aya", "text": "Hello world"})
    assert label == "#3 [Aya]  Hello world"


def test_node_label_long_text_truncated():
    label = _node_label(0, {"tag": "", "text": "A" * 60})
    assert "…" in label
    assert len(label) < 65


# ── validate_events ───────────────────────────────────────────────────────────

def test_validate_empty_list():
    assert validate_events([]) == []


def test_validate_skips_background_events():
    assert validate_events([{"type": "background", "name": "bg"}]) == []


def test_validate_skips_empty_content():
    assert validate_events([{"type": "dialog", "name": "d", "content": ""}]) == []


def test_validate_invalid_json_is_error():
    ev = {"type": "dialog", "name": "d", "content": "{bad}"}
    issues = validate_events([ev])
    assert len(issues) == 1
    assert issues[0][0] == "error"
    assert "JSON" in issues[0][3]


def test_validate_clean_scene_no_issues():
    issues = validate_events([_ev("s", [_node(vars=[{"key": "endEvent", "val": ""}])])])
    assert issues == []


def test_validate_missing_end_event_is_warning():
    issues = validate_events([_ev("s", [_node()])])
    assert any(i[0] == "warning" and "endEvent" in i[3] for i in issues)


def test_validate_out_of_range_onpc_is_error():
    nodes = [_node(oNPC=99, vars=[{"key": "endEvent", "val": ""}])]
    issues = validate_events([_ev("s", nodes)])
    assert any(i[0] == "error" and "oNPC=99" in i[3] for i in issues)


def test_validate_out_of_range_oset_is_error():
    nodes = [_node(oSet=5, vars=[{"key": "endEvent", "val": ""}])]
    issues = validate_events([_ev("s", nodes)])
    assert any(i[0] == "error" and "oSet=5" in i[3] for i in issues)


def test_validate_in_range_ref_ok():
    nodes = [
        _node(oNPC=1),
        _node(vars=[{"key": "endEvent", "val": ""}]),
    ]
    issues = validate_events([_ev("s", nodes)])
    assert not any(i[0] == "error" for i in issues)


def test_validate_minus_one_ref_ok():
    nodes = [_node(oNPC=-1, oSet=-1, oAct=-1, vars=[{"key": "endEvent", "val": ""}])]
    assert validate_events([_ev("s", nodes)]) == []


def test_validate_multiple_scenes():
    good = _ev("good", [_node(vars=[{"key": "endEvent", "val": ""}])])
    bad = _ev("bad", [_node()])
    issues = validate_events([good, bad])
    assert all(i[1] == "bad" for i in issues)


def test_validate_node_index_reported_correctly():
    nodes = [_node(), _node(oNPC=99, vars=[{"key": "endEvent", "val": ""}])]
    issues = validate_events([_ev("s", nodes)])
    ref_issue = next(i for i in issues if "oNPC" in i[3])
    assert ref_issue[2] == 1  # node index
