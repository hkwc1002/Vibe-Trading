"""State-file backup and restore utilities for the Low Absorb module.

Business-logic read/write (``save`` / ``_load``) stays in ``storage.py``;
this module handles *file-level* backup naming, directory selection,
and safe restore with validation.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pydantic

from ..storage import JsonLowAbsorbStorage


def export_state(storage: JsonLowAbsorbStorage, target_dir: str | Path) -> Path:
    """Copy the current state file to *target_dir* with a timestamp suffix.

    The backup file is named ``low_absorb_state_<YYYYMMDDTHHMMSS>.json``.
    Existing files are **never** overwritten — if the exact same timestamp
    exists, a counter suffix ``_N`` is appended.

    Returns the path to the newly created backup file.
    """
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    stem = f"low_absorb_state_{timestamp}"
    dest = target / f"{stem}.json"

    # Avoid overwrite — append _N if the exact name exists
    counter = 1
    while dest.exists():
        dest = target / f"{stem}_{counter}.json"
        counter += 1

    shutil.copy2(storage.path, dest)
    return dest


def load_state(storage: JsonLowAbsorbStorage, source_path: str | Path) -> None:
    """Restore state from a backup file created by ``export_state``.

    Steps:
    1. Validate the source file through the full Pydantic load pipeline
       (dry-run, so the current state is never touched on failure).
    2. Create a safety backup of the current state first.
    3. Atomically replace the current state file with the restored data.
    4. Reload the storage from the new file.

    Raises ``ValueError`` or ``pydantic.ValidationError`` if the source
    file fails validation — the current state is **never** modified on
    failure.
    """
    source = Path(source_path)
    if not source.exists():
        raise ValueError(f"Backup file not found: {source}")

    # ── Step 1: full Pydantic dry-run validation ──────────────────────────
    # Create a throw-away JsonLowAbsorbStorage to run the entire _load()
    # pipeline (every record goes through model_validate).  The real state
    # is NOT touched at this point.
    try:
        raw = source.read_text(encoding="utf-8")
        # Validate JSON syntax explicitly — _load() silently catches
        # JSONDecodeError, so we check here first.
        json.loads(raw)
        dry = JsonLowAbsorbStorage(source)
        dry._load()
    except (json.JSONDecodeError, OSError, pydantic.ValidationError) as exc:
        raise ValueError(f"Backup file validation failed: {exc}") from exc

    # ── Step 2: safety backup of current state ────────────────────────────
    current_path = storage.path
    if current_path.exists():
        safety_stem = f".state_pre_restore_{datetime.now():%Y%m%dT%H%M%S}"
        safety_path = current_path.parent / safety_stem
        shutil.copy2(current_path, safety_path)

    # ── Step 3: atomic replace ────────────────────────────────────────────
    fd, tmp_path = tempfile.mkstemp(
        suffix=".json",
        prefix=".state_restore_",
        dir=current_path.parent,
    )
    try:
        with open(fd, "w", encoding="utf-8") as f:
            f.write(raw)
        # Atomic on the same filesystem
        tmp = Path(tmp_path)
        tmp.replace(current_path)
    except OSError as exc:
        # Clean up temp file on failure
        Path(tmp_path).unlink(missing_ok=True)
        raise OSError(f"Failed to atomically replace state file: {exc}") from exc

    # ── Step 4: reload ────────────────────────────────────────────────────
    storage._load()
