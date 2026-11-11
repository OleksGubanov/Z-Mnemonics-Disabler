# Z Mnemonics Disabler

**Free Alt+letter keyboard shortcuts in Krita.**

Z Mnemonics Disabler is a small Python plugin for Krita. It removes Qt menu mnemonic markers (the `&` in labels such as `&File`) so those Alt+letter combinations can be used for personal shortcuts instead of menu navigation.

Created by **Oleksandr Gubanov (Zingless)** with help from **OpenAI ChatGPT**. The name uses the `Z` prefix found in my other tools.

## Why?

I wanted to use Alt as a shortcut modifier in **Krita 5.4.3**. Qt menu mnemonics can get in the way of combinations such as Alt+F. I used [Cellosia's Unbind Alt Shortcuts](https://github.com/Cellosia/krita-unbind-alt-shortcuts) as an idea and technical reference. That project's README lists Krita 5.2.2 as its last tested version; I haven't tested the original myself.

## What it does

- Removes mnemonic markers from supported menus, submenus, dialogs, and controls.
- Watches for newly opened menus and changed interface text.
- Adds a checkable **Tools → Z Mnemonics Disabler** switch.
- Restores original labels when the switch is turned off, if Krita hasn't changed them in the meantime.
- Saves the switch state in Krita's user configuration directory.

It **does not** intercept keystrokes, change your shortcuts automatically, or override operating-system shortcuts. Rich-text labels are deliberately left untouched to avoid damaging links and HTML formatting.

## Install

1. Open [**Releases**](../../releases) in this GitHub repository.
2. Download **Z_Mnemonics_Disabler_v1.0.0.zip** from the **v1.0.0** release assets. Do not use GitHub's auto-generated *Source code (zip)* archive.
3. In Krita, select **Tools → Scripts → Import Python Plugin…** and choose the downloaded ZIP.
4. Enable the plugin under **Settings → Configure Krita → Python Plugin Manager**, if it is not already enabled.
5. Restart Krita.
6. Find the switch at **Tools → Z Mnemonics Disabler**.

The plugin starts enabled by default. To assign a shortcut, use Krita's **Settings → Configure Krita → Keyboard Shortcuts**.

## Compatibility

- **Target:** Krita 5.4.3 / PyQt5.
- **Primary platform:** Windows.
- Other systems and Krita versions have not been verified.
- Krita 6 / Qt6 compatibility has not been established.

The plugin was developed for Krita 5.4.3 on Windows. The developer checked an earlier release candidate in Krita; later changes address tab/page tracking and passed automated tests. The suite includes **50 tests using simulated Qt objects**, which do not replace testing inside Krita. Other configurations are not yet verified.

## Important limitations

- Some Alt combinations may still belong to Krita Canvas Input or the operating system.
- Disabling mnemonics also removes Alt-based keyboard navigation for the affected menus and controls. This may not suit users who depend on keyboard-only menu access.
- Labels containing rich text or ambiguous formatting may intentionally remain unchanged.
- The plugin modifies Qt labels globally while enabled; unusual third-party UI elements may require compatibility fixes.
- If a label is changed by Krita after the plugin edits it, the plugin avoids restoring outdated text when you switch it off.
- If identical-looking tabs had different original mnemonic positions and one disappears without an identifiable move, the original for the remaining tab can be ambiguous. In that case, the plugin avoids guessing which mnemonic to restore.

## Remove / update

To disable it, uncheck **Tools → Z Mnemonics Disabler**. To stop loading it, uncheck the plugin in Krita's **Python Plugin Manager** and restart Krita.

To remove it completely, open **Settings → Manage Resources → Open Resource Folder** and delete only `pykrita/Z_Mnemonics_Disabler.desktop` and `pykrita/Z_Mnemonics_Disabler/`; then restart Krita. Your saved switch state is stored separately in Krita's configuration folder.

For an update, install the new release ZIP and restart Krita. The separate setting file helps preserve the switch state when the plugin folder is replaced.

## For developers

The GitHub repository includes the plugin files, tests, and a tiny ZIP builder:

```bash
python -m pytest -q tests
python tools/build_release.py
```

Automated tests use small Qt mock objects; they do not replace testing with real Krita.

## Credits and license

The project was designed by Oleksandr Gubanov (Zingless) and implemented and refined with ChatGPT assistance, including code generation and debugging. It was inspired by Cellosia's [Unbind Alt Shortcuts](https://github.com/Cellosia/krita-unbind-alt-shortcuts). The comparison found the same general approach and standard Krita API calls, but no distinctive copied code sequences. See [CREDITS.md](CREDITS.md) for details.

Released under **GNU GPL-3.0-only**. This is an unofficial community project, not an official Krita extension.
