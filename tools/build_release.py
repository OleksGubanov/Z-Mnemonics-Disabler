"""Create the ZIP that Krita's Python Plugin Importer expects."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = "Z_Mnemonics_Disabler"
VERSION = "1.0.0"

FILES = [
    ROOT / f"{PLUGIN}.desktop",
    *(ROOT / PLUGIN / name for name in (
        "__init__.py", "main.py", "guard.py", "policy.py", "config.json",
    )),
]


def build():
    destination = ROOT / "dist" / f"{PLUGIN}_v{VERSION}.zip"
    destination.parent.mkdir(exist_ok=True)
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for path in FILES:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.write(ROOT / "LICENSE", f"{PLUGIN}/LICENSE")
        archive.write(ROOT / "CREDITS.md", f"{PLUGIN}/CREDITS.md")
    print(f"Created: {destination}")


if __name__ == "__main__":
    build()
