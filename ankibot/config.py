from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TranslationConfig:
    enabled: bool
    provider: str
    source_column: str
    output_field: str
    source_language: str
    default_target_language: str


@dataclass
class AudioConfig:
    enabled: bool
    provider: str
    voice: str
    rate_wpm: int
    media_prefix: str


@dataclass
class AppConfig:
    watch_folder: Path
    anki_connect_url: str
    anki_auto_start: bool
    anki_app_name: str
    anki_startup_wait_seconds: int
    default_deck: str
    default_note_type: str
    unique_field: str
    deck_strategy: str
    processed_state_file: Path
    log_file: Path
    archive_folder: Path
    move_processed_files: bool
    dry_run: bool
    translation: TranslationConfig
    audio: AudioConfig
    supported_extensions: list[str]
    required_columns: list[str]
    optional_columns: list[str]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppConfig":
        return cls(
            watch_folder=Path(payload["watch_folder"]).expanduser(),
            anki_connect_url=payload["anki_connect_url"],
            anki_auto_start=bool(payload.get("anki_auto_start", True)),
            anki_app_name=str(payload.get("anki_app_name", "Anki")),
            anki_startup_wait_seconds=int(payload.get("anki_startup_wait_seconds", 20)),
            default_deck=payload["default_deck"],
            default_note_type=payload["default_note_type"],
            unique_field=payload["unique_field"],
            deck_strategy=str(payload.get("deck_strategy", "file_name")),
            processed_state_file=Path(payload["processed_state_file"]).expanduser(),
            log_file=Path(payload["log_file"]).expanduser(),
            archive_folder=Path(payload["archive_folder"]).expanduser(),
            move_processed_files=bool(payload.get("move_processed_files", False)),
            dry_run=bool(payload.get("dry_run", False)),
            translation=TranslationConfig(
                enabled=bool(payload.get("translation", {}).get("enabled", False)),
                provider=str(payload.get("translation", {}).get("provider", "google")),
                source_column=str(payload.get("translation", {}).get("source_column", "frente")),
                output_field=str(payload.get("translation", {}).get("output_field", "verso")),
                source_language=str(payload.get("translation", {}).get("source_language", "auto")),
                default_target_language=str(
                    payload.get("translation", {}).get("default_target_language", "en")
                ),
            ),
            audio=AudioConfig(
                enabled=bool(payload.get("audio", {}).get("enabled", False)),
                provider=str(payload.get("audio", {}).get("provider", "macos_say")),
                voice=str(payload.get("audio", {}).get("voice", "Samantha")),
                rate_wpm=int(payload.get("audio", {}).get("rate_wpm", 175)),
                media_prefix=str(payload.get("audio", {}).get("media_prefix", "ankibot")),
            ),
            supported_extensions=list(payload.get("supported_extensions", [])),
            required_columns=list(payload.get("required_columns", [])),
            optional_columns=list(payload.get("optional_columns", [])),
        )


def load_config(config_path: str | Path) -> AppConfig:
    with Path(config_path).expanduser().open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return AppConfig.from_dict(payload)
