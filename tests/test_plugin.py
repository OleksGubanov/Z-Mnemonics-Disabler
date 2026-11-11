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
