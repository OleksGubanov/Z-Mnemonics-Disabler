# SPDX-License-Identifier: GPL-3.0-only

"""Small helpers for menu text and the on/off preference."""

import json
import os
import re
import tempfile
from pathlib import Path

from PyQt5.QtCore import QStandardPaths


# Internal options stay enabled. The Tools menu controls only the main switch.
DEFAULTS = {
    "enabled": True,
    "main_menu": True,
    "nested_menus": True,
    "context_menus": True,
    "dialog_tabs": True,
    "dialog_buttons": True,
    "dialog_labels": True,
    "dialog_groups": True,
    "toolbox_pages": True,
    "dock_titles": True,
    "all_windows": True,
    "dynamic_actions": True,
    "dynamic_widgets": True,
    "late_updates": True,
}

# Older installations kept the switch beside the plugin source.
LEGACY_CONFIG = Path(__file__).with_name("config.json")
CONFIG_NAME = "Z_Mnemonics_Disabler.json"

# Rich-text labels can contain HTML entities (&amp;) and URLs. Leave them alone.
_HTML_TAG = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>|<!DOCTYPE", re.IGNORECASE)
_HTML_ENTITY = re.compile(r"&(?:[a-zA-Z][a-zA-Z0-9]*|#[0-9]+|#x[0-9a-fA-F]+);")


def looks_like_rich_text(text):
    """Avoid changing HTML markup in labels."""
    return bool(_HTML_TAG.search(text) or _HTML_ENTITY.search(text))


def strip_mnemonics(label):
    """Remove Qt &mnemonics without damaging literal ampersands.

    In Qt, && means a visible ampersand. A single & before a letter
    normally marks a shortcut. Text like AT&T is ambiguous, so keep
    its visible ampersand by escaping it as &&.
    """
    text = str(label)
    if "&" not in text or looks_like_rich_text(text):
        return text

    result = []
    i = 0
    while i < len(text):
        if text[i] != "&":
            result.append(text[i])
            i += 1
            continue

        if i + 1 < len(text) and text[i + 1] == "&":
            result.append("&&")
            i += 2
            continue

        before = text[i - 1] if i else ""
        after = text[i + 1] if i + 1 < len(text) else ""

        # Abbreviations such as AT&T are usually literal text.
        abbreviation = before.isupper() and after.isupper()
        # An ampersand before a space or punctuation is not a letter shortcut.
        literal = not after.isalnum() or abbreviation

        if literal:
            result.append("&&")
        # Otherwise drop the mnemonic marker, keeping the following letter.
        i += 1

    return "".join(result)


def validated(options):
    """Use one public switch; avoid loading removed experimental options."""
    enabled = options.get("enabled") if isinstance(options, dict) else None
    return {**DEFAULTS, "enabled": enabled if type(enabled) is bool else True}


def config_path():
    """Keep preferences in Krita's config area, not in the plugin folder."""
    folder = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
    if not folder:
        folder = str(Path.home() / ".config" / "krita")
    return Path(folder) / CONFIG_NAME


def load_enabled():
    """Read the new preference, or a legacy config on first upgrade."""
    current = config_path()
    source = current if current.exists() else LEGACY_CONFIG
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
        return validated(data)["enabled"]
    except (OSError, ValueError, UnicodeError):
        return True


def save_enabled(enabled):
    """Write safely so a crash cannot leave a half-written config."""
    path = config_path()
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=str(path.parent),
            prefix=".zmd-", suffix=".tmp", delete=False,
        ) as file:
            temporary = Path(file.name)
            json.dump({"enabled": bool(enabled)}, file, indent=2)
            file.write("\n")
        os.replace(str(temporary), str(path))
        return True
    except OSError:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        return False
