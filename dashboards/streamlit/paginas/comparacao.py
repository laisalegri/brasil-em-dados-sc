"""Comparação (docs/dashboards.md, seção 4.5): de 2 a 5 municípios, com seleção própria.

O filtro global Município não age aqui; o ano vale para CMP2 e CMP4 e é destacado nas séries.
"""

import pandas as pd
import streamlit as st

from brasil_em_dados.dashboard import componentes as ui
from brasil_em_dados.dashboard import dados, figuras, filtros
from brasil_em_dados.dashboard import textos as t

PADRAO = ("4209102", "4205407", "4208203")  # Joinville, Florianópolis, Itajaí

f = filtros.atuais()
cadastro = dados.municipios()
nomes = dict(zip(cadastro["cod_municipio"], cadastro["nome_municipio"]))
ui.cabecalho("Comparação", "Como de 2 a 5 municípios se comparam em PIB, PIB per capita e "
             "população?")
escolhidos = st.multiselect("Municípios (de 2 a 5)", list(nomes), default=list(PADRAO),
                            max_selections=5, format_func=nomes.get, key="cmp_municipios")
if len(escolhidos) < 2:
    st.warning("Escolha pelo menos 2 municípios para comparar.")
    st.stop()
ordem = {cod: i for i, cod in enumerate(escolhidos)}


def _recorte(df: pd.DataFrame) -> pd.DataFrame:
    """Linhas dos municípios escolhidos, na ordem da seleção."""
    linhas = df[df["cod_municipio"].isin(escolhidos)].copy()
    linhas["_ordem"] = linhas["cod_municipio"].map(ordem)
    return linhas.sort_values(["_ordem", *(["ano"] if "ano" in linhas else [])]).drop(
        columns="_ordem").reset_index(drop=True)


# -- CMP1 -----------------------------------------------------------------------------------------
ui.visual("CMP1", "Como evoluiu o peso de cada um no PIB do estado?")
medida = st.radio("Medida", ("Participação no PIB do estado", "PIB nominal (R$)"),
                  horizontal=True, key="cmp1_medida")
serie = _recorte(dados.participacao_serie("pib_corrente"))
em_reais = medida == "PIB nominal (R$)"
coluna = "valor" if em_reais else "participacao_percentual"
no_ano = serie[serie["ano"] == f.ano].dropna(subset=[coluna])
lider = no_ano.loc[no_ano[coluna].idxmax()] if not no_ano.empty else None
o_que = "o maior PIB nominal" if em_reais else "a maior participação no PIB nominal do estado"
ui.grafico(figuras.linhas(
    {nomes[cod]: (g["ano"], g[coluna]) for cod, g in serie.groupby("cod_municipio", sort=False)},
    titulo=(f"Em {f.ano}, {lider['nome_municipio']} tem {o_que} entre os escolhidos"
            if lider is not None else "PIB nominal dos municípios escolhidos"),
    rotulo_eixo="PIB nominal (R$, valores correntes)" if em_reais
    else "Participação no PIB nominal de SC (%)",
    fonte=t.FONTE_PIB, formatar=t.formatar_reais if em_reais else t.percentual,
    ano_destaque=f.ano))
ui.avisos(t.AVISO_PIB_NOMINAL if em_reais else t.AVISO_PARTICIPACAO)
ui.tabela_dados("CMP1", pd.DataFrame({
    "Município": serie["nome_municipio"],
    "Ano": serie["ano"],
    "Participação no PIB nominal do estado": t.coluna(serie["participacao_percentual"],
                                                      lambda v: t.percentual(v, 4)),
    "PIB nominal (R$)": t.coluna(serie["valor"], t.reais),
}))

# -- CMP2 -----------------------------------------------------------------------------------------
ui.visual("CMP2", "Como se comparam em PIB per capita?")
painel = _recorte(dados.painel(f.ano))
com_valor = painel.dropna(subset=["pib_per_capita_reais"])
titulo_cmp2 = "Sem PIB per capita publicado no ano para os escolhidos"
if not com_valor.empty:
    maior = com_valor.loc[com_valor["pib_per_capita_reais"].idxmax()]
    titulo_cmp2 = (f"Em {f.ano}, {maior['nome_municipio']} tem o maior PIB per capita entre os "
                   f"escolhidos ({t.reais_abreviado(maior['pib_per_capita_reais'])})")
