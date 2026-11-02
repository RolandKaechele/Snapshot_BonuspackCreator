"""Plugin Manager dialog — view loaded/disabled plugins and toggle them on/off."""

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import ( #type: ignore
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QCheckBox, QHeaderView, QAbstractItemView, QWidget,
)
from PyQt6.QtCore import Qt #type: ignore

from modules.plugin_system import load_disabled_plugins, save_disabled_plugins

if TYPE_CHECKING:
    from modules.plugin_system import PluginSystem

_COL_ENABLED, _COL_NAME, _COL_VERSION, _COL_STATUS, _COL_DESCRIPTION = range(5)


class PluginManagerDialog(QDialog):
    """Table of discovered plugins — name, version, load status, description,
    and an enable/disable checkbox per plugin.

    Changes are persisted to plugin_config.json and take effect on next
    application restart (plugins are only loaded once, at startup).
    """

    def __init__(self, parent, plugin_system: "PluginSystem") -> None:
        super().__init__(parent)
        self.setWindowTitle("Manage Plugins")
        self.resize(720, 360)
        self._plugin_system = plugin_system
        self._disabled = load_disabled_plugins()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Discovered plugins. Unchecking a plugin disables it; "
            "restart the app for changes to take effect.\n"
            "Plugins whose hardware requirements (e.g. VRAM) aren't met on this "
            "machine are greyed out and can't be enabled — hover the row for details."
        ))

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Enabled", "Name", "Version", "Status", "Description"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(_COL_ENABLED, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_VERSION, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_STATUS, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_DESCRIPTION, QHeaderView.ResizeMode.Stretch)

        loaded = set(self._plugin_system.loaded_plugin_names())
        names = sorted(self._plugin_system.discovered_plugin_names())
        self._table.setRowCount(len(names))
        for row, name in enumerate(names):
            is_disabled = name in self._disabled
            is_loaded = name in loaded
            unsupported = self._plugin_system.hardware_status(name)

            checkbox = QCheckBox()
            checkbox.setChecked(not is_disabled and not unsupported)
            checkbox.setEnabled(not unsupported)
            if unsupported:
                checkbox.setToolTip(unsupported)
            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.addWidget(checkbox)
            cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            self._table.setCellWidget(row, _COL_ENABLED, cell)

            self._table.setItem(row, _COL_NAME, QTableWidgetItem(name))

            meta = self._plugin_system.plugin_info(name)
            version_item = QTableWidgetItem(meta.get("version", "") or "\u2014")
            version_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, _COL_VERSION, version_item)

            if unsupported:
                status = "Unsupported Hardware"
            elif is_disabled:
                status = "Disabled"
            elif is_loaded:
                status = "Enabled"
            else:
                status = "Failed to load"
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if unsupported:
                status_item.setToolTip(unsupported)
            self._table.setItem(row, _COL_STATUS, status_item)

            description = meta.get("description", "")
            if not is_loaded and not is_disabled and not unsupported:
                description = (description + " " if description else "") + "(see debug log)"
            description_item = QTableWidgetItem(description)
            if unsupported:
                description_item.setToolTip(unsupported)
            self._table.setItem(row, _COL_DESCRIPTION, description_item)

        layout.addWidget(self._table, 1)

        buttons = QHBoxLayout()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self._on_close)
        buttons.addStretch()
        buttons.addWidget(btn_close)
        layout.addLayout(buttons)

    def _on_close(self) -> None:
        disabled: set[str] = set()
        for row in range(self._table.rowCount()):
            name = self._table.item(row, _COL_NAME).text()
            cell = self._table.cellWidget(row, _COL_ENABLED)
            checkbox = cell.findChild(QCheckBox) if cell else None
            if checkbox is not None and not checkbox.isChecked():
                disabled.add(name)
        save_disabled_plugins(disabled)
        self.accept()

