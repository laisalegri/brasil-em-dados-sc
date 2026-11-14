"""Configuração de logs do pipeline: console e arquivo em logs/."""

import logging
from datetime import datetime, timezone
from pathlib import Path

from brasil_em_dados.config import PASTA_LOGS

NOME_LOGGER = "brasil_em_dados"
FORMATO = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configurar_logging(pasta_logs: Path = PASTA_LOGS, nivel: int = logging.INFO) -> Path:
    """Envia os logs do pacote para o console e para um arquivo diário (UTC); devolve o arquivo."""
    logger = logging.getLogger(NOME_LOGGER)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    pasta_logs.mkdir(parents=True, exist_ok=True)
    arquivo = pasta_logs / f"pipeline_{datetime.now(timezone.utc):%Y%m%d}.log"
    formatador = logging.Formatter(FORMATO)
    for handler in (logging.StreamHandler(), logging.FileHandler(arquivo, encoding="utf-8")):
        handler.setFormatter(formatador)
        logger.addHandler(handler)
    logger.setLevel(nivel)
    return arquivo
