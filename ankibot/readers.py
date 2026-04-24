from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from ankibot.config import AppConfig
from ankibot.models import FlashcardRow
from ankibot.translator import TranslatorService


def load_rows(
    file_path: Path,
    config: AppConfig,
    translator: TranslatorService | None = None,
) -> list[FlashcardRow]:
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        dataframe = pd.read_csv(file_path).fillna("")
    elif suffix == ".xlsx":
        dataframe = pd.read_excel(file_path).fillna("")
    elif suffix == ".numbers":
        converted_csv = export_numbers_to_csv(file_path)
        dataframe = pd.read_csv(converted_csv).fillna("")
    else:
        raise ValueError(f"Formato nao suportado: {file_path.suffix}")

    dataframe = normalize_input_columns(dataframe)
    dataframe = ensure_required_generated_columns(dataframe)
    validate_required_columns(dataframe, config.required_columns)
    return dataframe_to_rows(
        dataframe,
        source_file=file_path.name,
        config=config,
        translator=translator,
    )


def dataframe_to_rows(
    dataframe: pd.DataFrame,
    source_file: str,
    config: AppConfig,
    translator: TranslatorService | None = None,
) -> list[FlashcardRow]:
    rows: list[FlashcardRow] = []

    for index, raw_row in dataframe.iterrows():
        external_id = str(raw_row.get("external_id", "")).strip()
        if not external_id:
            external_id = build_generated_external_id(source_file=source_file, row_index=index)
        front = normalize_multiline(raw_row.get("frente", raw_row.get("prompt", "")))
        manual_back = normalize_multiline(raw_row.get("verso", raw_row.get("answer", "")))
        audio = str(raw_row.get("audio", "")).strip()
        target_language = str(
            raw_row.get("target_language", config.translation.default_target_language)
        ).strip()

        back_text = resolve_back_text(
            front=front,
            manual_back=manual_back,
            target_language=target_language,
            translation_enabled=config.translation.enabled,
            translator=translator,
        )
        back = compose_back_content(back_text=back_text, audio=audio)

        if not external_id or not front or not back:
            continue

        tags_value = str(raw_row.get("tags", "")).strip()
        tags = [tag for tag in tags_value.replace(",", " ").split() if tag]

        rows.append(
            FlashcardRow(
                external_id=external_id,
                front=front,
                back=back,
                target_language=target_language,
                audio=audio,
                tags=tags,
                deck=blank_to_none(raw_row.get("deck", "")),
                note_type=blank_to_none(raw_row.get("note_type", "")),
                updated_at=str(raw_row.get("updated_at", "")).strip(),
                source_file=source_file,
            )
        )
    return rows


def normalize_input_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    normalized_columns = {}
    for column in dataframe.columns:
        original = str(column).strip()
        lowered = original.lower()
        mapped = COLUMN_ALIASES.get(lowered, original)
        normalized_columns[column] = mapped

    dataframe = dataframe.rename(columns=normalized_columns)

    if "sentence" in dataframe.columns and "verso" not in dataframe.columns:
        dataframe["verso"] = dataframe.apply(
            lambda row: build_back_from_sentence_layout(row),
            axis=1,
        )

    if "back" in dataframe.columns and "audio" not in dataframe.columns:
        dataframe["audio"] = ""

    return dataframe


def ensure_required_generated_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    if "external_id" not in dataframe.columns:
        dataframe["external_id"] = ""
    return dataframe


def validate_required_columns(dataframe: pd.DataFrame, required_columns: list[str]) -> None:
    current_columns = {str(column).strip() for column in dataframe.columns}
    normalized_required = set(required_columns)
    missing_columns = sorted(normalized_required - current_columns)
    if missing_columns:
        joined = ", ".join(missing_columns)
        raise ValueError(f"Colunas obrigatorias ausentes: {joined}")


def normalize_multiline(value: object) -> str:
    text = str(value).strip()
    return text.replace("\n", "<br>")


def blank_to_none(value: object) -> str | None:
    text = str(value).strip()
    return text or None


def build_answer(
    back: str,
    target_language: str,
    translation_enabled: bool,
    translator: TranslatorService | None,
) -> str:
    if not back:
        return ""
    if not translation_enabled:
        return back
    if translator is None:
        raise ValueError("Traducao ativada, mas nenhum servico de traducao foi configurado.")
    translated = translator.translate(back.replace("<br>", "\n"), target_language=target_language)
    return normalize_multiline(translated)


def resolve_back_text(
    front: str,
    manual_back: str,
    target_language: str,
    translation_enabled: bool,
    translator: TranslatorService | None,
) -> str:
    if manual_back:
        return manual_back
    return build_answer(
        back=front,
        target_language=target_language,
        translation_enabled=translation_enabled,
        translator=translator,
    )


def compose_back_content(back_text: str, audio: str) -> str:
    if back_text and audio:
        return f"{back_text}<br><br>{audio}"
    return back_text or audio


def build_back_from_sentence_layout(row: pd.Series) -> str:
    back_value = normalize_multiline(row.get("verso", row.get("answer", row.get("back", ""))))
    sentence_value = normalize_multiline(row.get("sentence", ""))

    cleaned_back = clean_audio_marker(back_value)
    if sentence_value:
        return f"{cleaned_back}<br><br>💬 Sentence: {sentence_value}"
    return cleaned_back


def clean_audio_marker(value: str) -> str:
    return value.replace("(audio)", "").replace("(Audio)", "").strip()


def build_generated_external_id(source_file: str, row_index: int) -> str:
    base_name = Path(source_file).stem.lower().replace(" ", "_")
    return f"{base_name}_{row_index + 1:03d}"


COLUMN_ALIASES = {
    "front": "frente",
    "back": "back",
    "sentence": "sentence",
}


def export_numbers_to_csv(file_path: Path) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="ankibot_numbers_"))
    output_csv = temp_dir / f"{file_path.stem}.csv"

    script = f'''
    on run argv
        set inputPath to item 1 of argv
        set outputPath to item 2 of argv
        tell application "Numbers"
            activate
            open POSIX file inputPath
            tell front document
                export to POSIX file outputPath as CSV
                close saving no
            end tell
        end tell
    end run
    '''

    completed = subprocess.run(
        ["osascript", "-", str(file_path), str(output_csv)],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Falha ao exportar arquivo Numbers '{file_path.name}': {completed.stderr.strip()}"
        )
    return output_csv