ui.grafico(figuras.barras_horizontais(
    painel["nome_municipio"].tolist(), painel["pib_per_capita_reais"], titulo=titulo_cmp2,
    rotulo_eixo=f"PIB per capita {f.ano} (R$, publicado pelo IBGE)", fonte=t.FONTE_PER_CAPITA,
    formatar=t.formatar_reais))
ui.avisos(t.AVISO_PER_CAPITA, t.AVISO_DENOMINADOR)

# -- CMP3 -----------------------------------------------------------------------------------------
ui.visual("CMP3", "Como variou a população entre os Censos?")
censo = _recorte(dados.variacao_censo())
variaram = censo.dropna(subset=["variacao_percentual"])
titulo_cmp3 = "Censos 2010 e 2022 dos municípios escolhidos"
if not variaram.empty:
    maior = variaram.loc[variaram["variacao_percentual"].idxmax()]
    titulo_cmp3 = (f"Entre os Censos, {maior['nome_municipio']} teve a maior variação entre os "
                   f"escolhidos ({t.variacao(maior['variacao_percentual'], 1)})")
ui.grafico(figuras.barras_agrupadas(
    censo["nome_municipio"].tolist(),
    {"Censo 2010": censo["pop_censo_2010"], "Censo 2022": censo["pop_censo_2022"]},
    titulo=titulo_cmp3, rotulo_eixo="População (Censo, pessoas)", fonte=t.FONTE_CENSOS,
    formatar=t.formatar_habitantes))
for nome, motivo in zip(censo["nome_municipio"], censo["motivo"]):
    if not t.ausente(motivo):
        st.caption(f"{nome}: {motivo}.")
ui.tabela_dados("CMP3", pd.DataFrame({
    "Município": censo["nome_municipio"],
    "Censo 2010": t.coluna(censo["pop_censo_2010"], t.inteiro),
    "Censo 2022": t.coluna(censo["pop_censo_2022"], t.inteiro),
    "Variação": t.coluna(censo["variacao_percentual"], lambda v: t.variacao(v, 2)),
}))

# -- CMP4 -----------------------------------------------------------------------------------------
ui.visual("CMP4", f"Valores de {f.ano}")
anos_estimativa = sorted(int(a) for a in dados.agregado("estado", "pop_estimada")
                         .dropna(subset=["valor"])["ano"])
anos_censo = sorted(int(a) for a in dados.agregado("estado", "pop_censo")
                    .dropna(subset=["valor"])["ano"])
tem_estimativa, tem_censo = f.ano in anos_estimativa, f.ano in anos_censo
st.dataframe(pd.DataFrame({
    "Município": painel["nome_municipio"],
    f"População estimada {f.ano}": (t.coluna(painel["pop_estimada"], t.inteiro) if tem_estimativa
                                    else f"sem estimativa publicada em {f.ano}"),
    "Base da estimativa": painel["base_estimativa"].fillna("" if not tem_estimativa else t.SEM_DADO),
    f"População (Censo {f.ano})": (t.coluna(painel["pop_censo"], t.inteiro) if tem_censo
                                   else f"sem Censo em {f.ano}"),
    "PIB nominal (R$)": t.coluna(painel["pib_corrente_reais"], t.reais),
    "PIB per capita (R$)": t.coluna(painel["pib_per_capita_reais"], t.reais),
    "Aviso": painel["aviso"].fillna(""),
}), hide_index=True)
ui.avisos(f"Estimativa e Censo ficam em colunas separadas (regra 2); o Censo só existe em "
          f"{' e '.join(map(str, anos_censo))}, e a estimativa só em {anos_estimativa[0]}–"
          f"{anos_estimativa[-1]}.", t.AVISO_PIB_NOMINAL, t.AVISO_PER_CAPITA)

ui.rodape()
