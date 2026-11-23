"""Consultas da análise: cada função lê um arquivo de sql/analise/ e devolve um DataFrame.

Só views do schema gold; conexão como bed_readonly (engine_readonly) e transação READ ONLY.
"""

import re
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, text

from brasil_em_dados.config import PASTA_CONSULTAS_ANALISE
from brasil_em_dados.db import transacao_somente_leitura

_NOME = re.compile(r"^[a-z][a-z0-9_]*$")
_ORIGEM = re.compile(r"\b(?:FROM|JOIN)\s+([A-Za-z_]\w*)(\.)?", re.IGNORECASE)
_CTE = re.compile(r"(?:\bWITH|,)\s+([A-Za-z_]\w*)\s+AS\s*\(", re.IGNORECASE)
INDICADORES = ("pop_estimada", "pop_censo", "pib_corrente", "pib_per_capita")
NIVEIS = ("estado", "regiao_intermediaria", "regiao_imediata")


class ErroConsulta(Exception):
    """Consulta inexistente, fora da GOLD ou com parâmetro inválido."""


def ler_sql(nome: str, pasta: Path = PASTA_CONSULTAS_ANALISE) -> str:
    """Texto de sql/analise/<nome>.sql; recusa nome fora do padrão e leitura fora do schema gold."""
    if not _NOME.match(nome):
        raise ErroConsulta(f"Nome de consulta inválido: {nome!r}")
    arquivo = pasta / f"{nome}.sql"
    if not arquivo.is_file():
        raise ErroConsulta(f"Consulta inexistente: {arquivo.name}")
    sql = arquivo.read_text(encoding="utf-8")
    ctes = {nome.lower() for nome in _CTE.findall(sql)}
    schemas, sem_schema = set(), set()
    for nome, ponto in _ORIGEM.findall(sql):
        if ponto:
            schemas.add(nome.lower())
        elif nome.lower() not in ctes:
            sem_schema.add(nome)  # resolvido pelo search_path: poderia ser silver ou public
    if schemas != {"gold"} or sem_schema:
        raise ErroConsulta(f"{arquivo.name}: a análise só lê views do schema gold "
                           f"(schemas: {sorted(schemas)}; sem schema: {sorted(sem_schema)})")
    return sql


def consultar(engine: Engine, nome: str, **parametros: object) -> pd.DataFrame:
    """Roda a consulta `nome` com parâmetros nomeados (:parametro) e devolve um DataFrame."""
    with transacao_somente_leitura(engine) as conexao:
        return pd.read_sql(text(ler_sql(nome)), conexao, params=parametros)


def _exigir(valor: str, permitidos: tuple[str, ...], rotulo: str) -> None:
    if valor not in permitidos:
        raise ErroConsulta(f"{rotulo} inválido: {valor!r}; use um de {permitidos}")


def participacao(engine: Engine, indicador: str, ano: int) -> pd.DataFrame:
    """Participação de cada município no total de SC (maior valor primeiro)."""
    _exigir(indicador, ("pop_estimada", "pop_censo", "pib_corrente"), "Indicador")
    return consultar(engine, "participacao_estadual", indicador=indicador, ano=ano)


def variacao_censo(engine: Engine) -> pd.DataFrame:
    """Censo 2010 × Censo 2022 por município, com a região intermediária."""
    return consultar(engine, "variacao_populacao_censo")


def agregado(engine: Engine, nivel: str, indicador: str) -> pd.DataFrame:
    """Somas por nível territorial e ano (sem per capita agregado, regra 4)."""
    _exigir(nivel, NIVEIS, "Nível")
    _exigir(indicador, ("pop_estimada", "pop_censo", "pib_corrente"), "Indicador")
    return consultar(engine, "agregado_regiao", nivel=nivel, indicador=indicador)


def painel(engine: Engine, ano: int) -> pd.DataFrame:
    """Uma linha por município no ano, com estimativa e Censo em colunas separadas."""
    return consultar(engine, "painel_ano", ano=ano)


def variacao_anual(engine: Engine, indicador: str) -> pd.DataFrame:
    """Variação ano a ano por município (pop_estimada ou pib_corrente)."""
    _exigir(indicador, ("pop_estimada", "pib_corrente"), "Indicador")
    return consultar(engine, "variacao_anual", indicador=indicador)
