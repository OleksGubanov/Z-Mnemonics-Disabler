# Changelog

## [1.0.0] — 2026-11-11

First public release of Z Mnemonics Disabler for Krita.

### Features

- Disables Qt Alt menu mnemonics in supported Krita menus and controls.
- Handles new windows, dialogs, context menus, and dynamically updated labels.
- Adds a checkable **Tools → Z Mnemonics Disabler** switch.
- Restores original interface labels when the switch is turned off, where the originals can be identified safely.
- Saves the enabled/disabled setting in Krita's user configuration directory.
- Uses no external Python dependencies beyond Krita's PyQt5 environment.

### Fixes made before release

- Removed mnemonic flicker by processing changed labels before painting instead of after it.
- Protected rich text and visible ampersands from unsafe text changes.
- Improved restoration of menus and their related QAction labels.
- Tracked moved, inserted, and removed tabs and toolbox pages more carefully.
- Avoided unnecessary rewrites on repeated Paint events.
- Added protection when saving a preference or changing the Qt event filter fails.

### Testing and known limitations

- 50 automated tests using simulated Qt objects.
- Target: Krita 5.4.3 on Windows; other Krita versions and operating systems are not confirmed.
- Some operating-system shortcuts and Krita Canvas Input shortcuts remain unaffected.
- If an original mnemonic cannot be identified uniquely after dynamic changes, the plugin prefers not to guess.

See [README.md](README.md) for installation, usage, compatibility, and limitations.
