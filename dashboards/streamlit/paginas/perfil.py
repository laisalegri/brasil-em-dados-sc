"""Perfil do município (docs/dashboards.md, seção 4.4): P1 a P4 para o município do filtro."""

import pandas as pd
import streamlit as st

from brasil_em_dados.dashboard import calculos as c
from brasil_em_dados.dashboard import componentes as ui
from brasil_em_dados.dashboard import dados, figuras, filtros
from brasil_em_dados.dashboard import textos as t

f = filtros.atuais()
cadastro = dados.municipios()
municipio = cadastro[cadastro["cod_municipio"] == f.cod_municipio].iloc[0]
serie = dados.painel_serie()
serie = serie[serie["cod_municipio"] == f.cod_municipio].sort_values("ano").reset_index(drop=True)
censo = dados.variacao_censo()
censo = censo[censo["cod_municipio"] == f.cod_municipio].iloc[0]
var_pib = dados.variacao_anual("pib_corrente")
var_pib = var_pib[var_pib["cod_municipio"] == f.cod_municipio]
instalado_depois = not t.ausente(municipio["ano_instalacao"])

ui.cabecalho(f"Perfil: {f.nome_municipio}",
             f"Qual o retrato de {f.nome_municipio} em população e PIB? (escolha o município "
             "na barra lateral)")
st.caption(f"Código IBGE {f.cod_municipio} · região intermediária de "
           f"{municipio['nome_regiao_intermediaria']} · região imediata de "
           f"{municipio['nome_regiao_imediata']}")
if instalado_depois:
    ui.avisos(t.AVISO_NAO_INSTALADO)

# -- PER1 -----------------------------------------------------------------------------------------
ui.visual("PER1", f"Qual o retrato de {f.nome_municipio}?")
part_pop = dados.participacao("pop_censo", 2022)
ui.metricas([
    ("População (Censo 2010)", t.inteiro(censo["pop_censo_2010"])),
    ("População (Censo 2022)", t.inteiro(censo["pop_censo_2022"])),
    ("Variação entre os Censos", t.variacao(censo["variacao_percentual"], 2)),
    ("Posição em população (Censo 2022)",
     t.posicao_texto(c.posicao(part_pop, f.cod_municipio), int(part_pop["valor"].notna().sum()))),
])
if not t.ausente(censo["motivo"]):
    st.caption(f"Variação entre os Censos: {censo['motivo']}.")
pib_ano = c.valor_no_ano(serie, f.ano, "pib_corrente_reais")
part_pib = dados.participacao("pib_corrente", f.ano)
ui.metricas([
    (f"PIB nominal {f.ano}", t.reais_abreviado(pib_ano)),
    (f"PIB per capita {f.ano}", t.reais(c.valor_no_ano(serie, f.ano, "pib_per_capita_reais"))),
    (f"Posição no PIB nominal {f.ano}",
     t.posicao_texto(c.posicao(part_pib, f.cod_municipio), int(part_pib["valor"].notna().sum()))),
])
st.caption(f"PIB nominal {f.ano}, valor exato: {t.reais(pib_ano)}.")
ui.avisos(t.AVISO_PIB_NOMINAL, t.AVISO_PER_CAPITA)

# -- PER2 -----------------------------------------------------------------------------------------
ui.visual("PER2", "Como o PIB nominal do município evoluiu?")
pib = serie.dropna(subset=["pib_corrente_reais"])
ui.grafico(figuras.colunas_anuais(
    pib["ano"], pib["pib_corrente_reais"],
    titulo=t.titulo_serie_pib(t.de_municipio(f.nome_municipio), int(pib["ano"].iloc[0]),
                              pib["pib_corrente_reais"].iloc[0], int(pib["ano"].iloc[-1]),
                              pib["pib_corrente_reais"].iloc[-1]),
    rotulo_eixo="PIB nominal (R$, valores correntes)", fonte=t.FONTE_PIB,
    formatar=t.formatar_reais, ano_destaque=f.ano))
saltos = c.saltos_pib(var_pib)
ui.avisos(t.AVISO_PIB_NOMINAL, t.AVISO_REVISAO_PIB)
if not saltos.empty:
    anos = ", ".join(f"{a}→{b} ({t.variacao(v, 1)})" for a, b, v in
                     zip(saltos["ano_anterior"], saltos["ano"], saltos["variacao_percentual"]))
    ui.avisos(f"Variações acima de 50% em módulo: {anos}. {t.AVISO_A1}")
tabela_pib = serie[["ano", "pib_corrente_reais"]].merge(
    var_pib[["ano", "variacao_percentual"]], on="ano", how="left", validate="one_to_one")
ui.tabela_dados("PER2", pd.DataFrame({
    "Ano": tabela_pib["ano"],
    "PIB nominal (R$)": t.coluna(tabela_pib["pib_corrente_reais"], t.reais),
    "Variação nominal sobre o ano anterior": t.coluna(tabela_pib["variacao_percentual"],
                                                      lambda v: t.variacao(v, 2)),
}))

