"""Visão geral (docs/dashboards.md, seção 4.1): responde à pergunta central em uma tela."""

import pandas as pd
import streamlit as st

from brasil_em_dados.analise import calculos as ca
from brasil_em_dados.dashboard import calculos as c
from brasil_em_dados.dashboard import componentes as ui
from brasil_em_dados.dashboard import dados, figuras, filtros
from brasil_em_dados.dashboard import textos as t

f = filtros.atuais()
de_territorio = t.de_territorio(f.nome_regiao)
ui.cabecalho("Visão geral", "Como os municípios de SC se diferenciam em população e dimensão "
             "econômica, e como esses indicadores evoluíram entre 2010 e 2023?")

pop_estado, pop_regioes = (dados.agregado("estado", "pop_censo"),
                           dados.agregado("regiao_intermediaria", "pop_censo"))
pib_estado, pib_regioes = (dados.agregado("estado", "pib_corrente"),
                           dados.agregado("regiao_intermediaria", "pib_corrente"))
serie_pop = c.serie_territorio(pop_estado, pop_regioes, f.cod_regiao)
serie_pib = c.serie_territorio(pib_estado, pib_regioes, f.cod_regiao)

# -- VG1 ------------------------------------------------------------------------------------------
ui.visual("VG1", f"Qual o tamanho {de_territorio}?")
pib_ano = c.valor_no_ano(serie_pib, f.ano)
municipios = c.recortar_regiao(dados.municipios(), f.cod_regiao)
ui.metricas([
    ("População (Censo 2022)", t.inteiro(c.valor_no_ano(serie_pop, 2022))),
    (f"PIB nominal {f.ano}", t.reais_abreviado(pib_ano)),
    ("Municípios", t.inteiro(len(municipios))),
])
st.caption(f"PIB nominal {f.ano}, valor exato: {t.reais(pib_ano)}.")
ui.avisos(t.AVISO_PIB_NOMINAL)

# -- VG2 ------------------------------------------------------------------------------------------
ui.visual("VG2", "Como o PIB nominal evoluiu de 2010 a 2023?")
primeiro, ultimo = serie_pib.iloc[0], serie_pib.iloc[-1]
ui.grafico(figuras.colunas_anuais(
    serie_pib["ano"], serie_pib["valor"],
    titulo=t.titulo_serie_pib(de_territorio, int(primeiro["ano"]), primeiro["valor"],
                              int(ultimo["ano"]), ultimo["valor"]),
    rotulo_eixo="PIB nominal (R$, valores correntes)", fonte=t.FONTE_PIB,
    formatar=t.formatar_reais, ano_destaque=f.ano))
ui.avisos(t.AVISO_PIB_NOMINAL, t.AVISO_REVISAO_PIB)
sequencia = ca.variacao_sequencial(serie_pib[["ano", "valor"]])
ui.tabela_dados("VG2", pd.DataFrame({
    "Ano": sequencia["ano"],
    "PIB nominal (R$)": t.coluna(sequencia["valor"], t.reais),
    "Variação nominal sobre o ano anterior": t.coluna(sequencia["variacao_percentual"],
                                                      lambda v: t.variacao(v, 2)),
}))

# -- VG3 ------------------------------------------------------------------------------------------
ui.visual("VG3", "Quanto os 10 maiores municípios concentram?")
part_pop = dados.participacao("pop_censo", 2022)
part_pib = dados.participacao("pib_corrente", f.ano)
conc_pop, conc_pib = ca.participacao_acumulada(part_pop), ca.participacao_acumulada(part_pib)
rotulos = ["População (Censo 2022)", f"PIB nominal ({f.ano})"]
ui.grafico(figuras.barras_horizontais(
    rotulos, [conc_pop, conc_pib], titulo=t.titulo_concentracao(conc_pop, conc_pib, f.ano),
    rotulo_eixo="Participação dos 10 maiores no total de SC (%)", fonte=t.FONTE_PARTICIPACAO,
    formatar=t.percentual))
metade_pop, metade_pib = ca.quantos_somam(part_pop), ca.quantos_somam(part_pib)
st.caption(f"Metade da população (Censo 2022) está em {metade_pop} municípios; metade do PIB "
           f"nominal de {f.ano}, em {metade_pib}. Concentração medida sempre no estado inteiro.")
ui.avisos(t.AVISO_DISTRIBUICAO)
ui.tabela_dados("VG3", pd.DataFrame({
    "Indicador": rotulos,
    "Participação dos 10 maiores": [t.percentual(conc_pop, 2), t.percentual(conc_pib, 2)],
    "Municípios que somam metade do total": [metade_pop, metade_pib],
}))

# -- VG4 ------------------------------------------------------------------------------------------
ui.visual("VG4", "Quais regiões pesam mais no PIB que na população?")
ano_vg4 = st.radio("Ano (Censo e PIB do mesmo ano)", t.ANOS_CENSO, index=1, horizontal=True,
                   key="vg4_ano")
regioes = c.comparar_pib_populacao(pib_regioes, pib_estado, pop_regioes, pop_estado, ano_vg4)
acima = int((regioes["diferenca_pp"] > 0).sum())
ui.grafico(figuras.barras_agrupadas(
    regioes["nome_regiao"].tolist(),
    {f"Participação no PIB nominal ({ano_vg4})": regioes["participacao_percentual_pib"],
     f"Participação na população (Censo {ano_vg4})": regioes["participacao_percentual_populacao"]},
    titulo=t.titulo_regioes_pib_pop(acima, len(regioes), ano_vg4),
    rotulo_eixo="Participação no total de SC (%)", fonte=t.FONTE_PARTICIPACAO,
    formatar=t.percentual))
ui.avisos(t.AVISO_SEM_PER_CAPITA_REGIONAL, t.AVISO_PIB_NOMINAL)
ui.tabela_dados("VG4", pd.DataFrame({
    "Região intermediária": regioes["nome_regiao"],
    f"Participação no PIB nominal {ano_vg4}": t.coluna(regioes["participacao_percentual_pib"],
                                                       lambda v: t.percentual(v, 2)),
    f"Participação na população, Censo {ano_vg4}": t.coluna(
        regioes["participacao_percentual_populacao"], lambda v: t.percentual(v, 2)),
    "Diferença": t.coluna(regioes["diferenca_pp"], t.pontos),
}))

ui.rodape()
