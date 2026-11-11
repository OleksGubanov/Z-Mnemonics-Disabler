# SPDX-License-Identifier: GPL-3.0-only

"""Add one simple on/off switch to Krita's Tools menu."""

from weakref import ref

from krita import Extension
from PyQt5 import sip
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMessageBox

from .guard import GlobalMnemonicGuard
from .policy import load_enabled, save_enabled, strip_mnemonics


class ZMnemonicsExtension(Extension):
    def __init__(self, parent):
        super().__init__(parent)
        self.enabled = load_enabled()
        self.guard = None
        self._hosts = {}  # Window ID -> (weak window, toggle action)
        self._closing = False
        self._quit_connected = False

    def setup(self):
        QTimer.singleShot(0, self._initialize)

    def _initialize(self):
        if self._closing:
            return
        try:
            if self.guard is None:
                self.guard = GlobalMnemonicGuard({"enabled": self.enabled})
            app = QApplication.instance()
            if app is not None and not self._quit_connected:
                app.aboutToQuit.connect(self.shutdown)
                self._quit_connected = True
            self.guard.set_enabled(self.enabled)
        except (RuntimeError, ReferenceError, AttributeError) as exc:
            print("[Z Mnemonics Disabler] Startup:", repr(exc))

    def createActions(self, window):
        """Krita calls this when it creates an application window."""
        try:
            main = window.qwindow()
            if main is None or sip.isdeleted(main):
                return
            token = id(main)
            handle = ref(main)
            main.destroyed.connect(lambda _obj=None, t=token: self._hosts.pop(t, None))
            self._mount_if_alive(handle)
            # Some Krita menus are added shortly after the window appears.
            for delay in (200, 900):
                QTimer.singleShot(delay, lambda h=handle: self._mount_if_alive(h))
        except (RuntimeError, ReferenceError, AttributeError) as exc:
            print("[Z Mnemonics Disabler] Window:", repr(exc))
        if self.guard is None:
            QTimer.singleShot(0, self._initialize)

    def _mount_if_alive(self, handle):
        if self._closing:
            return
        main = handle()
        try:
            if main is not None and not sip.isdeleted(main):
                self._mount_toggle(main, handle)
        except (RuntimeError, ReferenceError):
            pass

    @staticmethod
    def _find_tools(main):
        try:
            bar = main.menuBar()
            if bar is None:
                return None
            for action in bar.actions():
                menu = action.menu()
                if menu is None:
                    continue
                title = strip_mnemonics(action.text()).strip().casefold()
                identifiers = (action.objectName(), menu.objectName())
                identifiers = [
                    name.casefold().replace("_", "").replace("-", "")
                    for name in identifiers if name
                ]
                if title in ("tools", "инструменты", "інструменти"):
                    return menu
                if any(name in ("tools", "menutools", "toolsmenu") for name in identifiers):
                    return menu
        except (RuntimeError, ReferenceError, AttributeError):
            pass
        return None

    def _mount_toggle(self, main, handle):
        tools = self._find_tools(main)
        if tools is None:
            return
        action = next(
            (a for a in tools.actions() if a.objectName() == "zmd_toggle"), None
        )
        if action is None:
            action = tools.addAction("Z Mnemonics Disabler")
            action.setObjectName("zmd_toggle")
            action.setCheckable(True)
            action.setToolTip("Disable Qt Alt menu navigation shortcuts")
            action.triggered.connect(self.set_enabled)
        action.setChecked(self.enabled)
        self._hosts[id(main)] = (handle, action)

    def _sync_checks(self):
        for token, (handle, action) in tuple(self._hosts.items()):
            try:
                window = handle()
                if window is None or sip.isdeleted(window) or sip.isdeleted(action):
                    self._hosts.pop(token, None)
                    continue
                if action.isChecked() != self.enabled:
                    action.setChecked(self.enabled)
            except (RuntimeError, ReferenceError, AttributeError):
                self._hosts.pop(token, None)

    @staticmethod
    def _warn(message):
        try:
            QMessageBox.warning(None, "Z Mnemonics Disabler", message)
        except (RuntimeError, ReferenceError):
            print("[Z Mnemonics Disabler]", message)

    def set_enabled(self, checked=False):
        desired = bool(checked)
        if desired == self.enabled:
            self._sync_checks()
            return

        if self.guard is None:
            self._initialize()
        if self.guard is None:
            self._sync_checks()
            self._warn("The plugin could not be initialized.")
            return

        if not save_enabled(desired):
            self._sync_checks()
            self._warn("Could not save the setting to Krita's config folder.")
            return

        try:
            self.guard.set_enabled(desired)
        except (RuntimeError, ReferenceError, AttributeError) as exc:
            # Also undo a partly applied Qt change, not just the saved option.
            try:
                self.guard.set_enabled(self.enabled)
            except (RuntimeError, ReferenceError, AttributeError):
                pass
            save_enabled(self.enabled)
            self._sync_checks()
            self._warn("Could not change mnemonic suppression: " + str(exc))
            return

        self.enabled = desired
        self._sync_checks()

    def shutdown(self):
        self._closing = True
        if self.guard is not None:
            try:
                self.guard.shutdown()
            except (RuntimeError, ReferenceError):
                pass
        self._hosts.clear()
