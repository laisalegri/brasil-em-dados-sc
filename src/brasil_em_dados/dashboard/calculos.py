"""Cálculos do app sobre DataFrames lidos da GOLD (sem Streamlit, sem I/O, sem conversão de unidade).

Totais vêm sempre de gold.agregado_regiao_ano (C1): nada aqui soma municípios para obter um total,
porque a soma de pop_estimada 2012 teria a dupla contagem da regra 13.
"""

import pandas as pd

from brasil_em_dados.analise.calculos import LIMITE_SALTO_PERCENTUAL, saltos_anuais

COLUNA_REGIAO = "cod_regiao_intermediaria"
ANOS_ENTRE_BASES = {2013: "2012→2013", 2018: "2017→2018"}  # regra 12


def com_regiao(df: pd.DataFrame, municipios: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta a região intermediária pelo código do município, se ainda não houver."""
    if COLUNA_REGIAO in df.columns:
        return df
    regioes = municipios[["cod_municipio", COLUNA_REGIAO, "nome_regiao_intermediaria"]]
    if regioes["cod_municipio"].duplicated().any():
        raise ValueError("Município repetido no cadastro: a junção duplicaria linhas.")
    return df.merge(regioes, on="cod_municipio", how="left", validate="many_to_one")


def recortar_regiao(df: pd.DataFrame, cod_regiao: str | None,
                    municipios: pd.DataFrame | None = None) -> pd.DataFrame:
    """Linhas dos municípios da região (todas, se cod_regiao for None)."""
    if cod_regiao is None:
        return df.reset_index(drop=True)
    if COLUNA_REGIAO not in df.columns:
        if municipios is None:
            raise ValueError("Sem a região no DataFrame: informe o cadastro de municípios.")
        df = com_regiao(df, municipios)
    return df[df[COLUNA_REGIAO] == cod_regiao].reset_index(drop=True)


def serie_territorio(estado: pd.DataFrame, regioes: pd.DataFrame,
                     cod_regiao: str | None) -> pd.DataFrame:
    """Série anual do estado ou de uma região intermediária, lida pronta de agregado_regiao_ano."""
    serie = estado if cod_regiao is None else regioes[regioes["cod_regiao"] == cod_regiao]
    return serie.sort_values("ano").reset_index(drop=True)


def valor_no_ano(serie: pd.DataFrame, ano: int, coluna: str = "valor") -> object:
    """Valor de `coluna` no ano (None se o ano não existir na série)."""
    linhas = serie.loc[serie["ano"] == ano, coluna]
    if len(linhas) > 1:
        raise ValueError(f"Ano {ano} repetido na série.")
    return None if linhas.empty else linhas.iloc[0]


def participacao_regional(regioes: pd.DataFrame, estado: pd.DataFrame, ano: int) -> pd.DataFrame:
    """Participação (%) de cada região no total do estado, no mesmo indicador e ano (C2)."""
    total = valor_no_ano(estado, ano)
    if total is None or pd.isna(total) or float(total) == 0:
        raise ValueError(f"Sem total estadual em {ano}.")
    recorte = regioes[regioes["ano"] == ano][["cod_regiao", "nome_regiao", "valor"]].copy()
    if recorte["valor"].isna().any():
        raise ValueError("Região sem valor: a participação não trata ausência como zero (regra 5).")
    recorte["participacao_percentual"] = recorte["valor"].astype(float) / float(total) * 100
    return recorte.sort_values("participacao_percentual", ascending=False).reset_index(drop=True)


def comparar_pib_populacao(pib_reg: pd.DataFrame, pib_est: pd.DataFrame, pop_reg: pd.DataFrame,
                           pop_est: pd.DataFrame, ano: int) -> pd.DataFrame:
    """VG4: participação de cada região no PIB e na população (Censo) do mesmo ano.

    Só compara as duas participações; nunca divide PIB por população (regra 4).
    """
    pib = participacao_regional(pib_reg, pib_est, ano)
    pop = participacao_regional(pop_reg, pop_est, ano)
    juntos = pib[["cod_regiao", "nome_regiao", "participacao_percentual"]].merge(
        pop[["cod_regiao", "participacao_percentual"]], on="cod_regiao",
        suffixes=("_pib", "_populacao"), validate="one_to_one")
    juntos["diferenca_pp"] = (juntos["participacao_percentual_pib"]
                              - juntos["participacao_percentual_populacao"])
    return juntos.sort_values("participacao_percentual_pib", ascending=False).reset_index(drop=True)


def variacao_censo_territorios(regioes: pd.DataFrame, estado: pd.DataFrame) -> pd.DataFrame:
    """POP3: Censo 2010, Censo 2022 e variação, com o estado na primeira linha."""
    linhas = []
    for nome, grupo in [("Santa Catarina", estado), *regioes.groupby("nome_regiao")]:
        inicio, fim = valor_no_ano(grupo, 2010), valor_no_ano(grupo, 2022)
        var = None
        if inicio is not None and fim is not None and not pd.isna(inicio) and float(inicio) != 0:
            var = (float(fim) - float(inicio)) / float(inicio) * 100
        linhas.append({"territorio": nome, "censo_2010": inicio, "censo_2022": fim,
                       "variacao_percentual": var})
    tabela = pd.DataFrame(linhas)
    regioes_ordenadas = tabela.iloc[1:].sort_values("variacao_percentual", ascending=False)
    return pd.concat([tabela.iloc[:1], regioes_ordenadas]).reset_index(drop=True)


def posicao(df: pd.DataFrame, cod_municipio: str, coluna: str = "valor") -> int | None:
    """Posição do município no ranking decrescente de `coluna` (1 = maior); None sem valor."""
    validos = df.dropna(subset=[coluna])
    if cod_municipio not in set(validos["cod_municipio"]):
        return None
    ordenado = validos.sort_values([coluna, "cod_municipio"], ascending=[False, True])
    return int(ordenado["cod_municipio"].tolist().index(cod_municipio)) + 1


def mediana(serie: pd.Series) -> float | None:
    """Mediana dos valores presentes (rótulo obrigatório: 'mediana entre os municípios')."""
    valores = serie.dropna().astype(float)
    return None if valores.empty else float(valores.median())


def resumo_censo(variacao: pd.DataFrame) -> dict[str, float | int | None]:
    """POP2: comparáveis, cresceram, perderam e mediana da variação percentual."""
    comparaveis = variacao.dropna(subset=["variacao_percentual"])
    return {
        "comparaveis": len(comparaveis),
        "cresceram": int((comparaveis["variacao_absoluta"] > 0).sum()),
        "perderam": int((comparaveis["variacao_absoluta"] < 0).sum()),
        "mediana": mediana(comparaveis["variacao_percentual"]),
    }


def ganhos_e_perdas(variacao: pd.DataFrame, coluna: str, n: int = 10) -> pd.DataFrame:
    """POP2: os n maiores ganhos e as n maiores perdas (sem repetir), do maior para o menor."""
    validos = variacao.dropna(subset=[coluna])
    ganhos = validos[validos[coluna] > 0].nlargest(n, coluna)
    perdas = validos[validos[coluna] < 0].nsmallest(n, coluna)
    juntos = pd.concat([ganhos, perdas]).drop_duplicates("cod_municipio")
    return juntos.sort_values(coluna, ascending=False).reset_index(drop=True)


def variacoes_entre_bases(variacao_estimada: pd.DataFrame) -> pd.DataFrame:
    """POP4: pares municipais de 2012→2013 e 2017→2018, com quantos têm variação (regra 12)."""
    linhas = []
    for ano, rotulo in ANOS_ENTRE_BASES.items():
        pares = variacao_estimada[variacao_estimada["ano"] == ano]
        motivos = pares["motivo"].dropna().unique()
        linhas.append({
            "pares": rotulo,
            "municipios": len(pares),
            "com_variacao": int(pares["variacao_percentual"].notna().sum()),
            "comparaveis": int(pares["comparavel"].fillna(False).astype(bool).sum()),
            "motivo": motivos[0] if len(motivos) == 1 else "; ".join(sorted(motivos)),
        })
    return pd.DataFrame(linhas)


def saltos_pib(variacao_pib: pd.DataFrame) -> pd.DataFrame:
    """ECO4: variações anuais do PIB nominal acima do limite do alerta A1, maior módulo primeiro."""
    saltos = saltos_anuais(variacao_pib, LIMITE_SALTO_PERCENTUAL)
    ordem = saltos["variacao_percentual"].astype(float).abs().sort_values(ascending=False).index
    return saltos.loc[ordem].reset_index(drop=True)


def participacao_2010_e_ano(serie: pd.DataFrame, ano: int, n: int = 10) -> pd.DataFrame:
    """ECO2: os n maiores do ano, com a participação em 2010 e no ano e a diferença em p.p."""
    fim = serie[serie["ano"] == ano].dropna(subset=["valor"]).nlargest(n, "valor")
    inicio = serie[serie["ano"] == 2010][["cod_municipio", "participacao_percentual"]]
    tabela = fim[["cod_municipio", "nome_municipio", "participacao_percentual"]].merge(
        inicio, on="cod_municipio", how="left", suffixes=("", "_2010"), validate="one_to_one")
    tabela["diferenca_pp"] = (tabela["participacao_percentual"].astype(float)
                              - tabela["participacao_percentual_2010"].astype(float))
    return tabela.reset_index(drop=True)
