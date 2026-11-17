"""Constantes e funções de apoio dos testes de integração com o banco (sem fixtures)."""

from collections.abc import Callable

from sqlalchemy import Connection, Engine
from sqlalchemy.exc import DBAPIError

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
