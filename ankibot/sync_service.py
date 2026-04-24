from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from ankibot.anki_client import AnkiClient
from ankibot.audio_service import AudioService
from ankibot.config import AppConfig
from ankibot.models import FlashcardRow
from ankibot.readers import load_rows
from ankibot.state import StateStore
from ankibot.translator import TranslatorService


@dataclass
class SyncSummary:
    scanned_files: int = 0
    processed_files: int = 0
    skipped_files: int = 0
    created_notes: int = 0
    updated_notes: int = 0
    skipped_rows: int = 0


class SyncService:
    def __init__(self, config: AppConfig, anki_client: AnkiClient, logger) -> None:
        self.config = config
        self.anki_client = anki_client
        self.logger = logger
        self.state = StateStore(config.processed_state_file)
        self.translator = TranslatorService(config.translation) if config.translation.enabled else None
        self.audio_service = AudioService(config.audio) if config.audio.enabled else None
        self._ensured_decks: set[str] = set()
        self._existing_decks: set[str] | None = None

    def run(self, dry_run: bool | None = None) -> SyncSummary:
        effective_dry_run = self.config.dry_run if dry_run is None else dry_run
        summary = SyncSummary()
        tracked_files = self._list_input_files()
        previous_state = self.state.load()
        next_state = dict(previous_state)

        for file_path in tracked_files:
            summary.scanned_files += 1
            current_mtime = file_path.stat().st_mtime
            state_key = str(file_path.resolve())
            file_deck = self._resolve_file_deck(file_path)

            if previous_state.get(state_key) == current_mtime:
                if self._deck_exists(file_deck):
                    summary.skipped_files += 1
                    continue
                self.logger.info(
                    "Arquivo sem alteracao, mas o baralho %s nao existe no Anki. Reprocessando.",
                    file_deck,
                )

            self.logger.info("Processando arquivo: %s", file_path)
            rows = load_rows(file_path, config=self.config, translator=self.translator)
            file_summary = self._sync_rows(
                rows,
                file_path=file_path,
                file_deck=file_deck,
                dry_run=effective_dry_run,
            )
            summary.processed_files += 1
            summary.created_notes += file_summary.created_notes
            summary.updated_notes += file_summary.updated_notes
            summary.skipped_rows += file_summary.skipped_rows
            next_state[state_key] = current_mtime

            if self.config.move_processed_files and not effective_dry_run:
                self._archive_file(file_path)

        if not effective_dry_run:
            self.state.save(next_state)
        return summary

    def _sync_rows(
        self,
        rows: list[FlashcardRow],
        file_path: Path,
        file_deck: str,
        dry_run: bool,
    ) -> SyncSummary:
        summary = SyncSummary()
        self._ensure_deck_exists(file_deck, dry_run=dry_run)
        progress = ProgressBar(total=len(rows), label=file_path.stem)

        for index, row in enumerate(rows, start=1):
            row = self._prepare_row(row=row, dry_run=dry_run)
            deck = file_deck or self.config.default_deck
            self._ensure_deck_exists(deck, dry_run=dry_run)
            note_type = row.note_type or self.config.default_note_type
            note_id = self.anki_client.find_note_id(row, deck=deck)

            if note_id is None:
                if dry_run:
                    self.logger.info("[DRY RUN] Criaria nota %s em %s", row.external_id, deck)
                else:
                    self.anki_client.add_note(row, deck=deck, note_type=note_type)
                    self.logger.info("Nota criada: %s", row.external_id)
                summary.created_notes += 1
                progress.advance(index)
                continue

            if dry_run:
                self.logger.info("[DRY RUN] Atualizaria nota %s (id=%s)", row.external_id, note_id)
            else:
                self.anki_client.update_note(note_id, row)
                self.anki_client.add_tags(note_id, row.tags or [])
                self.logger.info("Nota atualizada: %s (id=%s)", row.external_id, note_id)
            summary.updated_notes += 1
            progress.advance(index)
        progress.finish()
        return summary

    def _resolve_file_deck(self, file_path: Path) -> str:
        if self.config.deck_strategy == "file_name":
            relative_path = file_path.relative_to(self.config.watch_folder)
            deck_parts = [part.strip() for part in relative_path.parts[:-1] if part.strip()]
            deck_parts.append(file_path.stem.strip())
            return "::".join(part for part in deck_parts if part)
        return self.config.default_deck

    def _ensure_deck_exists(self, deck_name: str, dry_run: bool) -> None:
        if not deck_name or deck_name in self._ensured_decks:
            return
        deck_hierarchy = build_deck_hierarchy(deck_name)
        if dry_run:
            for deck_level in deck_hierarchy:
                if deck_level in self._ensured_decks:
                    continue
                self.logger.info("[DRY RUN] Criaria/verificaria baralho %s", deck_level)
                self._ensured_decks.add(deck_level)
                self._add_existing_deck(deck_level)
            return
        for deck_level in deck_hierarchy:
            if deck_level in self._ensured_decks:
                continue
            self.anki_client.create_deck(deck_level)
            self.logger.info("Baralho garantido: %s", deck_level)
            self._ensured_decks.add(deck_level)
            self._add_existing_deck(deck_level)

    def _prepare_row(self, row: FlashcardRow, dry_run: bool) -> FlashcardRow:
        if row.audio or not self.audio_service:
            return row

        back_text = extract_back_text(row.back)
        if not back_text:
            return row

        if dry_run:
            simulated_name = self.audio_service.build_filename(back_text)
            row.audio = f"[sound:{simulated_name}]"
            row.back = append_audio_to_back(back_text, row.audio)
            self.logger.info("[DRY RUN] Geraria audio para %s", row.external_id)
            return row

        audio_file = self.audio_service.synthesize(back_text)
        stored_name = self.anki_client.store_media_file(audio_file)
        row.audio = f"[sound:{stored_name}]"
        row.back = append_audio_to_back(back_text, row.audio)
        self.logger.info("Audio gerado para %s: %s", row.external_id, stored_name)
        return row

    def _list_input_files(self) -> list[Path]:
        watch_folder = self.config.watch_folder
        watch_folder.mkdir(parents=True, exist_ok=True)
        supported = {extension.lower() for extension in self.config.supported_extensions}
        return sorted(
            file_path
            for file_path in watch_folder.rglob("*")
            if file_path.is_file() and file_path.suffix.lower() in supported
        )

    def _archive_file(self, file_path: Path) -> None:
        self.config.archive_folder.mkdir(parents=True, exist_ok=True)
        destination = self.config.archive_folder / file_path.name
        shutil.move(str(file_path), str(destination))

    def _deck_exists(self, deck_name: str) -> bool:
        if not deck_name:
            return False
        existing_decks = self._load_existing_decks()
        return deck_name in existing_decks

    def _load_existing_decks(self) -> set[str]:
        if self._existing_decks is None:
            self._existing_decks = set(self.anki_client.deck_names())
        return self._existing_decks

    def _add_existing_deck(self, deck_name: str) -> None:
        if self._existing_decks is None:
            self._existing_decks = set()
        self._existing_decks.add(deck_name)


