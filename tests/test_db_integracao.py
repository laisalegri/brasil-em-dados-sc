"""Testes de integração com o PostgreSQL local (D17).

Rodam só quando o banco está disponível; caso contrário, são pulados.
Nenhum teste altera dados: as tentativas de criar tabela rodam em transações desfeitas.
O .env é lido num dicionário local (db.ler_ambiente): os segredos não vão para os.environ.
Para rodar só estes: `pytest -m integracao`; para pular: `pytest -m "not integracao"`.
"""

import socket
from collections.abc import Callable, Iterator, Mapping

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, OperationalError

from brasil_em_dados import db

pytestmark = pytest.mark.integracao

TIMEOUT_PORTA_S = 3
# Bloqueios aceitos ao tentar criar tabela como bed_readonly:
SQLSTATE_SEM_PRIVILEGIO = "42501"     # insufficient_privilege (falta CREATE/TEMPORARY)
SQLSTATE_SOMENTE_LEITURA = "25006"    # read_only_sql_transaction (default_transaction_read_only)
BLOQUEIOS = {SQLSTATE_SEM_PRIVILEGIO, SQLSTATE_SOMENTE_LEITURA}
TABELA_TESTE = "teste_permissao_readonly"


def _servidor_aceita_conexao(host: str, porta: int) -> bool:
    """Indica se a porta do servidor aceita conexão TCP (sem autenticar)."""
    try:
        with socket.create_connection((host, porta), timeout=TIMEOUT_PORTA_S):
            return True
    except OSError:
        return False


def _engine_ou_pular(criar: Callable[[Mapping[str, str]], Engine]) -> Engine:
    """Cria o engine e testa a conexão.

    Pula se faltar configuração ou se a porta do servidor não aceitar conexão.
    Se o servidor estiver no ar e recusar (senha errada, banco inexistente), FALHA:
    isso é configuração quebrada, não banco indisponível.
    """
    try:
        engine = criar(db.ler_ambiente())
    except db.ErroConfiguracao as exc:
        pytest.skip(f"Banco não configurado: {exc}")
    if not _servidor_aceita_conexao(engine.url.host, engine.url.port):
        engine.dispose()
        pytest.skip(f"Banco indisponível em {engine.url.host}:{engine.url.port}")
    try:
        with engine.connect():
            pass
    except OperationalError as exc:
        engine.dispose()
        # A mensagem do libpq traz usuário, host e banco, nunca a senha.
        pytest.fail(f"Servidor no ar, mas recusou a conexão: {exc.orig}", pytrace=False)
    return engine


@pytest.fixture(scope="module")
def engine_app() -> Iterator[Engine]:
    engine = _engine_ou_pular(db.engine_app)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def engine_readonly() -> Iterator[Engine]:
    engine = _engine_ou_pular(db.engine_readonly)
    yield engine
    engine.dispose()


def _sqlstate_ao_executar_desfazendo(engine: Engine, sql: str) -> str | None:
    """Executa `sql` numa transação sempre desfeita; devolve o SQLSTATE do erro ou None."""
    with engine.connect() as conn:
        transacao = conn.begin()
        try:
            conn.execute(text(sql))
        except DBAPIError as exc:
            return getattr(exc.orig, "sqlstate", None)
        finally:
            transacao.rollback()  # mesmo se o comando passasse, nada fica no banco
    return None


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
    sqlstate = _sqlstate_ao_executar_desfazendo(
        engine_readonly, f"CREATE TABLE public.{TABELA_TESTE} (x integer)")
    assert sqlstate in BLOQUEIOS, f"CREATE TABLE não foi bloqueado (SQLSTATE {sqlstate})"
    # O que importa: a tabela não existe.
    with engine_readonly.connect() as conn:
        existe = conn.execute(text(f"SELECT to_regclass('public.{TABELA_TESTE}')")).scalar()
    assert existe is None


def test_bed_readonly_nao_consegue_criar_tabela_temporaria(engine_readonly):
    sqlstate = _sqlstate_ao_executar_desfazendo(
        engine_readonly, f"CREATE TEMP TABLE {TABELA_TESTE} (x integer)")
    assert sqlstate in BLOQUEIOS, f"CREATE TEMP TABLE não foi bloqueado (SQLSTATE {sqlstate})"
