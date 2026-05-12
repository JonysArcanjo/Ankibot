from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import time

from ankibot.anki_client import AnkiClient, AnkiConnectError
from ankibot.config import load_config
from ankibot.logging_utils import setup_logging
from ankibot.sync_service import SyncService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sincroniza flashcards de planilhas com o Anki.")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Caminho do arquivo de configuracao.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula as operacoes sem alterar o Anki.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    logger = setup_logging(config.log_file)
    anki_client = AnkiClient(config.anki_connect_url, unique_field=config.unique_field)
    anki_started_by_ankibot = False

    try:
        anki_client.ping()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "AnkiConnect indisponivel em %s. Vou tentar abrir o Anki automaticamente. Detalhe: %s",
            config.anki_connect_url,
            exc,
        )
        anki_ready, anki_started_by_ankibot = ensure_anki_ready(config, anki_client, logger)
        if not anki_ready:
            logger.error(
                "Nao foi possivel conectar ao AnkiConnect em %s. Abra o Anki e confirme o add-on. Detalhe: %s",
                config.anki_connect_url,
                exc,
            )
            if anki_started_by_ankibot:
                close_anki(config, logger)
            return 1

    service = SyncService(config=config, anki_client=anki_client, logger=logger)

    try:
        summary = service.run(dry_run=args.dry_run)
    except AnkiConnectError as exc:
        logger.error("Erro do AnkiConnect: %s", exc)
        exit_code = 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha inesperada durante a sincronizacao: %s", exc)
        exit_code = 1
    else:
        logger.info(
            "Concluido | arquivos escaneados=%s processados=%s ignorados=%s criados=%s atualizados=%s linhas_ignoradas=%s",
            summary.scanned_files,
            summary.processed_files,
            summary.skipped_files,
            summary.created_notes,
            summary.updated_notes,
            summary.skipped_rows,
        )
        exit_code = 0

    if anki_started_by_ankibot:
        close_anki(config, logger)
    return exit_code


def ensure_anki_ready(config, anki_client: AnkiClient, logger) -> tuple[bool, bool]:
    if not config.anki_auto_start:
        return False, False

    if platform.system() != "Darwin":
        return False, False

    try:
        subprocess.run(
            ["open", "-a", config.anki_app_name],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Falha ao tentar abrir o app %s: %s", config.anki_app_name, exc)
        return False, False

    timeout_seconds = max(config.anki_startup_wait_seconds, 1)
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            anki_client.ping()
            logger.info("AnkiConnect respondeu apos abrir o Anki.")
            return True, True
        except Exception:  # noqa: BLE001
            time.sleep(1)

    return False, True


def close_anki(config, logger) -> None:
    if platform.system() != "Darwin":
        return

    try:
        completed = subprocess.run(
            ["osascript", "-e", f'tell application "{config.anki_app_name}" to quit'],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao tentar fechar o app %s: %s", config.anki_app_name, exc)
        return

    if completed.returncode == 0:
        logger.info("App %s fechado apos a execucao do Ankibot.", config.anki_app_name)
        return

    logger.warning(
        "Nao foi possivel fechar o app %s automaticamente: %s",
        config.anki_app_name,
        completed.stderr.strip() or completed.stdout.strip(),
    )


if __name__ == "__main__":
    sys.exit(main())
