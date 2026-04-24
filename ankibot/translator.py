from __future__ import annotations

from deep_translator import GoogleTranslator

from ankibot.config import TranslationConfig


class TranslatorService:
    def __init__(self, config: TranslationConfig) -> None:
        self.config = config

    def translate(self, text: str, target_language: str | None = None) -> str:
        normalized_text = str(text).strip()
        if not normalized_text:
            return ""

        target = (target_language or self.config.default_target_language).strip()
        if not target:
            return normalized_text

        if self.config.provider != "google":
            raise ValueError(f"Provedor de traducao nao suportado: {self.config.provider}")

        source = self.config.source_language.strip() or "auto"
        translator = GoogleTranslator(source=source, target=target)
        return translator.translate(normalized_text)
