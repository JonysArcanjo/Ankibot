from __future__ import annotations

import hashlib
import re
import subprocess
import tempfile
from pathlib import Path

from ankibot.config import AudioConfig


class AudioService:
    def __init__(self, config: AudioConfig) -> None:
        self.config = config

    def synthesize(self, text: str, voice: str | None = None) -> Path:
        normalized_text = str(text).strip()
        if not normalized_text:
            raise ValueError("Nao e possivel gerar audio para texto vazio.")
        if self.config.provider != "macos_say":
            raise ValueError(f"Provedor de audio nao suportado: {self.config.provider}")

        temp_dir = Path(tempfile.mkdtemp(prefix="ankibot_audio_"))
        filename = self.build_filename(normalized_text, voice=voice)
        output_path = temp_dir / filename
        selected_voice = (voice or self.config.voice).strip() or self.config.voice

        completed = subprocess.run(
            [
                "say",
                "-v",
                selected_voice,
                "-r",
                str(self.config.rate_wpm),
                "-o",
                str(output_path),
                normalized_text,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"Falha ao gerar audio com say: {completed.stderr.strip()}")
        return output_path

    def build_filename(self, text: str, voice: str | None = None) -> str:
        selected_voice = (voice or self.config.voice).strip() or self.config.voice
        slug_base = slugify(text)[:40] or "audio"
        digest = hashlib.sha1(f"{selected_voice}:{text}".encode("utf-8")).hexdigest()[:12]
        prefix = self.config.media_prefix.strip() or "ankibot"
        return f"{prefix}_{selected_voice}_{slug_base}_{digest}.aiff"


def slugify(value: str) -> str:
    lowered = value.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", lowered)
    return cleaned.strip("_")
