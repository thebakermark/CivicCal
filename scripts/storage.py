"""Replaceable storage boundary for CivicCal identity state.

The initial backend is a human-inspectable JSON file. Future backends must
implement the same small interface; pipeline code should not depend on a
specific database or storage engine.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Protocol


class IdentityStateStore(Protocol):
    """Persistence contract consumed by the event identity tracker."""

    def load_identity_state(self) -> dict[str, Any] | None:
        """Return the previous state, or None when no state exists."""
        ...

    def save_identity_state(self, state: dict[str, Any]) -> None:
        """Persist a complete replacement state."""
        ...


class JsonFileIdentityStateStore:
    """Atomic JSON-file implementation of the identity-state contract."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load_identity_state(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        with self.path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError("Identity state JSON must contain an object.")
        return value

    def save_identity_state(self, state: dict[str, Any]) -> None:
        if not isinstance(state, dict):
            raise ValueError("Identity state must be an object.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rendered = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=str(self.path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.path)
        except BaseException:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise
