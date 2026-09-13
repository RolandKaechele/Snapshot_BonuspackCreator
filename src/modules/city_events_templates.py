"""City Events Templates — bundled starter dialog scenes for the City Events tab.

Templates are stored in city_events_templates.json, one file holding a list of
named starter scenes. Each template's "dialog" value is the same flat nd_*/pd_*
JSON structure used by dialog scene files loaded via "Add Scene…".
"""

import json
import os
import sys

_TEMPLATE_FILENAME = "city_events_templates.json"


def default_template_file() -> str:
    """Return the templates JSON path: beside main.py, or beside the exe when frozen."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # src/
    return os.path.join(base, _TEMPLATE_FILENAME)


def load_templates(path: str | None = None) -> list[dict]:
    """Load the list of city event dialog templates; returns [] if missing or invalid."""
    path = path or default_template_file()
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return []
    templates = data.get("templates", [])
    return [t for t in templates if isinstance(t, dict) and "name" in t and "dialog" in t]


def add_template(name: str, dialog: dict, description: str = "", path: str | None = None) -> None:
    """Append a new template to the templates file, creating it if missing."""
    path = path or default_template_file()
    templates = load_templates(path)
    templates.append({"name": name, "description": description, "dialog": dialog})
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"templates": templates}, fh, ensure_ascii=False, indent=2)
