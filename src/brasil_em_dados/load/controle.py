"""Carga do controle de execução (D21): data/controle/execucoes.jsonl → silver.controle_execucao.

O arquivo só recebe acréscimos: cada execução, identificada por (cod_serie, inicio), entra uma
vez. Se o banco tiver a mesma execução com conteúdo diferente, a carga é recusada (ErroCarga).
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import Connection

from brasil_em_dados.config import ARQUIVO_CONTROLE
from brasil_em_dados.extract.controle import ler_execucoes
from brasil_em_dados.load.upsert import ErroCarga, EspecTabela, Linha, Resumo, upsert

logger = logging.getLogger("brasil_em_dados.load.controle")

COLUNAS_CONTROLE = ("cod_serie", "inicio", "fim", "status", "n_registros", "arquivo", "erro")
CONTROLE = EspecTabela(
    "silver.controle_execucao", ("cod_serie", "inicio"), COLUNAS_CONTROLE,
    imutaveis=("fim", "status", "n_registros", "arquivo", "erro"),
    orientacao_imutavel=("O execucoes.jsonl só recebe acréscimos: uma execução registrada "
                         "não muda. Confira se o arquivo foi editado."))


def linha_controle(registro: dict) -> Linha:
    """Converte um registro do JSONL (datas ISO 8601 em UTC) numa linha da tabela."""
    try:
        linha = {coluna: registro[coluna] for coluna in COLUNAS_CONTROLE}
        for coluna in ("inicio", "fim"):
            linha[coluna] = datetime.fromisoformat(linha[coluna])
    except (KeyError, TypeError, ValueError) as exc:
        raise ErroCarga(f"Registro do controle fora do formato: {registro!r} ({exc})") from exc
    if linha["inicio"].tzinfo is None or linha["fim"].tzinfo is None:
        raise ErroCarga(f"Registro do controle sem fuso horário: {registro!r}")
    return linha


def ler_controle(arquivo: Path = ARQUIVO_CONTROLE) -> list[Linha]:
    """Linhas do JSONL (lista vazia se o arquivo não existir)."""
    try:
        registros = ler_execucoes(arquivo)
    except (OSError, json.JSONDecodeError) as exc:
        raise ErroCarga(f"Controle de execução ilegível ({arquivo}): {exc}") from exc
    return [linha_controle(r) for r in registros]


def carregar_controle(conexao: Connection, arquivo: Path = ARQUIVO_CONTROLE) -> Resumo:
    """Acrescenta as execuções novas; as já carregadas ficam como estão."""
    linhas = ler_controle(arquivo)
    logger.info("Controle de execução: %d registros em %s", len(linhas), arquivo)
    return upsert(conexao, CONTROLE, linhas)
