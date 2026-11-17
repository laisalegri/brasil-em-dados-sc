"""Testes de integração das conexões e dos usuários (D17).

Fixtures em conftest.py. Nenhum teste altera dados: as tentativas de criar tabela rodam em
transações desfeitas. Para rodar só estes: `pytest -m integracao`; para pular: `-m "not integracao"`.
"""

import pytest
from sqlalchemy import text

from tests.apoio_banco import BLOQUEIOS_READONLY, sqlstate_em_transacao_desfeita

pytestmark = pytest.mark.integracao

TABELA_TESTE = "teste_permissao_readonly"


def test_bed_app_conecta_no_banco_do_projeto(engine_app):
    with engine_app.connect() as conn:
        usuario, banco = conn.execute(text("SELECT current_user, current_database()")).one()
    assert (usuario, banco) == ("bed_app", "brasil_em_dados")


def test_bed_readonly_conecta_no_banco_do_projeto(engine_readonly):
    with engine_readonly.connect() as conn:
        usuario, banco = conn.execute(text("SELECT current_user, current_database()")).one()
    assert (usuario, banco) == ("bed_readonly", "brasil_em_dados")


def test_bed_readonly_tem_transacao_somente_leitura_por_padrao(engine_readonly):
    with engine_readonly.connect() as conn:
        valor = conn.execute(text("SHOW default_transaction_read_only")).scalar()
    assert valor == "on"


def test_bed_readonly_nao_consegue_criar_tabela(engine_readonly):
    sqlstate = sqlstate_em_transacao_desfeita(
        engine_readonly,
        lambda conn: conn.execute(text(f"CREATE TABLE public.{TABELA_TESTE} (x integer)")))
    assert sqlstate in BLOQUEIOS_READONLY, f"CREATE TABLE não foi bloqueado (SQLSTATE {sqlstate})"
    # O que importa: a tabela não existe.
    with engine_readonly.connect() as conn:
        existe = conn.execute(text(f"SELECT to_regclass('public.{TABELA_TESTE}')")).scalar()
    assert existe is None


def test_bed_readonly_nao_consegue_criar_tabela_temporaria(engine_readonly):
    sqlstate = sqlstate_em_transacao_desfeita(
        engine_readonly,
        lambda conn: conn.execute(text(f"CREATE TEMP TABLE {TABELA_TESTE} (x integer)")))
    assert sqlstate in BLOQUEIOS_READONLY, (
        f"CREATE TEMP TABLE não foi bloqueado (SQLSTATE {sqlstate})")
