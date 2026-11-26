"""População (docs/dashboards.md, seção 4.2): responde a P1 (população) e P2.

Censo e estimativa nunca na mesma série (regra 2). POP1 a POP3 usam só o Censo, com anos fixos, e
não respondem ao filtro de ano. POP4 é a estimativa, com uma linha por base (regra 12).
"""

import pandas as pd
import streamlit as st

from brasil_em_dados.analise import calculos as ca
from brasil_em_dados.dashboard import calculos as c
from brasil_em_dados.dashboard import componentes as ui
from brasil_em_dados.dashboard import dados, figuras, filtros
from brasil_em_dados.dashboard import textos as t

f = filtros.atuais()
de_territorio = t.de_territorio(f.nome_regiao)
cadastro = dados.municipios()
ui.cabecalho("População", "Quais municípios concentram a população e como ela variou entre os "
             "Censos de 2010 e 2022?")

# -- POP1 -----------------------------------------------------------------------------------------
ui.visual("POP1", "Quais municípios têm mais moradores?")
ano_censo = st.radio("Censo", t.ANOS_CENSO, index=1, horizontal=True, key="pop1_ano")
part = c.recortar_regiao(dados.participacao("pop_censo", ano_censo), f.cod_regiao, cadastro)
maiores = ca.top_n(part, "valor", 15)
onde = "" if f.cod_regiao is None else f" da região de {f.nome_regiao}"
ui.grafico(figuras.barras_horizontais(
    maiores["nome_municipio"].tolist(), maiores["valor"],
    titulo=t.titulo_lider(maiores["nome_municipio"][0], maiores["participacao_percentual"][0],
                          f"a população{onde} no Censo {ano_censo}"),
    rotulo_eixo=f"População (Censo {ano_censo}, pessoas)", fonte=t.FONTE_CENSOS,
    formatar=t.formatar_habitantes,
    cores=figuras.cores_destaque(maiores["cod_municipio"].tolist(), f.cod_municipio)))
sem_censo = part[part["valor"].isna()]
if not sem_censo.empty:
    st.caption(f"Sem Censo {ano_censo}: {', '.join(sem_censo['nome_municipio'])}. "
               f"{t.AVISO_NAO_INSTALADO}")
ui.tabela_dados("POP1", pd.DataFrame({
    "Posição": range(1, len(maiores) + 1),
    "Município": maiores["nome_municipio"],
    f"População (Censo {ano_censo})": t.coluna(maiores["valor"], t.inteiro),
    "Participação no estado": t.coluna(maiores["participacao_percentual"],
                                       lambda v: t.percentual(v, 4)),
}))

# -- POP2 -----------------------------------------------------------------------------------------
ui.visual("POP2", "Quem mais ganhou e perdeu população entre os Censos?")
variacao = c.recortar_regiao(dados.variacao_censo(), f.cod_regiao)
resumo = c.resumo_censo(variacao)
ui.metricas([
    ("Municípios comparáveis", t.inteiro(resumo["comparaveis"])),
    ("Cresceram", t.inteiro(resumo["cresceram"])),
    ("Perderam população", t.inteiro(resumo["perderam"])),
    ("Variação: mediana entre os municípios", t.variacao(resumo["mediana"], 1)),
])
medida = st.radio("Medida", ("Variação percentual", "Variação absoluta"), horizontal=True,
                  key="pop2_medida")
coluna = "variacao_percentual" if medida == "Variação percentual" else "variacao_absoluta"
extremos = c.ganhos_e_perdas(variacao, coluna)
ui.grafico(figuras.barras_divergentes(
    extremos["nome_municipio"].tolist(), extremos[coluna],
    titulo=t.titulo_variacao_censo(resumo["perderam"], resumo["comparaveis"], de_territorio),
    rotulo_eixo=("Variação entre os Censos 2010 e 2022 (%)" if coluna == "variacao_percentual"
                 else "Variação entre os Censos 2010 e 2022 (pessoas)"),
    fonte=t.FONTE_CENSOS,
    formatar=(lambda v: t.variacao(v, 1)) if coluna == "variacao_percentual"
    else t.formatar_habitantes,
    chaves=extremos["cod_municipio"].tolist(), destaque=f.cod_municipio))
sem_variacao = variacao[variacao["motivo"].notna()]
if not sem_variacao.empty:
    st.caption("Sem variação: " + "; ".join(
        f"{n} ({m})" for n, m in zip(sem_variacao["nome_municipio"], sem_variacao["motivo"])) + ".")
