"""Orquestra uma coleta: baixar, validar, gravar na RAW e registrar no controle (D11)."""

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from brasil_em_dados.config import ARQUIVO_CONTROLE, PASTA_RAW
from brasil_em_dados.extract import catalogo
from brasil_em_dados.extract.cliente_http import RespostaHTTP, baixar
from brasil_em_dados.extract.controle import registrar_execucao
from brasil_em_dados.extract.raw import gravar_coleta, versao_extrator
from brasil_em_dados.extract.validacao import validar_resposta

logger = logging.getLogger(__name__)


def agora_utc() -> datetime:
    """Instante atual em UTC."""
    return datetime.now(timezone.utc)


def coletar(
    cod_serie: str,
    *,
    pasta_raw: Path = PASTA_RAW,
    arquivo_controle: Path = ARQUIVO_CONTROLE,
    sessao: requests.Session | None = None,
    baixar_fn: Callable[[str, requests.Session | None], RespostaHTTP] = baixar,
    agora: Callable[[], datetime] = agora_utc,
    versao: str | None = None,
) -> dict[str, Any]:
    """Coleta uma fonte do catálogo; em falha, registra o erro e relança a exceção."""
    fonte = catalogo.obter(cod_serie)
    inicio = agora()
    logger.info("Iniciando coleta de %s", cod_serie)
    try:
        resposta = baixar_fn(fonte.url_extrator, sessao)
        n_registros = validar_resposta(resposta.status_http, resposta.conteudo, fonte.fonte)
        meta = gravar_coleta(
            fonte, resposta, n_registros,
            pasta_raw=pasta_raw, coletado_em=agora(), versao=versao or versao_extrator(),
        )
    except Exception as exc:
        logger.exception("Coleta de %s falhou: %s", cod_serie, exc)
        try:
            registrar_execucao(
                arquivo_controle, cod_serie=cod_serie, inicio=inicio, fim=agora(),
                status="falha", n_registros=None, arquivo=None,
                erro=f"{type(exc).__name__}: {exc}",
            )
        except OSError as erro_controle:
            logger.warning("Não foi possível registrar a falha no controle de execução: %s",
                           erro_controle)
        raise exc
    registrar_execucao(
        arquivo_controle, cod_serie=cod_serie, inicio=inicio, fim=agora(), status="sucesso",
        n_registros=n_registros, arquivo=f"{cod_serie}/{meta['arquivo_dados']}", erro=None,
    )
    return meta
