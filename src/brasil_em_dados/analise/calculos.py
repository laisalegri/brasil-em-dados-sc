"""Cálculos da análise sobre DataFrames já lidos da GOLD (sem I/O, sem conversão de unidade)."""

from dataclasses import dataclass

import pandas as pd

LIMITE_SALTO_PERCENTUAL = 50.0  # mesmo corte da auditoria de qualidade (alerta A1)


@dataclass(frozen=True)
class Resumo:
    """Resumo de uma distribuição."""

    n: int
    minimo: float
    p25: float
    mediana: float
    p75: float
    maximo: float
    negativos: int


def top_n(df: pd.DataFrame, coluna: str, n: int = 10, maiores: bool = True) -> pd.DataFrame:
    """As n linhas com maior (ou menor) valor em `coluna`, ignorando nulos."""
    validos = df.dropna(subset=[coluna])
    ordenado = validos.sort_values(coluna, ascending=not maiores, kind="mergesort")
    return ordenado.head(n).reset_index(drop=True)


def participacao_acumulada(df: pd.DataFrame, n: int = 10) -> float:
    """Soma da participação (%) dos n maiores municípios."""
    return float(top_n(df, "participacao_percentual", n)["participacao_percentual"].sum())


def resumo(serie: pd.Series) -> Resumo:
    """Mínimo, quartis, máximo e quantidade de valores negativos (nulos ignorados)."""
    s = serie.dropna().astype(float)
    if s.empty:
        raise ValueError("Série sem valores para resumir.")
    return Resumo(int(s.size), float(s.min()), float(s.quantile(0.25)), float(s.median()),
                  float(s.quantile(0.75)), float(s.max()), int((s < 0).sum()))


def variacao_entre_anos(df: pd.DataFrame, ano_inicial: int, ano_final: int,
                        chave: str = "nome_regiao") -> pd.DataFrame:
    """Valor nos dois anos, variação absoluta e percentual por `chave` (ex.: região)."""
    recorte = df[df["ano"].isin([ano_inicial, ano_final])]
    # min_count=1: um grupo só com ausências soma NaN, nunca 0 (regra 5).
    tabela = recorte.groupby([chave, "ano"])["valor"].sum(min_count=1).unstack("ano")
    faltando = {ano_inicial, ano_final} - set(tabela.columns)
    if faltando:
        raise ValueError(f"Anos ausentes nos dados: {sorted(faltando)}")
    resultado = pd.DataFrame({
        "valor_inicial": tabela[ano_inicial],
        "valor_final": tabela[ano_final],
    })
    resultado["variacao_absoluta"] = resultado["valor_final"] - resultado["valor_inicial"]
    resultado["variacao_percentual"] = (
        resultado["variacao_absoluta"] / resultado["valor_inicial"].where(resultado["valor_inicial"] != 0)
        * 100)
    return resultado.sort_values("variacao_percentual", ascending=False).reset_index()


def participacao_no_total(df: pd.DataFrame, chave: str = "nome_regiao") -> pd.DataFrame:
    """Participação (%) de cada `chave` na soma de `valor` (um ano por vez)."""
    if df["ano"].nunique() != 1:
        raise ValueError("participacao_no_total espera um único ano.")
    if df["valor"].isna().any():
        raise ValueError("Há valor ausente: a participação no total não trata ausência como zero "
                         "(regra 5).")
    soma = df.groupby(chave, as_index=False)["valor"].sum()
    soma["participacao_percentual"] = soma["valor"] / soma["valor"].sum() * 100
    return soma.sort_values("participacao_percentual", ascending=False).reset_index(drop=True)


def segmentos_por_base(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    """Série estadual da estimativa separada por base (regra 12), na ordem dos anos.

    Cada base vira uma linha própria no gráfico: nunca se liga um ponto de uma base ao da outra.
    """
    if df["base_estimativa"].isna().any():
        raise ValueError("Toda linha da estimativa precisa de base_estimativa (regra 12).")
    ordenado = df.sort_values("ano")
    bases = list(dict.fromkeys(ordenado["base_estimativa"]))
    return [(b, ordenado[ordenado["base_estimativa"] == b].reset_index(drop=True)) for b in bases]


def saltos_anuais(df: pd.DataFrame, limite: float = LIMITE_SALTO_PERCENTUAL) -> pd.DataFrame:
    """Variações anuais com |variação %| acima do limite (municípios com saltos, alerta A1)."""
    validos = df.dropna(subset=["variacao_percentual"])
    return validos[validos["variacao_percentual"].abs() > limite].reset_index(drop=True)


def anexar(df: pd.DataFrame, outro: pd.DataFrame, colunas: list[str],
           chave: str = "cod_municipio", sufixo: str = "") -> pd.DataFrame:
    """Acrescenta `colunas` de `outro` a `df` pela chave (junção à esquerda, sem duplicar linhas)."""
    if outro[chave].duplicated().any():
        raise ValueError(f"Chave repetida em '{chave}': a junção duplicaria linhas.")
    renomear = {c: f"{c}{sufixo}" for c in colunas}
    return df.merge(outro[[chave, *colunas]].rename(columns=renomear), on=chave, how="left")


def quantos_somam(df: pd.DataFrame, percentual: float = 50.0) -> int:
    """Menor quantidade de municípios, dos maiores para os menores, que soma `percentual` do total."""
    ordenada = df["participacao_percentual"].dropna().sort_values(ascending=False)
    acumulada = ordenada.cumsum()
    atingiu = acumulada[acumulada >= percentual]
    if atingiu.empty:
        raise ValueError(f"As participações não chegam a {percentual}%.")
    return int(acumulada.index.get_loc(atingiu.index[0])) + 1


def extremos(df: pd.DataFrame, coluna: str, n: int = 10) -> pd.DataFrame:
    """Os n maiores e os n menores valores de `coluna`, do maior para o menor (sem repetir)."""
    maiores = top_n(df, coluna, n)
    menores = top_n(df, coluna, n, maiores=False)
    juntos = pd.concat([maiores, menores]).drop_duplicates()
    return juntos.sort_values(coluna, ascending=False, kind="mergesort").reset_index(drop=True)


def variacao_sequencial(df: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta a variação % de cada ano sobre o anterior (série com colunas ano e valor)."""
    ordenado = df.sort_values("ano").reset_index(drop=True)
    anos_seguidos = ordenado["ano"].diff() == 1
    variacao = ordenado["valor"].pct_change(fill_method=None) * 100
    return ordenado.assign(variacao_percentual=variacao.where(anos_seguidos))
