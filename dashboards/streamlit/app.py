"""App Streamlit do Brasil em Dados SC (D36): especificação em docs/dashboards.md.

Rodar da raiz do repositório:  streamlit run dashboards/streamlit/app.py

Este arquivo é o ponto de entrada: monta os filtros globais na barra lateral (assim eles persistem
entre as páginas), define a navegação e mostra a página inicial. Os dados vêm só das funções de
brasil_em_dados.analise (views gold, bed_readonly); nenhuma página tem SQL.
"""

import streamlit as st

from brasil_em_dados.dashboard import componentes as ui
from brasil_em_dados.dashboard import dados, filtros
from brasil_em_dados.dashboard import textos as t

st.set_page_config(page_title="Brasil em Dados SC", page_icon="📊", layout="wide")


def inicio() -> None:
    """Página inicial: pergunta central, como navegar e regras de leitura."""
    fontes = dados.fontes_series()
    inicio_serie, fim_serie = int(fontes["ano_inicial"].min()), int(fontes["ano_final"].max())
    st.title("Brasil em Dados SC")
    st.markdown(f"População e PIB dos {t.inteiro(len(dados.municipios()))} municípios de Santa "
                f"Catarina, de {inicio_serie} a {fim_serie}, a partir de dados públicos do IBGE.")
    st.markdown("**Pergunta central:** *como os municípios de Santa Catarina se diferenciam em "
                "população e dimensão econômica, e como esses indicadores evoluíram entre "
                f"{inicio_serie} e {fim_serie}?*")
    st.markdown(
        "- **Visão geral:** o tamanho do estado, a concentração e o peso das regiões.\n"
        "- **População:** quem concentra moradores e como a população variou entre os Censos "
        "2010 e 2022.\n"
        "- **Economia:** PIB nominal, participação no PIB do estado e PIB per capita.\n"
        "- **Perfil do município:** um município de cada vez, escolhido na barra lateral.\n"
        "- **Comparação:** de 2 a 5 municípios lado a lado.\n"
        "- **Sobre os dados:** fontes, cobertura e regras de leitura.")
    st.markdown("**Como ler os números**")
    ui.avisos(t.AVISO_PIB_NOMINAL, t.AVISO_PER_CAPITA, t.AVISO_CENSO_OFICIAL, t.AVISO_QUEBRAS)
    ui.rodape()


PAGINAS = [
    st.Page(inicio, title="Início", icon="🏠", default=True),
    st.Page("paginas/visao_geral.py", title="Visão geral", icon="🗺️"),
    st.Page("paginas/populacao.py", title="População", icon="👥"),
    st.Page("paginas/economia.py", title="Economia", icon="💰"),
    st.Page("paginas/perfil.py", title="Perfil do município", icon="📍"),
    st.Page("paginas/comparacao.py", title="Comparação", icon="⚖️"),
    st.Page("paginas/sobre.py", title="Sobre os dados", icon="ℹ️"),
]

try:
    filtros.barra_lateral(dados.municipios())
    st.navigation(PAGINAS).run()
except dados.ErroDados:
    st.error(dados.MENSAGEM_ERRO)
    st.stop()
