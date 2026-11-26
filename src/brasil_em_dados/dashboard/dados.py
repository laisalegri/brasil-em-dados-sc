"""Leitura dos dados do app: só as funções de brasil_em_dados.analise.consultas, com cache.

- Conexão bed_readonly (engine_readonly), cada consulta numa transação READ ONLY.
- st.cache_resource guarda o engine; st.cache_data guarda cada DataFrame (a GOLD só muda com uma
  nova carga; para ver dados novos, limpe o cache no menu do app ou reinicie).
- Falha de conexão ou de configuração vira ErroDados, sem a mensagem original: ela pode trazer
  host, usuário ou banco. O app mostra MENSAGEM_ERRO, e o log registra só o tipo do erro e o
  código SQLSTATE, que ajuda no diagnóstico (ex.: 28P01, senha recusada).
"""

import logging
from collections.abc import Callable

import pandas as pd
import streamlit as st
from sqlalchemy import Engine

from brasil_em_dados import db
from brasil_em_dados.analise import consultas

logger = logging.getLogger(__name__)

MENSAGEM_ERRO = ("Não foi possível ler os dados do banco. Confira se o PostgreSQL local está no ar "
                 "e se o arquivo .env está configurado (veja o README); depois, recarregue a "
                 "página.")
ERROS_DE_CONEXAO = db.ERROS_DE_CONEXAO
sqlstate = db.sqlstate  # mantidos aqui pelo nome usado nos testes e no log

# Colunas numéricas: uma coluna toda vazia num recorte chega como object (None); vira float com
# NaN. É conversão de tipo, não de unidade (regra 11).
COLUNAS_NUMERICAS = frozenset({
    "valor", "valor_anterior", "total_estado", "participacao_percentual", "variacao_absoluta",
    "variacao_percentual", "pop_estimada", "pop_censo", "pib_corrente_reais",
    "pib_per_capita_reais", "pop_censo_2010", "pop_censo_2022", "municipios_somados",
    "municipios_sem_valor", "municipios_excluidos", "ano_instalacao", "linhas",
})


class ErroDados(Exception):
    """Falha ao ler a GOLD; a mensagem é sempre MENSAGEM_ERRO (sem detalhes da conexão)."""

    def __init__(self) -> None:
        super().__init__(MENSAGEM_ERRO)


def normalizar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    """Converte as colunas numéricas conhecidas para número (ausente continua ausente)."""
    saida = df.copy()
    for nome in COLUNAS_NUMERICAS.intersection(saida.columns):
        saida[nome] = pd.to_numeric(saida[nome], errors="raise").astype("float64")
    return saida


@st.cache_resource(show_spinner=False)
def _engine() -> Engine:
    return db.engine_readonly()


def ler(funcao: Callable[..., pd.DataFrame], *args: object) -> pd.DataFrame:
    """Chama uma função de consultas com o engine bed_readonly; erro de conexão vira ErroDados."""
    try:
        return normalizar_tipos(funcao(_engine(), *args))
    except ERROS_DE_CONEXAO as exc:
        logger.warning("Falha ao ler a GOLD (%s, SQLSTATE %s); detalhes omitidos.",
                       type(exc).__name__, sqlstate(exc))
        raise ErroDados() from None


@st.cache_data(show_spinner="Lendo a camada GOLD…")
def municipios() -> pd.DataFrame:
    """Cadastro dos 295 municípios com as regiões (filtros e rótulos)."""
    return ler(consultas.municipios)


@st.cache_data(show_spinner="Lendo a camada GOLD…")
def agregado(nivel: str, indicador: str) -> pd.DataFrame:
    """Totais prontos de estado ou região (agregado_regiao_ano; regra C1)."""
    return ler(consultas.agregado, nivel, indicador)


@st.cache_data(show_spinner="Lendo a camada GOLD…")
def participacao(indicador: str, ano: int) -> pd.DataFrame:
    """Participação de cada município no total do estado, num ano."""
    return ler(consultas.participacao, indicador, ano)


@st.cache_data(show_spinner="Lendo a camada GOLD…")
def participacao_serie(indicador: str) -> pd.DataFrame:
    """Participação de cada município em todos os anos."""
    return ler(consultas.participacao_serie, indicador)


@st.cache_data(show_spinner="Lendo a camada GOLD…")
def variacao_censo() -> pd.DataFrame:
    """Variação entre os Censos 2010 e 2022 por município."""
    return ler(consultas.variacao_censo)


@st.cache_data(show_spinner="Lendo a camada GOLD…")
def painel(ano: int) -> pd.DataFrame:
    """Painel município × indicadores de um ano."""
    return ler(consultas.painel, ano)


@st.cache_data(show_spinner="Lendo a camada GOLD…")
def painel_serie() -> pd.DataFrame:
    """Painel município × indicadores de todos os anos."""
    return ler(consultas.painel_serie)


@st.cache_data(show_spinner="Lendo a camada GOLD…")
def variacao_anual(indicador: str) -> pd.DataFrame:
    """Variação anual por município, com comparável e motivo (regra 12)."""
    return ler(consultas.variacao_anual, indicador)


@st.cache_data(show_spinner="Lendo a camada GOLD…")
def fontes_series() -> pd.DataFrame:
    """Uma linha por série de origem: fonte, unidade, anos e última coleta."""
    return ler(consultas.fontes_series)


@st.cache_data(show_spinner="Lendo a camada GOLD…")
def cobertura() -> pd.DataFrame:
    """Linhas da grade por indicador e status."""
    return ler(consultas.cobertura)
