"""Fixtures compartilhadas dos testes de integração com o PostgreSQL local.

Pulam se faltar configuração ou se a porta do banco não aceitar conexão; FALHAM se o servidor
estiver no ar e recusar (senha errada, banco inexistente), para não esconder configuração quebrada.
O .env é lido num dicionário local (db.ler_ambiente): os segredos não vão para os.environ.
"""

import socket
from collections.abc import Callable, Iterator, Mapping

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from brasil_em_dados import db

TIMEOUT_PORTA_S = 3


def _servidor_aceita_conexao(host: str, porta: int) -> bool:
    """Indica se a porta do servidor aceita conexão TCP (sem autenticar)."""
    try:
        with socket.create_connection((host, porta), timeout=TIMEOUT_PORTA_S):
            return True
    except OSError:
        return False


def _engine_ou_pular(criar: Callable[[Mapping[str, str]], Engine]) -> Engine:
    """Cria o engine e testa a conexão; pula ou falha conforme a docstring do módulo."""
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


@pytest.fixture(scope="session")
def engine_app() -> Iterator[Engine]:
    engine = _engine_ou_pular(db.engine_app)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def engine_readonly() -> Iterator[Engine]:
    engine = _engine_ou_pular(db.engine_readonly)
    yield engine
    engine.dispose()
