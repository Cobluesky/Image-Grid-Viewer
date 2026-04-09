from __future__ import annotations

import os
import sys
from pathlib import Path


def _remove_conda_entries_from_path() -> None:
    raw_path = os.environ.get("PATH", "")
    if not raw_path:
        return

    cleaned_parts: list[str] = []
    for part in raw_path.split(os.pathsep):
        lower = part.lower()
        if "anaconda" in lower or "miniconda" in lower or "\\conda\\" in lower:
            continue
        cleaned_parts.append(part)
    os.environ["PATH"] = os.pathsep.join(cleaned_parts)


def _prepend_bundle_dirs() -> None:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundle_root = Path(meipass)
    else:
        bundle_root = Path(sys.executable).resolve().parent / "_internal"

    candidate_dirs = [
        bundle_root,
        bundle_root / "PySide6",
        bundle_root / "shiboken6",
    ]
    existing = [str(path) for path in candidate_dirs if path.exists()]
    if not existing:
        return

    current_path = os.environ.get("PATH", "")
    os.environ["PATH"] = os.pathsep.join(existing + ([current_path] if current_path else []))

    try:
        os.add_dll_directory(str(bundle_root))
        if (bundle_root / "PySide6").exists():
            os.add_dll_directory(str(bundle_root / "PySide6"))
        if (bundle_root / "shiboken6").exists():
            os.add_dll_directory(str(bundle_root / "shiboken6"))
    except (AttributeError, FileNotFoundError, OSError):
        pass


for key in (
    "PYTHONHOME",
    "PYTHONPATH",
    "QT_PLUGIN_PATH",
    "QML2_IMPORT_PATH",
    "QT_QPA_PLATFORM_PLUGIN_PATH",
    "CONDA_PREFIX",
    "CONDA_DEFAULT_ENV",
    "CONDA_PROMPT_MODIFIER",
    "CONDA_EXE",
):
    os.environ.pop(key, None)

_remove_conda_entries_from_path()
_prepend_bundle_dirs()
