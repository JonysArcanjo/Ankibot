from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import requests

from ankibot.models import FlashcardRow


class AnkiConnectError(RuntimeError):
    pass


class AnkiClient:
    def __init__(self, url: str, unique_field: str) -> None:
        self.url = url
        self.unique_field = unique_field

    def ping(self) -> None:
        self._invoke("version")

    def find_note_id(self, row: FlashcardRow, deck: str | None = None) -> int | None:
        field_query = f'"{self.unique_field}:{row.external_id}"'
        if deck:
            query = f'deck:"{deck}" {field_query}'
        else:
            query = field_query
        note_ids = self._invoke("findNotes", query=query)
        return int(note_ids[0]) if note_ids else None

    def add_note(self, row: FlashcardRow, deck: str, note_type: str) -> Any:
        payload = {
            "deckName": deck,
            "modelName": note_type,
            "fields": row.anki_fields(),
            "tags": row.tags or [],
        }
        return self._invoke("addNote", note=payload)

    def update_note(self, note_id: int, row: FlashcardRow) -> Any:
        return self._invoke(
            "updateNoteFields",
            note={
                "id": note_id,
                "fields": row.anki_fields(),
            },
        )

    def add_tags(self, note_id: int, tags: list[str]) -> Any:
        if not tags:
            return None
        return self._invoke("addTags", notes=[note_id], tags=" ".join(tags))

    def create_deck(self, deck_name: str) -> Any:
        return self._invoke("createDeck", deck=deck_name)

    def deck_names(self) -> list[str]:
        return list(self._invoke("deckNames"))

    def store_media_file(self, file_path: Path, filename: str | None = None) -> str:
        target_name = filename or file_path.name
        data = base64.b64encode(file_path.read_bytes()).decode("ascii")
        return self._invoke("storeMediaFile", filename=target_name, data=data)

    def _invoke(self, action: str, **params: Any) -> Any:
        response = requests.post(
            self.url,
            json={"action": action, "version": 6, "params": params},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            raise AnkiConnectError(str(payload["error"]))
        return payload.get("result")
