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
st.caption("com_valor: valor publicado; municipio_nao_instalado: ausência esperada de Pescaria "
           "Brava e Balneário Rincão antes de 2013 (regras 6 e 10); sem_dado: ausência não "
           "esperada, que faria os testes falharem.")

# -- SOB3 -----------------------------------------------------------------------------------------
ui.visual("SOB3", "Regras de leitura")
st.markdown(f"""
- **Censo e estimativa são medidas diferentes (regra 2).** Nunca aparecem na mesma série.
  {t.AVISO_CENSO_OFICIAL}
- **PIB é nominal (regra 3).** {t.AVISO_PIB_NOMINAL} {t.AVISO_REVISAO_PIB}
- **PIB per capita é o publicado (regra 4).** {t.AVISO_PER_CAPITA} Não há per capita de região ou
  do estado; a única estatística mostrada é a {t.ROTULO_MEDIANA}. {t.AVISO_DENOMINADOR}
- **Ausência não é zero (regra 5).** Valor ausente aparece como "{t.SEM_DADO}" e não é interpolado.
- **Estimativa em três bases (regra 12).** {t.AVISO_QUEBRAS}
- **Dupla contagem em 2012 (regra 13).** {t.AVISO_DUPLA_CONTAGEM}
- **Saltos do PIB em municípios pequenos.** {t.AVISO_A1}
- **PIB municipal é distribuição do PIB estadual.** {t.AVISO_DISTRIBUICAO}

Detalhes em `docs/limitacoes.md` e `docs/dashboards.md` no repositório.
""")

ui.rodape()