ui.avisos(t.AVISO_LAGUNA, t.AVISO_APURACOES)
ui.tabela_dados("POP2", pd.DataFrame({
    "Município": extremos["nome_municipio"],
    "Censo 2010": t.coluna(extremos["pop_censo_2010"], t.inteiro),
    "Censo 2022": t.coluna(extremos["pop_censo_2022"], t.inteiro),
    "Variação absoluta": t.coluna(extremos["variacao_absoluta"], t.inteiro),
    "Variação percentual": t.coluna(extremos["variacao_percentual"], lambda v: t.variacao(v, 2)),
}))

# -- POP3 -----------------------------------------------------------------------------------------
ui.visual("POP3", "Que regiões cresceram mais entre os Censos?")
territorios = c.variacao_censo_territorios(dados.agregado("regiao_intermediaria", "pop_censo"),
                                           dados.agregado("estado", "pop_censo"))
regioes = territorios.iloc[1:]
ui.grafico(figuras.barras_horizontais(
    regioes["territorio"].tolist(), regioes["variacao_percentual"],
    titulo=t.titulo_regioes_censo(regioes["territorio"].iloc[0],
                                  regioes["variacao_percentual"].iloc[0],
                                  regioes["territorio"].iloc[-1],
                                  regioes["variacao_percentual"].iloc[-1]),
    rotulo_eixo="Variação da população entre os Censos 2010 e 2022 (%)", fonte=t.FONTE_CENSOS,
    formatar=lambda v: t.variacao(v, 1),
    cores=figuras.cores_destaque(regioes["territorio"].tolist(), f.nome_regiao)))
ui.avisos(t.AVISO_CRICIUMA)
ui.tabela_dados("POP3", pd.DataFrame({
    "Território": territorios["territorio"],
    "Censo 2010": t.coluna(territorios["censo_2010"], t.inteiro),
    "Censo 2022": t.coluna(territorios["censo_2022"], t.inteiro),
    "Variação": t.coluna(territorios["variacao_percentual"], lambda v: t.variacao(v, 2)),
}))

# -- POP4 -----------------------------------------------------------------------------------------
ui.visual("POP4", "Como a estimativa anual de população evoluiu?")
estimativa = c.serie_territorio(dados.agregado("estado", "pop_estimada"),
                                dados.agregado("regiao_intermediaria", "pop_estimada"),
                                f.cod_regiao).dropna(subset=["valor"])
anos_estimativa = sorted(int(a) for a in estimativa["ano"])
if f.ano not in anos_estimativa:
    st.info(f"Sem estimativa publicada em {f.ano}: a tabela 6579 cobre {anos_estimativa[0]}–"
            f"{anos_estimativa[-1]}. O Censo não é usado no lugar (limitações, seção 4).")
inicio, fim = estimativa.iloc[0], estimativa.iloc[-1]
ui.grafico(figuras.linhas_por_base(
    estimativa[["ano", "valor", "base_estimativa"]],
    titulo=t.titulo_estimativa(de_territorio, int(inicio["ano"]), inicio["valor"], int(fim["ano"]),
                               fim["valor"]),
    rotulo_eixo="População estimada (pessoas)", fonte=t.FONTE_ESTIMATIVA,
    formatar=t.formatar_habitantes, ano_destaque=f.ano))
ui.avisos(t.AVISO_QUEBRAS, t.AVISO_DUPLA_CONTAGEM, t.AVISO_CENSO_OFICIAL)
ui.tabela_dados("POP4", pd.DataFrame({
    "Ano": estimativa["ano"],
    "Base da estimativa": estimativa["base_estimativa"],
    "População estimada": t.coluna(estimativa["valor"], t.inteiro),
    "Municípios somados": t.coluna(estimativa["municipios_somados"], t.inteiro),
    "Municípios excluídos": t.coluna(estimativa["municipios_excluidos"], t.inteiro),
    "Aviso": estimativa["aviso"].fillna(""),
}))
entre_bases = c.variacoes_entre_bases(
    c.recortar_regiao(dados.variacao_anual("pop_estimada"), f.cod_regiao, cadastro))
ui.avisos(t.AVISO_REVISAO_2018)
ui.tabela_dados("POP4 · variações entre bases", pd.DataFrame({
    "Variação": entre_bases["pares"],
    "Pares municipais": entre_bases["municipios"],
    "Com variação calculada": entre_bases["com_variacao"],
    "Comparáveis": entre_bases["comparaveis"],
    "Motivo": entre_bases["motivo"],
}))

ui.rodape()