def extract_back_text(back: str) -> str:
    if "<br><br>[sound:" in back:
        return back.split("<br><br>[sound:", 1)[0]
    return back


def append_audio_to_back(back_text: str, audio_tag: str) -> str:
    if not audio_tag:
        return back_text
    return f"{back_text}<br><br>{audio_tag}"


def build_deck_hierarchy(deck_name: str) -> list[str]:
    parts = [part.strip() for part in deck_name.split("::") if part.strip()]
    hierarchy: list[str] = []
    current_parts: list[str] = []
    for part in parts:
        current_parts.append(part)
        hierarchy.append("::".join(current_parts))
    return hierarchy


class ProgressBar:
    def __init__(self, total: int, label: str) -> None:
        self.total = total
        self.label = label
        self.enabled = total > 0 and sys.stdout.isatty()
        self.width = 24
        self.step = 20
        self.last_reported_percent = -1

    def advance(self, current: int) -> None:
        if not self.enabled:
            return
        ratio = min(max(current / self.total, 0), 1)
        filled = int(self.width * ratio)
        bar = "#" * filled + "-" * (self.width - filled)
        percent = int(ratio * 100)
        milestone = min((percent // self.step) * self.step, 100)
        if current < self.total and milestone <= self.last_reported_percent:
            return
        if current < self.total and percent % self.step != 0:
            return
        self.last_reported_percent = 100 if current >= self.total else milestone
        sys.stdout.write(
            f"\r[{bar}] {self.last_reported_percent:3d}% {current}/{self.total} | {self.label}"
        )
        sys.stdout.flush()

    def finish(self) -> None:
        if not self.enabled:
            return
        sys.stdout.write("\n")
        sys.stdout.flush()
