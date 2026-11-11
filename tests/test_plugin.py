"""Basic tests without a Krita installation or a graphical desktop."""
import importlib
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


class Signal:
    def __init__(self):
        self.handlers = []

    def connect(self, fn):
        self.handlers.append(fn)

    def emit(self, *args):
        for fn in list(self.handlers):
            fn(*args)


class QObject:
    def __init__(self, parent=None):
        self.parent = parent
        self.destroyed = Signal()
        self._object_name = ""

    def objectName(self):
        return self._object_name

    def setObjectName(self, value):
        self._object_name = value


class QWidget(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._children = []
        self._visible = True
        self._is_window = parent is None
        if isinstance(parent, QWidget):
            parent._children.append(self)

    def isVisible(self):
        return self._visible

    def isWindow(self):
        return self._is_window

    def window(self):
        obj = self
        while isinstance(obj.parent, QWidget):
            obj = obj.parent
        return obj

    def findChildren(self, kind):
        found = []
        for child in self._children:
            if isinstance(child, kind):
                found.append(child)
            found.extend(child.findChildren(kind))
        return found

    def parentWidget(self):
        return self.parent


class QAction(QObject):
    def __init__(self, value, menu=None):
        super().__init__()
        self.value = value
        self._menu = menu
        self._checked = False
        self._checkable = False
        self._tooltip = ""
        self.triggered = Signal()

    def setCheckable(self, enabled):
        self._checkable = enabled

    def setToolTip(self, text):
        self._tooltip = text

    def setChecked(self, value):
        self._checked = value

    def isChecked(self):
        return self._checked

    def trigger(self):
        if self._checkable:
            self._checked = not self._checked
        self.triggered.emit(self._checked)

    def text(self):
        return self.value

    def setText(self, value):
        self.value = value

    def menu(self):
        return self._menu


class QMenu(QWidget):
    def __init__(self, title, parent=None, linked=True):
        super().__init__(parent)
        self._title = title
        self._menu_action = QAction(title, self)
        self._items = []
        self.linked = linked

    def title(self):
        return self._title

    def setTitle(self, title):
        self._title = title
        if self.linked:
            self._menu_action.setText(title)

    def menuAction(self):
        return self._menu_action

    def actions(self):
        return self._items

    def add(self, action):
        self._items.append(action)

    def addAction(self, text):
        action = QAction(text)
        self._items.append(action)
        return action


class QMenuBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []

    def actions(self):
        return self._items

    def add(self, action):
        self._items.append(action)


class QMainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._bar = QMenuBar(self)
        tools = QMenu("&Tools", self._bar)
        tools.setObjectName("menu_tools")
        self._bar.add(tools.menuAction())
        self._tools = tools

    def menuBar(self):
        return self._bar


class QLabel(QWidget):
    def __init__(self, text, parent=None, format_=0):
        super().__init__(parent)
        self._text = text
        self._format = format_
        self.write_count = 0

    def text(self):
        return self._text

    def setText(self, text):
        self.write_count += 1
        self._text = text

    def textFormat(self):
        return self._format


class QAbstractButton(QLabel):
    pass


class QDialog(QWidget):
    pass


class QDockWidget(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self._title = title
        self.write_count = 0

    def windowTitle(self):
        return self._title

    def setWindowTitle(self, title):
        self.write_count += 1
        self._title = title


class QGroupBox(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self._title = title
        self.write_count = 0

    def title(self):
        return self._title

    def setTitle(self, title):
        self.write_count += 1
        self._title = title


class QTabBar(QWidget):
    def __init__(self, tabs=None, parent=None):
        super().__init__(parent)
        self.tabs = list(tabs or [])
        self.tabMoved = Signal()
        self.write_count = 0

    def count(self):
        return len(self.tabs)

    def removeTab(self, index):
        self.tabs.pop(index)

    def insertTab(self, index, text):
        self.tabs.insert(index, text)

    def moveTab(self, old, new):
        self.tabs.insert(new, self.tabs.pop(old))
        self.tabMoved.emit(old, new)

    def tabText(self, index):
        return self.tabs[index]

    def setTabText(self, index, text):
        self.write_count += 1
        self.tabs[index] = text


class QToolBar(QWidget):
    def actions(self):
        return getattr(self, "_actions", [])


class QToolBox(QWidget):
    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self.items = list(items or [])
        self.pages = [QWidget(self) for _ in self.items]
        self.write_count = 0

    def count(self):
        return len(self.items)

    def widget(self, index):
        return self.pages[index]

    def removeItem(self, index):
        self.items.pop(index)
        self.pages.pop(index)

    def insertItem(self, index, page, text):
        self.items.insert(index, text)
        self.pages.insert(index, page)

    def moveItem(self, old, new):
        self.items.insert(new, self.items.pop(old))
        self.pages.insert(new, self.pages.pop(old))

    def itemText(self, index):
        return self.items[index]

    def setItemText(self, index, text):
        self.write_count += 1
        self.items[index] = text


class QApplication(QObject):
    current = None

    def __init__(self, windows=None):
        super().__init__()
        self.windows = windows or []
        self.filters = []
        self.aboutToQuit = Signal()
        QApplication.current = self

    @staticmethod
    def instance():
        return QApplication.current

    def topLevelWidgets(self):
        return self.windows

    def installEventFilter(self, obj):
        self.filters.append(obj)

    def removeEventFilter(self, obj):
        self.filters.remove(obj)


class QMessageBox:
    warnings = []

    @classmethod
    def warning(cls, _parent, title, message):
        cls.warnings.append((title, message))


class QTimer:
    jobs = []

    @classmethod
    def singleShot(cls, _delay, fn):
        cls.jobs.append(fn)

    @classmethod
    def flush(cls):
        jobs, cls.jobs = cls.jobs, []
        for fn in jobs:
            fn()


class QEvent:
    ActionAdded = 1
    ActionChanged = 2
    Show = 3
    ChildAdded = 4
    LanguageChange = 5
    Polish = 6
    PolishRequest = 7
    Paint = 8


class QStandardPaths:
    AppConfigLocation = 1
    location = ""

    @staticmethod
    def writableLocation(_type):
        return QStandardPaths.location


@pytest.fixture(autouse=True)
def fake_modules(monkeypatch, tmp_path):
    """Supply the small part of Qt used by the plugin."""
    QStandardPaths.location = str(tmp_path / "krita-config")
    QApplication.current = None
    QTimer.jobs = []
    QMessageBox.warnings = []
    pyqt = types.ModuleType("PyQt5")
    core = types.ModuleType("PyQt5.QtCore")
    widgets = types.ModuleType("PyQt5.QtWidgets")
    sip = types.ModuleType("PyQt5.sip")
    core.QObject = QObject
    core.QEvent = QEvent
    core.QTimer = QTimer
    core.QStandardPaths = QStandardPaths
    core.Qt = types.SimpleNamespace(RichText=1, AutoText=0)
    for klass in (
        QApplication, QWidget, QDialog, QMenu, QMenuBar, QAbstractButton,
        QLabel, QGroupBox, QTabBar, QToolBox, QDockWidget, QToolBar,
        QMainWindow, QMessageBox,
    ):
        setattr(widgets, klass.__name__, klass)
    sip.isdeleted = lambda _obj: False
    pyqt.sip = sip
    for name, module in (
        ("PyQt5", pyqt), ("PyQt5.QtCore", core),
        ("PyQt5.QtWidgets", widgets), ("PyQt5.sip", sip),
    ):
        monkeypatch.setitem(sys.modules, name, module)

    # Import policy and guard without executing __init__.py (needs Krita).
    pkg = types.ModuleType("Z_Mnemonics_Disabler")
    pkg.__path__ = [str(ROOT / "Z_Mnemonics_Disabler")]
    monkeypatch.setitem(sys.modules, "Z_Mnemonics_Disabler", pkg)
    for name in ("policy", "guard", "main"):
        sys.modules.pop("Z_Mnemonics_Disabler." + name, None)
    yield


def modules():
    policy = importlib.import_module("Z_Mnemonics_Disabler.policy")
    guard = importlib.import_module("Z_Mnemonics_Disabler.guard")
    return policy, guard


@pytest.mark.parametrize("source,expected", [
    ("&File", "File"),
    ("E&dit", "Edit"),
    ("Save &As...", "Save As..."),
    ("A && B", "A && B"),
    ("AT&T", "AT&&T"),
    ("A & B", "A && B"),
    ("R&D", "R&&D"),
    ("&Open && Close", "Open && Close"),
    ("A &amp; B", "A &amp; B"),
    ("<b>&Open</b>", "<b>&Open</b>"),
    ("Nothing to change", "Nothing to change"),
])
def test_text_policy(source, expected):
    policy, _ = modules()
    assert policy.strip_mnemonics(source) == expected


def test_config_upgrade_and_persistence(monkeypatch, tmp_path):
    policy, _ = modules()
    legacy = tmp_path / "old_config.json"
    legacy.write_text('{"enabled": false}', encoding="utf-8")
    monkeypatch.setattr(policy, "LEGACY_CONFIG", legacy)
    assert policy.load_enabled() is False
    assert policy.save_enabled(True)
    assert policy.config_path().parent.is_dir()
    assert policy.load_enabled() is True
    assert legacy.read_text(encoding="utf-8") == '{"enabled": false}'


def test_menu_and_action_restore_exact_originals():
    _, guard_module = modules()
    window = QWidget()
    bar = QMenuBar(window)
    menu = QMenu("&File", bar)
    # QAction text may differ from the QMenu title.
    menu.menuAction().setText("&Files")
    bar.add(menu.menuAction())
    menu.add(QAction("&Open"))
    app = QApplication([window])
    guard = guard_module.GlobalMnemonicGuard({}, app)
    guard.set_enabled(True)
    assert menu.title() == "File"
    assert menu.menuAction().text() == "Files"
    # Submenu entries are processed when that menu first opens.
    guard._visit_menu(menu, "top")
    assert menu.actions()[0].text() == "Open"
    guard.set_enabled(False)
    assert menu.title() == "&File"
    assert menu.menuAction().text() == "&Files"
    assert menu.actions()[0].text() == "&Open"
    assert not app.filters
    assert not guard._tracked


def test_repeated_scans_do_not_lose_original():
    _, guard_module = modules()
    window = QWidget()
    bar = QMenuBar(window)
    menu = QMenu("&Edit", bar)
    bar.add(menu.menuAction())
    app = QApplication([window])
    guard = guard_module.GlobalMnemonicGuard({}, app)
    guard.set_enabled(True)
    guard.scan_existing_windows()
    guard.scan_existing_windows()
    guard.set_enabled(False)
    assert menu.title() == "&Edit"
    assert menu.menuAction().text() == "&Edit"


def test_dynamic_label_and_rich_text():
    _, guard_module = modules()
    window = QWidget()
    plain = QLabel("&Select", window)
    rich = QLabel("<a href='https://example.org?a=1&amp;b=2'>&Link</a>", window)
    app = QApplication([window])
