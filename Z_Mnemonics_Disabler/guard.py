# SPDX-License-Identifier: GPL-3.0-only

"""Disable Alt menu mnemonics in Krita's Qt interface.

The filter watches new menus and controls, so a restart is not needed after
opening a dialog. Only displayed labels are changed; key presses are not read.
"""

from weakref import ref

from PyQt5 import sip
from PyQt5.QtCore import QObject, QEvent, QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication, QAbstractButton, QDialog, QDockWidget, QGroupBox,
    QLabel, QMenu, QMenuBar, QTabBar, QToolBar, QToolBox, QWidget,
)

from .policy import looks_like_rich_text, strip_mnemonics, validated


def alive(obj):
    """Qt may delete a widget while Python still holds its wrapper."""
    try:
        return obj is not None and not sip.isdeleted(obj)
    except (RuntimeError, ReferenceError, TypeError):
        return False


class GlobalMnemonicGuard(QObject):
    def __init__(self, options, app=None):
        app = app or QApplication.instance()
        if app is None:
            raise RuntimeError("QApplication is not available")
        super().__init__(app)

        self.app = app
        self.options = validated(options)
        self.enabled = False
        self._installed = False
        self._busy = False
        self._records = {}       # object ID -> {(kind, index): (old, clean)}
        self._tracked = {}       # object ID -> QObject
        self._menu_roles = {}    # object ID -> menu role
        self._pending_widgets = set()
        self._scanned_windows = set()
        self._indexed_counts = {}  # Last known number of tabs/pages.
        self._item_ids = {}        # Stable QToolBox page widget IDs.
        self.last_error = ""

    @property
    def tracked_labels(self):
        return sum(len(properties) for properties in self._records.values())

    def _scope(self, name):
        return self.options.get(name, False)

    def _track(self, obj):
        if not alive(obj):
            return
        token = id(obj)
        if token in self._tracked:
            return
        self._tracked[token] = obj
        try:
            obj.destroyed.connect(lambda _obj=None, t=token: self._forget(t))
            if isinstance(obj, QTabBar):
                obj.tabMoved.connect(
                    lambda old, new, t=token: self._tab_moved(t, old, new)
                )
        except (ReferenceError, RuntimeError):
            self._forget(token)

    def _forget(self, token):
        self._tracked.pop(token, None)
        self._records.pop(token, None)
        self._menu_roles.pop(token, None)
        self._pending_widgets.discard(token)
        self._scanned_windows.discard(token)
        for key in [k for k in self._indexed_counts if k[0] == token]:
            self._indexed_counts.pop(key, None)
        for key in [k for k in self._item_ids if k[0] == token]:
            self._item_ids.pop(key, None)

    def _tab_moved(self, token, old, new):
        """A QTabBar reports moves, so keep its saved labels in the same order."""
        obj = self._tracked.get(token)
        if not alive(obj) or not isinstance(obj, QTabBar):
            return
        count = obj.count()
        if not (0 <= old < count and 0 <= new < count):
            return
        properties = self._records.get(token)
        if not properties:
            return
        labels = [properties.pop(("tab", index), None) for index in range(count)]
        labels.insert(new, labels.pop(old))
        for index, label in enumerate(labels):
            if label is not None:
                properties[("tab", index)] = label
        self._indexed_counts[(token, "tab")] = count

    @staticmethod
    def _page_id(obj, kind, index):
        """QToolBox pages are real widgets, so their identity survives moves."""
        if kind != "toolbox":
            return None
        try:
            page = obj.widget(index)
            return id(page) if alive(page) else None
        except (RuntimeError, ReferenceError, AttributeError, IndexError):
            return None

    def _reconcile_indexed(self, obj, kind):
        """Match saved originals to today's tabs, not yesterday's indices.

        In particular, removing tab 0 must not restore its label onto tab 1.
        QToolBox has stable page widgets; QTabBar is matched by its label.
        When two changed tabs have identical text but different originals,
        there is no reliable identity: avoid guessing the original mnemonic.
        """
        token = id(obj)
        properties = self._records.get(token)
        if not properties:
            return
        old = {
            index: label for (entry_kind, index), label in properties.items()
            if entry_kind == kind
        }
        if not old:
            return
        count = obj.count()
        last_count = self._indexed_counts.get((token, kind))
        current = [self._read(obj, kind, i) for i in range(count)]
        identities = [self._page_id(obj, kind, i) for i in range(count)]
        stable = last_count == count and all(
            index < count
            and current[index] in (original, clean)
            and (kind != "toolbox" or self._item_ids.get((token, kind, index)) == identities[index])
            for index, (original, clean) in old.items()
        )
        if stable:
            return

        remapped = {}
        unused = set(old)

        def assign(index, source):
            remapped[index] = old[source]
            unused.remove(source)

        # Prefer a QToolBox page's widget identity, even when it was renamed.
        if kind == "toolbox":
            for index, identity in enumerate(identities):
                if identity is None:
                    continue
                matches = [
                    source for source in unused
                    if self._item_ids.get((token, kind, source)) == identity
                ]
                if len(matches) == 1:
                    assign(index, matches[0])

        # Text matching covers removed/inserted/moved QTabBar tabs.
        for index, text in enumerate(current):
            if index in remapped:
                continue
            matches = [
                source for source in unused
                if text in old[source] or strip_mnemonics(text) == old[source][1]
            ]
            if not matches:
                continue
            if len(matches) == 1:
                assign(index, matches[0])
            elif index in matches and last_count == count:
                assign(index, index)
            elif len({old[source][0] for source in matches}) == 1:
                # All candidates restore to precisely the same label.
                assign(index, min(matches))
            # Otherwise the source is ambiguous; don't restore a wrong label.

        for index in old:
            properties.pop((kind, index), None)
            self._item_ids.pop((token, kind, index), None)
        for index, value in remapped.items():
            properties[(kind, index)] = value
            identity = identities[index]
            if identity is not None:
                self._item_ids[(token, kind, index)] = identity
        if not properties:
            self._records.pop(token, None)

    def _scan_indexed(self, obj, kind):
        self._reconcile_indexed(obj, kind)
        for index in range(obj.count()):
            self._sanitize(obj, kind, index)
        # No need to remember controls we never modified.
        key = (id(obj), kind)
        if id(obj) in self._tracked:
            self._indexed_counts[key] = obj.count()
        else:
            self._indexed_counts.pop(key, None)

    @staticmethod
    def _read(obj, kind, index):
        if kind == "action":
            return str(obj.text())
        if kind == "menu":
            return str(obj.title())
        if kind == "tab":
            return str(obj.tabText(index))
        if kind == "toolbox":
            return str(obj.itemText(index))
        if kind == "group":
            return str(obj.title())
        if kind == "dock":
            return str(obj.windowTitle())
        return str(obj.text())  # button or label

    @staticmethod
    def _write(obj, kind, index, value):
        if kind == "action":
            obj.setText(value)
        elif kind == "menu":
            obj.setTitle(value)
        elif kind == "tab":
            obj.setTabText(index, value)
        elif kind == "toolbox":
            obj.setItemText(index, value)
        elif kind == "group":
            obj.setTitle(value)
        elif kind == "dock":
            obj.setWindowTitle(value)
        else:
            obj.setText(value)

    def _prepare(self, obj, kind, index, current):
        """Remember the original text before changing it."""
        key = (kind, index)
        token = id(obj)
        previous = self._records.get(token, {}).get(key)
        if previous and current == previous[1]:
            return None  # Still showing our own sanitized text.

        clean = strip_mnemonics(current)
        if clean == current:
            if previous:
                properties = self._records[token]
                properties.pop(key, None)
                self._item_ids.pop((token, kind, index), None)
                if not properties:
                    self._records.pop(token, None)
            return None

        self._track(obj)
        self._records.setdefault(token, {})[key] = (current, clean)
        identity = self._page_id(obj, kind, index)
        if identity is not None:
            self._item_ids[(token, kind, index)] = identity
        return clean

    def _sanitize(self, obj, kind, index=-1):
        if not alive(obj):
            return
        try:
            if kind == "label":
                # QLabel can render HTML. Altering its text may break entities
                # or links, so rich labels are deliberately left alone.
                if obj.textFormat() == Qt.RichText:
                    return
                if looks_like_rich_text(str(obj.text())):
                    return
            current = self._read(obj, kind, index)
            clean = self._prepare(obj, kind, index, current)
            if clean is not None:
                self._write(obj, kind, index, clean)
        except (RuntimeError, ReferenceError, AttributeError, IndexError) as exc:
            self.last_error = str(exc)[:150]

    def _sanitize_menu_header(self, menu):
        """Keep both originals: changing a QMenu title can change its QAction."""
        if not alive(menu):
            return
        try:
            action = menu.menuAction()
            if not alive(action):
                self._sanitize(menu, "menu")
                return

            title = str(menu.title())
            label = str(action.text())
            # Plan BOTH edits before calling a setter; Qt may link the texts.
            clean_title = self._prepare(menu, "menu", -1, title)
            clean_label = self._prepare(action, "action", -1, label)

            if clean_title is not None:
                menu.setTitle(clean_title)
            if clean_label is not None:
                action.setText(clean_label)
        except (RuntimeError, ReferenceError, AttributeError) as exc:
            self.last_error = str(exc)[:150]

    def _role_allowed(self, role):
        setting = {
            "bar": "main_menu", "top": "main_menu",
            "nested": "nested_menus", "context": "context_menus",
        }[role]
        return self._scope(setting)

    def _infer_role(self, menu):
        known = self._menu_roles.get(id(menu))
        if known:
            return known
        try:
            parent = menu.parentWidget()
            if isinstance(parent, QMenuBar):
                return "top"
            if isinstance(parent, QMenu):
                return "context" if self._infer_role(parent) == "context" else "nested"
        except (RuntimeError, ReferenceError, AttributeError):
            pass
        return "context"

    def _visit_action(self, action, parent_role):
        if not alive(action):
            return
        try:
            submenu = action.menu()
            if alive(submenu):
                role = "top" if parent_role == "bar" else (
                    "context" if parent_role == "context" else "nested"
                )
                self._menu_roles[id(submenu)] = role
                self._track(submenu)
                if self._role_allowed(role):
                    self._sanitize_menu_header(submenu)
            elif self._role_allowed(parent_role):
                self._sanitize(action, "action")
        except (RuntimeError, ReferenceError, AttributeError):
            pass

    def _visit_menu(self, menu, role):
        if not alive(menu):
            return
        self._menu_roles[id(menu)] = role
        self._track(menu)
        if self._role_allowed(role):
            self._sanitize_menu_header(menu)
        try:
            # Submenus will scan their own entries when they open.
            for action in menu.actions():
                self._visit_action(action, role)
        except (RuntimeError, ReferenceError):
            pass

    def _visit_bar(self, bar):
        if not alive(bar):
            return
        try:
            for action in bar.actions():
                self._visit_action(action, "bar")
        except (RuntimeError, ReferenceError):
            pass

    def _scan_widget(self, widget):
        if not alive(widget):
            return
        if isinstance(widget, QMenu):
            self._visit_menu(widget, self._infer_role(widget))
        elif isinstance(widget, QMenuBar):
            self._visit_bar(widget)
        elif isinstance(widget, QTabBar) and self._scope("dialog_tabs"):
            self._scan_indexed(widget, "tab")
        elif isinstance(widget, QToolBox) and self._scope("toolbox_pages"):
            self._scan_indexed(widget, "toolbox")
        elif isinstance(widget, QAbstractButton) and self._scope("dialog_buttons"):
            self._sanitize(widget, "button")
        elif isinstance(widget, QGroupBox) and self._scope("dialog_groups"):
            self._sanitize(widget, "group")
        elif isinstance(widget, QLabel) and self._scope("dialog_labels"):
            self._sanitize(widget, "label")
        elif isinstance(widget, QDockWidget) and self._scope("dock_titles"):
            self._sanitize(widget, "dock")
        elif isinstance(widget, QToolBar) and self._scope("nested_menus"):
            for action in widget.actions():
                self._sanitize(action, "action")

    def _allowed_window(self, root):
        return self._scope("all_windows") or isinstance(root, QDialog)

    def _scan_window(self, root):
        if not alive(root):
            return
        self._track(root)
        self._scanned_windows.add(id(root))
        try:
            if not self._allowed_window(root):
                for bar in root.findChildren(QMenuBar):
                    self._visit_bar(bar)
                return

            self._scan_widget(root)
            for widget in root.findChildren(QWidget):
                if not isinstance(widget, QMenu):
                    self._scan_widget(widget)
        except (RuntimeError, ReferenceError, AttributeError) as exc:
            self.last_error = str(exc)[:150]

    def scan_existing_windows(self):
        if not self.enabled:
            return

        def scan():
            windows = [w for w in self.app.topLevelWidgets() if alive(w)]
            # Classify menubars first, then handle floating popup menus.
            for window in windows:
                if not isinstance(window, QMenu) and window.isVisible():
                    self._scan_window(window)
            for window in windows:
                if isinstance(window, QMenu) and window.isVisible():
                    self._scan_widget(window)

        self._safe_run(scan)

    def _queue_widget(self, widget):
        """Process a new/changed control outside its construction or paint event."""
        token = id(widget)
        if token in self._pending_widgets:
            return
        self._pending_widgets.add(token)
        try:
            handle = ref(widget)
        except TypeError:
            self._pending_widgets.discard(token)
            return

        def process():
            self._pending_widgets.discard(token)
            obj = handle()
            if not self.enabled or not alive(obj) or not isinstance(obj, QWidget):
                return
            try:
                if self._allowed_window(obj.window()):
                    self._safe_run(lambda: self._scan_widget(obj))
            except (RuntimeError, ReferenceError, AttributeError):
                pass

        QTimer.singleShot(0, process)

    def _needs_update(self, widget):
        """Check whether a control needs fixing before Qt draws it."""
        if isinstance(widget, QLabel):
            if widget.textFormat() == Qt.RichText or looks_like_rich_text(widget.text()):
                return False
            kind, indices = "label", (-1,)
        elif isinstance(widget, QAbstractButton):
            kind, indices = "button", (-1,)
        elif isinstance(widget, QGroupBox):
            kind, indices = "group", (-1,)
        elif isinstance(widget, QDockWidget):
            kind, indices = "dock", (-1,)
        elif isinstance(widget, QTabBar):
            kind, indices = "tab", range(widget.count())
        elif isinstance(widget, QToolBox):
            kind, indices = "toolbox", range(widget.count())
        else:
            return False

        records = self._records.get(id(widget), {})
        if kind in ("tab", "toolbox") and records:
            if self._indexed_counts.get((id(widget), kind)) != widget.count():
                return True
            if kind == "toolbox" and any(
                self._item_ids.get((id(widget), kind, index))
                != self._page_id(widget, kind, index)
                for index in indices if (kind, index) in records
            ):
                return True
        for index in indices:
            text = self._read(widget, kind, index)
            previous = records.get((kind, index))
            if previous and text != previous[1]:
                return True
            if strip_mnemonics(text) != text:
                return True
        return False

    def _safe_run(self, callback):
        if self._busy:
            return
        self._busy = True
        try:
            callback()
        except (RuntimeError, ReferenceError, AttributeError) as exc:
            self.last_error = str(exc)[:150]
        finally:
            self._busy = False

    def eventFilter(self, obj, event):
        if not self.enabled or self._busy:
            return False
        try:
            event_type = event.type()
            if event_type in (QEvent.ActionAdded, QEvent.ActionChanged):
                if self._scope("dynamic_actions") and isinstance(obj, (QMenu, QMenuBar)):
                    role = "bar" if isinstance(obj, QMenuBar) else self._infer_role(obj)
                    self._safe_run(lambda: self._visit_action(event.action(), role))
            elif event_type == QEvent.Show and isinstance(obj, QWidget):
                if isinstance(obj, QMenu):
                    self._safe_run(lambda: self._visit_menu(obj, self._infer_role(obj)))
                elif obj.isWindow():
                    if id(obj) not in self._scanned_windows:
                        self._safe_run(lambda: self._scan_window(obj))
                    else:
                        self._safe_run(lambda: self._scan_widget(obj))
                elif self._allowed_window(obj.window()):
                    self._safe_run(lambda: self._scan_widget(obj))
            elif event_type == QEvent.ChildAdded:
                if self._scope("dynamic_widgets") and isinstance(obj, QWidget):
                    self._queue_widget(event.child())
            elif event_type == QEvent.LanguageChange and isinstance(obj, QWidget):
                if obj.isWindow():
                    self._safe_run(lambda: self._scan_window(obj))
                elif self._allowed_window(obj.window()):
                    self._safe_run(lambda: self._scan_widget(obj))
            elif event_type in (QEvent.Polish, QEvent.PolishRequest):
                if isinstance(obj, QWidget) and self._allowed_window(obj.window()):
                    self._safe_run(lambda: self._scan_widget(obj))
            elif event_type == QEvent.Paint and self._scope("late_updates"):
                # A timer would run AFTER this paint, briefly exposing the
                # underlined mnemonic. Fix changed text before Qt draws it.
                if isinstance(obj, QWidget) and self._allowed_window(obj.window()):
                    if self._needs_update(obj):
                        self._safe_run(lambda: self._scan_widget(obj))
        except (RuntimeError, ReferenceError, AttributeError, TypeError, ValueError) as exc:
            self.last_error = str(exc)[:150]
        return False

    def set_enabled(self, value):
        value = bool(value)
        if value == self.enabled:
            return
        if value:
            self.enabled = True
            if not self._installed:
                self.app.installEventFilter(self)
                self._installed = True
            self.scan_existing_windows()
        else:
            self.enabled = False
            if self._installed:
                self.app.removeEventFilter(self)
                self._installed = False
            self.restore()

    def restore(self):
        if self._busy:
            return
        self._busy = True
        try:
            # Tabs and pages may have moved or been deleted since the last paint.
            for (token, kind) in tuple(self._indexed_counts):
                obj = self._tracked.get(token)
                if alive(obj):
                    try:
                        self._reconcile_indexed(obj, kind)
                    except (RuntimeError, ReferenceError, AttributeError, IndexError):
                        pass

            # Check all current texts first: a menu title setter can also
            # change its QAction, but we still need the original QAction text.
            changes = []
            for token, properties in tuple(self._records.items()):
                obj = self._tracked.get(token)
                if not alive(obj):
                    continue
                for (kind, index), (original, clean) in properties.items():
                    try:
                        if self._read(obj, kind, index) == clean:
                            changes.append((obj, kind, index, original))
                    except (RuntimeError, ReferenceError, AttributeError, IndexError):
                        pass

            # Actions go last because changing a menu title can rewrite them.
            changes.sort(key=lambda entry: entry[1] == "action")
            for obj, kind, index, original in changes:
                try:
                    if alive(obj):
                        self._write(obj, kind, index, original)
                except (RuntimeError, ReferenceError, AttributeError, IndexError):
                    pass
            self._records.clear()
            self._tracked.clear()
            self._menu_roles.clear()
            self._scanned_windows.clear()
            self._pending_widgets.clear()
            self._indexed_counts.clear()
            self._item_ids.clear()
        finally:
            self._busy = False

    def shutdown(self):
        # Krita is closing: do not touch widgets during Qt teardown.
        self.enabled = False
        if self._installed:
            try:
                self.app.removeEventFilter(self)
            except (ReferenceError, RuntimeError):
                pass
        self._installed = False
        self._records.clear()
        self._tracked.clear()
        self._menu_roles.clear()
        self._pending_widgets.clear()
        self._scanned_windows.clear()
        self._indexed_counts.clear()
        self._item_ids.clear()
