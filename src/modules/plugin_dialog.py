"""Plugin Manager dialog — view loaded/disabled plugins and toggle them on/off."""

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import ( #type: ignore
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QCheckBox,
)
from PyQt6.QtCore import Qt #type: ignore

from modules.plugin_system import load_disabled_plugins, save_disabled_plugins

if TYPE_CHECKING:
    from modules.plugin_system import PluginSystem


class PluginManagerDialog(QDialog):
    """Lists discovered plugins with an enable/disable checkbox per plugin.

    Changes are persisted to plugin_config.json and take effect on next
    application restart (plugins are only loaded once, at startup).
    """

    def __init__(self, parent, plugin_system: "PluginSystem") -> None:
        super().__init__(parent)
        self.setWindowTitle("Manage Plugins")
        self.resize(480, 360)
        self._plugin_system = plugin_system
        self._disabled = load_disabled_plugins()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Discovered plugins. Unchecking a plugin disables it; "
            "restart the app for changes to take effect."
        ))

        self._list = QListWidget()
        names = self._plugin_system.discovered_plugin_names()
        loaded = set(self._plugin_system.loaded_plugin_names())
        for name in sorted(names):
            item = QListWidgetItem()
            self._list.addItem(item)
            checkbox = QCheckBox(name)
            checkbox.setChecked(name not in self._disabled)
            meta = self._plugin_system.plugin_info(name)
            tip = meta.get("description", "")
            if name not in loaded and name not in self._disabled:
                tip = (tip + "\n" if tip else "") + "(failed to load — see debug log)"
            if tip:
                checkbox.setToolTip(tip)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self._list.setItemWidget(item, checkbox)
        layout.addWidget(self._list, 1)

        buttons = QHBoxLayout()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self._on_close)
        buttons.addStretch()
        buttons.addWidget(btn_close)
        layout.addLayout(buttons)

    def _on_close(self) -> None:
        disabled: set[str] = set()
        for row in range(self._list.count()):
            item = self._list.item(row)
            name = item.data(Qt.ItemDataRole.UserRole)
            checkbox = self._list.itemWidget(item)
            if isinstance(checkbox, QCheckBox) and not checkbox.isChecked():
                disabled.add(name)
        save_disabled_plugins(disabled)
        self.accept()
