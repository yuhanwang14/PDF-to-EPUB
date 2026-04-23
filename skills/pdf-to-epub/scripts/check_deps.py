"""Pre-flight dependency check.

Run before Step 1 of the pipeline. Verifies Python packages, CLI tools,
and disk space for PaddleOCR model cache. Prints an install command for
anything missing and exits non-zero so the caller can stop early.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

PY_PACKAGES = [
    ("paddle", "paddlepaddle"),          # import name, pip name
    ("paddleocr", "paddleocr"),
    ("paddlex", "paddlex[ocr]"),
    ("PIL", "pillow"),
]

CLI_TOOLS = [
    # (command, brew pkg, homepage)
    ("pandoc", "pandoc", "https://pandoc.org"),
    ("pdftoppm", "poppler", "https://poppler.freedesktop.org"),
    ("pdfinfo", "poppler", "https://poppler.freedesktop.org"),
    ("magick", "imagemagick", "https://imagemagick.org"),
]

MODEL_CACHE = Path.home() / ".paddlex" / "official_models"
MODEL_CACHE_NEED_GB = 1.5


def check_py() -> list[tuple[str, str]]:
    missing: list[tuple[str, str]] = []
    for imp_name, pip_name in PY_PACKAGES:
        if importlib.util.find_spec(imp_name) is None:
            missing.append((imp_name, pip_name))
    return missing


def check_cli() -> list[tuple[str, str, str]]:
    missing: list[tuple[str, str, str]] = []
    for cmd, brew, url in CLI_TOOLS:
        if shutil.which(cmd) is None:
            missing.append((cmd, brew, url))
    return missing


def check_disk() -> tuple[bool, float]:
    """Returns (ok, free_gb). Checks $HOME's filesystem."""
    total, used, free = shutil.disk_usage(Path.home())
    free_gb = free / (1024 ** 3)
    # Need enough room for models PLUS some for the OCR pages/artifacts
    return free_gb >= MODEL_CACHE_NEED_GB + 2, free_gb


def main() -> int:
    py_missing = check_py()
    cli_missing = check_cli()
    disk_ok, free_gb = check_disk()
    models_cached = MODEL_CACHE.exists() and any(MODEL_CACHE.iterdir())

    if not py_missing and not cli_missing and disk_ok:
        print("✓ All dependencies present.")
        if models_cached:
            size_gb = sum(p.stat().st_size for p in MODEL_CACHE.rglob("*") if p.is_file()) / (1024 ** 3)
            print(f"✓ PaddleOCR models cached at {MODEL_CACHE} ({size_gb:.1f} GB)")
        else:
            print(f"  PaddleOCR models will download on first OCR run (~1.3 GB → {MODEL_CACHE})")
        print(f"  Free disk: {free_gb:.1f} GB")
        return 0

    print("Missing dependencies:\n")

    if py_missing:
        print("Python packages:")
        for imp_name, pip_name in py_missing:
            print(f"  ✗ {imp_name}")
        pip_cmd = "pip install " + " ".join(f"'{pkg}'" for _, pkg in py_missing)
        print(f"\n  Install: {pip_cmd}\n")

    if cli_missing:
        print("CLI tools:")
        for cmd, _, url in cli_missing:
            print(f"  ✗ {cmd}  ({url})")
        brew_pkgs = sorted({brew for _, brew, _ in cli_missing})
        print(f"\n  Install: brew install {' '.join(brew_pkgs)}\n")

    if not disk_ok:
        print(f"✗ Low disk space: {free_gb:.1f} GB free, need ≥ {MODEL_CACHE_NEED_GB + 2:.1f} GB")
        print("  (PaddleOCR models + per-book OCR artifacts)\n")

    return 1


if __name__ == "__main__":
    sys.exit(main())
