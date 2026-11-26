"""Filtros globais (docs/dashboards.md, seção 3): região intermediária, município e ano.

Os widgets são montados uma vez, na barra lateral, pelo app.py (ponto de entrada do
st.navigation). Assim o valor persiste ao trocar de página. As páginas leem os filtros com atuais().
O filtro de ano nunca troca o indicador de população: os visuais de Censo não o usam.
"""

from dataclasses import dataclass

import pandas as pd
import streamlit as st

ANOS = tuple(range(2010, 2024))
ANO_PADRAO = 2023
MUNICIPIO_PADRAO = "4205407"  # Florianópolis
CHAVE_REGIAO, CHAVE_MUNICIPIO, CHAVE_ANO = "filtro_regiao", "filtro_municipio", "filtro_ano"
CHAVE_FILTROS = "filtros"
TODAS = "Santa Catarina (todas)"


@dataclass(frozen=True)
class Filtros:
    """Seleção atual: cod_regiao None quer dizer o estado inteiro."""

    cod_regiao: str | None
    nome_regiao: str | None
    cod_municipio: str
    nome_municipio: str
    ano: int


def opcoes_municipios(municipios: pd.DataFrame, cod_regiao: str | None) -> list[str]:
    """Códigos dos municípios da região (todos, sem região), em ordem alfabética do nome."""
    recorte = municipios if cod_regiao is None else municipios[
        municipios["cod_regiao_intermediaria"] == cod_regiao]
    return recorte.sort_values(["nome_municipio", "cod_municipio"])["cod_municipio"].tolist()


def indice_padrao(opcoes: list[str], padrao: str = MUNICIPIO_PADRAO) -> int:
    """Florianópolis, se estiver na lista; senão, o primeiro."""
    return opcoes.index(padrao) if padrao in opcoes else 0


def barra_lateral(municipios: pd.DataFrame) -> Filtros:
    """Monta os três filtros na barra lateral e guarda a seleção em st.session_state."""
    regioes = (municipios[["cod_regiao_intermediaria", "nome_regiao_intermediaria"]]
               .drop_duplicates().sort_values("nome_regiao_intermediaria"))
    nomes_regiao = dict(zip(regioes["cod_regiao_intermediaria"], regioes["nome_regiao_intermediaria"]))
    nomes_municipio = dict(zip(municipios["cod_municipio"], municipios["nome_municipio"]))

    st.sidebar.header("Filtros")
    cod_regiao = st.sidebar.selectbox(
        "Região intermediária", [None, *nomes_regiao], key=CHAVE_REGIAO,
        format_func=lambda c: TODAS if c is None else nomes_regiao[c])
    opcoes = opcoes_municipios(municipios, cod_regiao)
    cod_municipio = st.sidebar.selectbox(
        "Município", opcoes, index=indice_padrao(opcoes), key=CHAVE_MUNICIPIO,
        format_func=lambda c: nomes_municipio[c])
    ano = st.sidebar.selectbox("Ano", ANOS, index=ANOS.index(ANO_PADRAO), key=CHAVE_ANO)
    st.sidebar.caption("O ano vale para PIB, PIB per capita e estimativa de população. "
                       "Os visuais de Censo mostram sempre 2010 e 2022.")
    filtros = Filtros(cod_regiao, None if cod_regiao is None else nomes_regiao[cod_regiao],
                      cod_municipio, nomes_municipio[cod_municipio], int(ano))
    st.session_state[CHAVE_FILTROS] = filtros
    return filtros


def atuais() -> Filtros:
    """Filtros montados pelo app.py nesta execução."""
    filtros = st.session_state.get(CHAVE_FILTROS)
    if filtros is None:
        raise RuntimeError("Filtros não montados: abra o app por dashboards/streamlit/app.py.")
    return filtros
