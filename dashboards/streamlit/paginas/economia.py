"""Economia (docs/dashboards.md, seção 4.3): responde a P1 (PIB), P3 e P4.

PIB sempre nominal (regra 3). PIB per capita é o publicado, sem agregação (regra 4): a única
estatística sobre ele é a mediana, sempre rotulada "mediana entre os municípios" (decisão D34).
"""

import pandas as pd
import streamlit as st

from brasil_em_dados.analise import calculos as ca
from brasil_em_dados.analise.graficos import PALETA
from brasil_em_dados.dashboard import calculos as c
from brasil_em_dados.dashboard import componentes as ui
from brasil_em_dados.dashboard import dados, figuras, filtros
from brasil_em_dados.dashboard import textos as t

f = filtros.atuais()
cadastro = dados.municipios()
onde = "" if f.cod_regiao is None else f" da região de {f.nome_regiao}"
ui.cabecalho("Economia", "Quais municípios concentram o PIB, como a participação deles mudou e "
             "como se comparam em PIB per capita?")

# -- ECO1 -----------------------------------------------------------------------------------------
ui.visual("ECO1", "Quais municípios concentram o PIB?")
part = c.recortar_regiao(dados.participacao("pib_corrente", f.ano), f.cod_regiao, cadastro)
maiores = ca.top_n(part, "valor", 15)
ui.grafico(figuras.barras_horizontais(
    maiores["nome_municipio"].tolist(), maiores["valor"],
    titulo=t.titulo_lider(maiores["nome_municipio"][0], maiores["participacao_percentual"][0],
                          f"o PIB nominal{onde} de {f.ano}"),
    rotulo_eixo=f"PIB nominal {f.ano} (R$, valores correntes)", fonte=t.FONTE_PIB,
    formatar=t.formatar_reais,
    cores=figuras.cores_destaque(maiores["cod_municipio"].tolist(), f.cod_municipio)))
ui.avisos(t.AVISO_PIB_NOMINAL, t.AVISO_DISTRIBUICAO)
ui.tabela_dados("ECO1", pd.DataFrame({
    "Posição": range(1, len(maiores) + 1),
    "Município": maiores["nome_municipio"],
    f"PIB nominal {f.ano} (R$)": t.coluna(maiores["valor"], t.reais),
    "Participação no estado": t.coluna(maiores["participacao_percentual"],
                                       lambda v: t.percentual(v, 4)),
}))

# -- ECO2 -----------------------------------------------------------------------------------------
ui.visual("ECO2", "Quem ganhou e perdeu participação no PIB desde 2010?")
if f.ano == 2010:
    st.info("Escolha na barra lateral um ano depois de 2010 para comparar com 2010.")
else:
    serie = c.recortar_regiao(dados.participacao_serie("pib_corrente"), f.cod_regiao, cadastro)
    halter = c.participacao_2010_e_ano(serie, f.ano)
    variaram = halter.dropna(subset=["diferenca_pp"])
    maior = variaram.loc[variaram["diferenca_pp"].idxmax()]
    ui.grafico(figuras.halteres(
        halter["nome_municipio"].tolist(), halter["participacao_percentual_2010"],
        halter["participacao_percentual"], nome_inicio="2010", nome_fim=str(f.ano),
        titulo=t.titulo_ganhos_participacao(int((variaram["diferenca_pp"] > 0).sum()),
                                            len(halter), maior["nome_municipio"],
                                            maior["diferenca_pp"], f.ano),
        rotulo_eixo="Participação no PIB nominal de SC (%)", fonte=t.FONTE_PIB,
        formatar=t.percentual))
    ui.avisos(t.AVISO_PARTICIPACAO, t.AVISO_PIB_NOMINAL)
    ui.tabela_dados("ECO2", pd.DataFrame({
        "Município": halter["nome_municipio"],
        "Participação 2010": t.coluna(halter["participacao_percentual_2010"],
                                      lambda v: t.percentual(v, 4)),
        f"Participação {f.ano}": t.coluna(halter["participacao_percentual"],
                                          lambda v: t.percentual(v, 4)),
        "Diferença": t.coluna(halter["diferenca_pp"], t.pontos),
    }))

