from __future__ import annotations

import json
from pathlib import Path


class StateStore:
    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self._write({})

    def load(self) -> dict[str, float]:
        with self.state_file.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def save(self, payload: dict[str, float]) -> None:
        self._write(payload)

    def _write(self, payload: dict[str, float]) -> None:
        with self.state_file.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True, sort_keys=True)
