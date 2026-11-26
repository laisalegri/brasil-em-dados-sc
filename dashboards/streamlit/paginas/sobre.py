"""Sobre os dados (docs/dashboards.md, seção 4.6): fontes, cobertura e regras de leitura."""

import pandas as pd
import streamlit as st

from brasil_em_dados.dashboard import componentes as ui
from brasil_em_dados.dashboard import dados
from brasil_em_dados.dashboard import textos as t

ui.cabecalho("Sobre os dados", "De onde vêm os números e o que eles não dizem?")

# -- SOB1 -----------------------------------------------------------------------------------------
ui.visual("SOB1", "Fontes e séries")
fontes = dados.fontes_series()
st.dataframe(pd.DataFrame({
    "Série": fontes["cod_serie"],
    "Fonte": fontes["fonte"],
    "Indicador": fontes["codigo_indicador"],
    "Tipo de medida": fontes["tipo_medida"],
    "Unidade": fontes["unidade"],
    "Anos": fontes["ano_inicial"].astype(str) + "–" + fontes["ano_final"].astype(str),
    "Última coleta": pd.to_datetime(fontes["ultima_coleta"]).dt.strftime("%d/%m/%Y"),
}), hide_index=True)

# -- SOB2 -----------------------------------------------------------------------------------------
ui.visual("SOB2", "Cobertura")
cobertura = dados.cobertura()
st.dataframe(pd.DataFrame({
    "Indicador": cobertura["codigo_indicador"],
    "Status": cobertura["status"],
    "Linhas (município × ano)": t.coluna(cobertura["linhas"], t.inteiro),
}), hide_index=True)
st.caption(t.LEGENDA_COBERTURA)

# -- SOB3 -----------------------------------------------------------------------------------------
ui.visual("SOB3", "Regras de leitura")
regras = "\n".join(f"- **{titulo}** {texto}" for titulo, texto in t.REGRAS_DE_LEITURA)
st.markdown(f"{regras}\n\n{t.DETALHES_REGRAS}")

ui.rodape()