# -- ECO3 -----------------------------------------------------------------------------------------
ui.visual("ECO3", "Como os municípios se comparam em PIB per capita?")
painel = c.recortar_regiao(dados.painel(f.ano), f.cod_regiao)
mediana = c.mediana(painel["pib_per_capita_reais"])
rotulo = t.rotulo_mediana(f.nome_regiao)  # decisão D34: nunca per capita do estado ou da região
com_valor = int(painel["pib_per_capita_reais"].notna().sum())
ui.metricas([(f"PIB per capita {f.ano}: {rotulo}", t.reais(mediana)),
             ("Municípios com valor", t.inteiro(com_valor))])
extremos = ca.extremos(painel, "pib_per_capita_reais", 10)
if not extremos.empty:
    # Maiores e menores por pertença (não pela posição): com até 20 municípios, aparecem todos.
    maiores = set(ca.top_n(painel, "pib_per_capita_reais", 10)["cod_municipio"])
    cores = [PALETA["contraste"] if cod == f.cod_municipio
             else PALETA["principal"] if cod in maiores else PALETA["neutra"]
             for cod in extremos["cod_municipio"]]
    nota = (f"Todos os {com_valor} municípios{onde} com valor; azul: os 10 maiores."
            if len(extremos) == com_valor else
            f"Azul: os 10 maiores; cinza: os 10 menores{onde}.")
    ui.grafico(figuras.barras_horizontais(
        extremos["nome_municipio"].tolist(), extremos["pib_per_capita_reais"],
        titulo=t.titulo_per_capita(extremos["nome_municipio"].iloc[0],
                                   extremos["pib_per_capita_reais"].iloc[0],
                                   extremos["nome_municipio"].iloc[-1],
                                   extremos["pib_per_capita_reais"].iloc[-1], f.ano),
        rotulo_eixo=f"PIB per capita {f.ano} (R$, publicado pelo IBGE)", fonte=t.FONTE_PER_CAPITA,
        formatar=t.formatar_reais, cores=cores, nota=nota,
        referencia=None if mediana is None else (mediana, rotulo[0].upper() + rotulo[1:])))
ui.avisos(t.AVISO_PER_CAPITA, t.AVISO_DENOMINADOR, t.AVISO_A1)
ui.tabela_dados("ECO3", pd.DataFrame({
    "Município": extremos["nome_municipio"],
    f"PIB per capita {f.ano} (R$)": t.coluna(extremos["pib_per_capita_reais"], t.reais),
}))

# -- ECO4 -----------------------------------------------------------------------------------------
ui.visual("ECO4", "Onde houve saltos anuais de PIB nominal acima de 50%?")
saltos = c.saltos_pib(c.recortar_regiao(dados.variacao_anual("pib_corrente"), f.cod_regiao,
                                        cadastro))
ui.metricas([("Variações acima de 50% em módulo", t.inteiro(len(saltos))),
             ("Municípios", t.inteiro(saltos["cod_municipio"].nunique()))])
st.markdown(f"**{t.titulo_saltos(len(saltos), saltos['cod_municipio'].nunique())}**")
destacar = saltos["cod_municipio"] == f.cod_municipio
st.dataframe(pd.DataFrame({
    "Município": saltos["nome_municipio"] + destacar.map({True: " ◀", False: ""}),
    "Anos": saltos["ano_anterior"].astype(str) + "→" + saltos["ano"].astype(str),
    "PIB nominal no ano anterior (R$)": t.coluna(saltos["valor_anterior"], t.reais),
    "PIB nominal no ano (R$)": t.coluna(saltos["valor"], t.reais),
    "Variação nominal": t.coluna(saltos["variacao_percentual"], lambda v: t.variacao(v, 2)),
}), hide_index=True)
ui.avisos(t.AVISO_A1, t.AVISO_PIB_NOMINAL)

ui.rodape()
