"""Testes da configuração de logs."""

import logging

from brasil_em_dados.logs import NOME_LOGGER, configurar_logging


def test_configurar_logging_grava_em_arquivo(tmp_path):
    logger = logging.getLogger(NOME_LOGGER)
    try:
        arquivo = configurar_logging(tmp_path)
        logging.getLogger("brasil_em_dados.extract.teste").info("mensagem de teste")
        for handler in logger.handlers:
            handler.flush()
        assert arquivo.parent == tmp_path
        assert "mensagem de teste" in arquivo.read_text(encoding="utf-8")
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()


def test_configurar_duas_vezes_nao_duplica_handlers(tmp_path):
    logger = logging.getLogger(NOME_LOGGER)
    try:
        configurar_logging(tmp_path)
        configurar_logging(tmp_path)
        assert len(logger.handlers) == 2
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
