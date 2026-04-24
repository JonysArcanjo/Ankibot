from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FlashcardRow:
    external_id: str
    front: str = ""
    back: str = ""
    target_language: str = ""
    audio: str = ""
    tags: list[str] | None = None
    deck: str | None = None
    note_type: str | None = None
    updated_at: str = ""
    source_file: str = ""

    def anki_fields(self) -> dict[str, str]:
        return {
            "external_id": self.external_id,
            "frente": self.front,
            "verso": self.back,
            "updated_at": self.updated_at,
            "source_file": self.source_file,
        }
