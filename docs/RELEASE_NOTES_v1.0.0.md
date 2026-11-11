# Z Mnemonics Disabler v1.0.0

**Free Alt+letter combinations from Qt menu mnemonic conflicts in Krita.**

Initial public release of a small Python plugin created for Krita 5.4.3 on Windows.

## Features

- Suppresses Qt menu mnemonics in supported menus, submenus, dialogs, and controls.
- Watches newly opened windows and dynamically updated labels.
- Provides an on/off switch at **Tools → Z Mnemonics Disabler**.
- Restores original labels when disabled, where recovery is unambiguous.
- Saves the switch state between Krita sessions.

## Download and install

1. Download **Z_Mnemonics_Disabler_v1.0.0.zip** under **Assets** below.
2. In Krita, open **Tools → Scripts → Import Python Plugin…** and choose this ZIP.
3. Enable **Z Mnemonics Disabler** in **Settings → Configure Krita → Python Plugin Manager** if prompted.
4. Restart Krita and find the toggle under **Tools → Z Mnemonics Disabler**.

**Do not use GitHub's automatically generated Source code ZIP as the plugin installer.**

## Compatibility and notes

- Developed for **Krita 5.4.3 / PyQt5 on Windows**. Other configurations are not verified.
- The plugin does not intercept keystrokes, configure your shortcuts for you, or override OS shortcuts.
- Disabling Qt Alt menu mnemonics also disables keyboard navigation through those mnemonics in affected menus and controls.
- 50 automated tests cover the text logic and simulated Qt interface events; these are not a substitute for testing in Krita.

## Credits

Created by **Oleksandr Gubanov (Zingless)** with development assistance from **OpenAI ChatGPT**, including code generation and debugging.

Inspired by [Cellosia's Unbind Alt Shortcuts](https://github.com/Cellosia/krita-unbind-alt-shortcuts), used as a technical reference. The original plugin was not tested during this project's development.

**License:** GPL-3.0-only. Source code and detailed documentation are in this repository.