# -- PER3 -----------------------------------------------------------------------------------------
ui.visual("PER3", "Como a população do município evoluiu?")
estimativa = (serie.dropna(subset=["pop_estimada"])
              .rename(columns={"pop_estimada": "valor"})[["ano", "valor", "base_estimativa"]])
coluna_a, coluna_b = st.columns(2)
with coluna_a:
    ui.grafico(figuras.linhas_por_base(
        estimativa,
        titulo=t.titulo_estimativa(t.de_municipio(f.nome_municipio), int(estimativa["ano"].iloc[0]),
                                   estimativa["valor"].iloc[0], int(estimativa["ano"].iloc[-1]),
                                   estimativa["valor"].iloc[-1]),
        rotulo_eixo="População estimada (pessoas)", fonte=t.FONTE_ESTIMATIVA,
        formatar=t.formatar_habitantes, ano_destaque=f.ano))
with coluna_b:
    ui.grafico(figuras.colunas_anuais(
        list(t.ANOS_CENSO), [censo["pop_censo_2010"], censo["pop_censo_2022"]],
        titulo=t.titulo_censos(f.nome_municipio, censo["pop_censo_2010"], censo["pop_censo_2022"]),
        rotulo_eixo="População (Censo, pessoas)", fonte=t.FONTE_CENSOS,
        formatar=t.formatar_habitantes))
ui.avisos(t.AVISO_QUEBRAS, t.AVISO_CENSO_OFICIAL)
var_est = dados.variacao_anual("pop_estimada")
quebra = var_est[(var_est["cod_municipio"] == f.cod_municipio) & (var_est["ano"] == 2013)]
if not quebra.empty and not t.ausente(quebra["motivo"].iloc[0]):
    st.caption(f"Variação 2012→2013: {quebra['motivo'].iloc[0]}.")
for aviso in serie["aviso"].dropna().unique():
    ui.avisos(f"2012: {aviso}. {t.AVISO_DUPLA_CONTAGEM}")
ui.tabela_dados("PER3", pd.DataFrame({
    "Ano": serie["ano"],
    "Estimativa": t.coluna(serie["pop_estimada"], t.inteiro),
    "Base da estimativa": serie["base_estimativa"].fillna(""),
    "Censo": t.coluna(serie["pop_censo"], t.inteiro),
}))

# -- PER4 -----------------------------------------------------------------------------------------
ui.visual("PER4", "Como o PIB per capita evoluiu?")
per_capita = serie.dropna(subset=["pib_per_capita_reais"])
ui.grafico(figuras.linhas(
    {f.nome_municipio: (per_capita["ano"], per_capita["pib_per_capita_reais"])},
    titulo=t.titulo_per_capita_municipio(
        f.nome_municipio, int(per_capita["ano"].iloc[0]), per_capita["pib_per_capita_reais"].iloc[0],
        int(per_capita["ano"].iloc[-1]), per_capita["pib_per_capita_reais"].iloc[-1]),
    rotulo_eixo="PIB per capita (R$, publicado pelo IBGE)", fonte=t.FONTE_PER_CAPITA,
    formatar=t.formatar_reais, ano_destaque=f.ano))
ui.avisos(t.AVISO_PER_CAPITA, t.AVISO_DENOMINADOR)
ui.tabela_dados("PER4", pd.DataFrame({
    "Ano": serie["ano"],
    "PIB per capita (R$)": t.coluna(serie["pib_per_capita_reais"], t.reais),
}))

# -- PER5 -----------------------------------------------------------------------------------------
ui.visual("PER5", "O município ganhou ou perdeu peso no PIB do estado?")
part = dados.participacao_serie("pib_corrente")
part = (part[part["cod_municipio"] == f.cod_municipio].dropna(subset=["participacao_percentual"])
        .sort_values("ano"))
inicio = part.iloc[0]
fim = part[part["ano"] == f.ano].iloc[0] if f.ano in set(part["ano"]) else part.iloc[-1]
ui.grafico(figuras.linhas(
    {f.nome_municipio: (part["ano"], part["participacao_percentual"])},
    titulo=t.titulo_participacao(f.nome_municipio, int(inicio["ano"]),
                                 inicio["participacao_percentual"], int(fim["ano"]),
                                 fim["participacao_percentual"]),
    rotulo_eixo="Participação no PIB nominal de SC (%)", fonte=t.FONTE_PIB, formatar=t.percentual,
    ano_destaque=f.ano))
if int(fim["ano"]) != f.ano:
    st.caption(f"Sem participação no PIB em {f.ano}; o título usa o último ano com valor "
               f"({int(fim['ano'])}).")
ui.avisos(t.AVISO_PARTICIPACAO)
ui.tabela_dados("PER5", pd.DataFrame({
    "Ano": part["ano"],
    "Participação no PIB nominal do estado": t.coluna(part["participacao_percentual"],
                                                      lambda v: t.percentual(v, 4)),
}))

ui.rodape()
