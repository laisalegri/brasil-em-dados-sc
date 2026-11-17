"""Conexões SQLAlchemy com o PostgreSQL do projeto, a partir das variáveis de ambiente (D17).

Dois perfis: `app` (bed_app, escrita, usado pelo pipeline) e `readonly` (bed_readonly,
somente leitura, usado pelos agentes). A senha nunca aparece em log nem em mensagem de erro.
O .env é lido num dicionário local: os segredos não vão para o ambiente do processo.
"""

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL

from brasil_em_dados.config import RAIZ_PROJETO

logger = logging.getLogger(__name__)

ARQUIVO_ENV: Path = RAIZ_PROJETO / ".env"
DRIVER = "postgresql+psycopg"
TIMEOUT_CONEXAO_S = 10  # sem isso, um servidor que não responde trava o pipeline e os testes
PORTA_MAXIMA = 65535


class ErroConfiguracao(Exception):
    """Variáveis de ambiente do banco ausentes ou inválidas (a mensagem nunca traz valores)."""


@dataclass(frozen=True)
class Perfil:
    """Nomes das variáveis de ambiente de usuário e senha de um perfil de conexão."""

    nome: str
    var_usuario: str
    var_senha: str


PERFIL_APP = Perfil("app", "PG_USER", "PG_PASSWORD")
PERFIL_READONLY = Perfil("readonly", "PG_READONLY_USER", "PG_READONLY_PASSWORD")
VARS_COMUNS = ("PG_HOST", "PG_PORT", "PG_DATABASE")


def ler_ambiente(arquivo: Path | None = None) -> dict[str, str]:
    """Junta o .env e as variáveis do processo num dicionário; o processo tem precedência.

    Não altera os.environ.
    """
    do_arquivo = dotenv_values(arquivo or ARQUIVO_ENV)
    valores = {chave: valor for chave, valor in do_arquivo.items() if valor is not None}
    return {**valores, **os.environ}


def _porta(texto: str) -> int:
    """Converte PG_PORT; o erro não repete o valor recebido."""
    if not (texto.isascii() and texto.isdecimal()) or not 1 <= int(texto) <= PORTA_MAXIMA:
        raise ErroConfiguracao(f"PG_PORT deve ser um inteiro entre 1 e {PORTA_MAXIMA}")
    return int(texto)


def montar_url(perfil: Perfil, ambiente: Mapping[str, str]) -> URL:
    """Monta a URL de conexão do perfil; falha listando só os NOMES das variáveis faltantes."""
    nomes = (*VARS_COMUNS, perfil.var_usuario, perfil.var_senha)
    faltando = [nome for nome in nomes if not ambiente.get(nome)]
    if faltando:
        raise ErroConfiguracao(
            f"Variáveis de ambiente ausentes para o perfil {perfil.nome}: {', '.join(faltando)}")
    return URL.create(
        DRIVER,
        username=ambiente[perfil.var_usuario],
        password=ambiente[perfil.var_senha],
        host=ambiente["PG_HOST"],
        port=_porta(ambiente["PG_PORT"]),
        database=ambiente["PG_DATABASE"],
    )


def descrever_url(url: URL) -> str:
    """Texto da URL com a senha mascarada, seguro para log."""
    return url.render_as_string(hide_password=True)


def _criar_engine(perfil: Perfil, ambiente: Mapping[str, str] | None) -> Engine:
    """Cria o engine do perfil (sem conectar); sem `ambiente`, lê o .env e o processo."""
    url = montar_url(perfil, ler_ambiente() if ambiente is None else ambiente)
    logger.info("Engine do perfil %s: %s", perfil.nome, descrever_url(url))
    # hide_parameters: valores de parâmetros SQL não entram nas mensagens de erro.
    return create_engine(url, hide_parameters=True, pool_pre_ping=True,
                         connect_args={"connect_timeout": TIMEOUT_CONEXAO_S})


def engine_app(ambiente: Mapping[str, str] | None = None) -> Engine:
    """Engine do usuário de escrita (bed_app), usado pelo pipeline."""
    return _criar_engine(PERFIL_APP, ambiente)


def engine_readonly(ambiente: Mapping[str, str] | None = None) -> Engine:
    """Engine do usuário somente leitura (bed_readonly), usado pelos agentes."""
    return _criar_engine(PERFIL_READONLY, ambiente)
