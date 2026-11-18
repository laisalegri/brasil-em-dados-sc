"""Constantes e funções de apoio dos testes de integração com o banco (sem fixtures)."""

import re
from collections.abc import Callable
from decimal import Decimal

from sqlalchemy import Connection, Engine
from sqlalchemy.exc import DBAPIError

from brasil_em_dados.config import RAIZ_PROJETO

# Bloqueios esperados quando bed_readonly tenta escrever:
SQLSTATE_SEM_PRIVILEGIO = "42501"     # insufficient_privilege
SQLSTATE_SOMENTE_LEITURA = "25006"    # read_only_sql_transaction (default_transaction_read_only)
BLOQUEIOS_READONLY = frozenset({SQLSTATE_SEM_PRIVILEGIO, SQLSTATE_SOMENTE_LEITURA})


def sqlstate_em_savepoint(conexao: Connection, executar: Callable[[], object]) -> str | None:
    """Roda `executar` num savepoint desfeito em caso de erro; devolve o SQLSTATE ou None."""
    try:
        with conexao.begin_nested():
            executar()
    except DBAPIError as exc:
        return getattr(exc.orig, "sqlstate", None)
    return None


def sqlstate_em_transacao_desfeita(engine: Engine, executar: Callable[[Connection], object]
                                   ) -> str | None:
    """Roda `executar` numa transação sempre desfeita; devolve o SQLSTATE do erro ou None."""
    with engine.connect() as conexao:
        transacao = conexao.begin()
        try:
            executar(conexao)
        except DBAPIError as exc:
            return getattr(exc.orig, "sqlstate", None)
        finally:
            transacao.rollback()  # mesmo se o comando passasse, nada fica no banco
    return None


# Total de SC (N3) da 6579 em 2012 (D26, regra 13) ------------------------------------

DICIONARIO = RAIZ_PROJETO / "docs" / "dicionario_dados.md"
_REFERENCIA_TOTAL_SC_2012 = re.compile(r"`TOTAL_SC_6579_2012 = (\d+)`")


def total_sc_2012_documentado() -> Decimal:
    """Total de SC (N3) da 6579 em 2012: não está no banco; vem do valor de referência do
    dicionário (fonte: docs/fontes/alertas_qualidade_2026-11.md, consulta R3)."""
    encontrados = _REFERENCIA_TOTAL_SC_2012.findall(DICIONARIO.read_text(encoding="utf-8"))
    assert len(encontrados) == 1, (
        "valor de referência TOTAL_SC_6579_2012 ausente ou repetido no dicionário de dados")
    return Decimal(encontrados[0])
