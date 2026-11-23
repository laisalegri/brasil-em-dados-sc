"""Gráficos da análise exploratória (matplotlib).

Padrão de todos os gráficos:
- título que afirma o achado (escrito por quem chama, no notebook);
- unidade no rótulo do eixo de valores;
- nota "Fonte: IBGE (...), elaboração própria." no rodapé;
- paleta fixa: os três primeiros tons da paleta categórica de referência (validados para
  daltonismo mesmo quando aparecem juntos) e um cinza neutro para contexto.

Regra 11: os valores são desenhados como vêm da GOLD (R$, habitantes, %). Os formatadores só
mudam o texto dos rótulos (ex.: 513393000000 aparece como "R$ 513,4 bi"); nunca alteram dados.
As figuras são criadas com matplotlib.figure.Figure (sem pyplot): no notebook, cada uma é exibida
uma vez, ao ser a última expressão da célula.
"""

from collections.abc import Callable, Sequence

import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator

PALETA = {
    "principal": "#2a78d6",         # azul (slot 1)
    "contraste": "#eb6834",         # laranja (slot 2)
    "terceira": "#1baf7a",          # água (slot 3)
    "neutra": "#a3a29d",            # contexto
    "texto": "#0b0b0b",
    "texto_secundario": "#52514e",
    "grade": "#e4e3df",
    "fundo": "#fcfcfb",
}
CORES_BASES = {  # regra 12: uma cor por base da estimativa
    "ate_2012": PALETA["neutra"],
    "2013_2017": PALETA["principal"],
    "desde_2018": PALETA["contraste"],
}
ROTULOS_BASES = {
    "ate_2012": "Base até 2012",
    "2013_2017": "Base 2013–2017 (nova projeção)",
    "desde_2018": "Base desde 2018 (revisão)",
}
QUEBRAS_ESTIMATIVA = {2013: "Quebra de nível (2013)", 2018: "Revisão da projeção (2018)"}

FONTE_CENSOS = "IBGE (Censos 2010 e 2022; SIDRA, tabelas 1378 e 4709)"
FONTE_CENSO_2022 = "IBGE (Censo 2022; SIDRA, tabela 4709)"
FONTE_ESTIMATIVA = "IBGE (Estimativas de população; SIDRA, tabela 6579)"
FONTE_PIB = "IBGE (PIB dos Municípios; SIDRA, tabela 5938)"
FONTE_PER_CAPITA = "IBGE (PIB per capita; API de Pesquisas, pesquisa 38, indicador 47001)"
FONTE_PIB_E_CENSO = "IBGE (PIB dos Municípios, SIDRA 5938; Censo 2022, SIDRA 4709)"

TAMANHO = (9.0, 5.4)
Formatador = Callable[[float], str]


# -- formatação de rótulos (só texto) -----------------------------------------------------------

def _numero_br(valor: float, casas: int) -> str:
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def formatar_reais(valor: float) -> str:
    """R$ com abreviação: 'R$ 513,4 bi', 'R$ 820,5 mi', 'R$ 52.591'."""
    sinal = "−" if valor < 0 else ""
    v = abs(valor)
    if v >= 1e9:
        return f"{sinal}R$ {_numero_br(v / 1e9, 1)} bi"
    if v >= 1e6:
        return f"{sinal}R$ {_numero_br(v / 1e6, 1)} mi"
    return f"{sinal}R$ {_numero_br(v, 0)}"


def formatar_habitantes(valor: float) -> str:
    """Habitantes com abreviação: '7,61 mi', '616,3 mil', '850'."""
    sinal = "−" if valor < 0 else ""
    v = abs(valor)
    if v >= 1e6:
        return f"{sinal}{_numero_br(v / 1e6, 2)} mi"
    if v >= 1e3:
        return f"{sinal}{_numero_br(v / 1e3, 1)} mil"
    return f"{sinal}{_numero_br(v, 0)}"


def formatar_percentual(valor: float, casas: int = 1) -> str:
    """'8,1%' e '−17,0%' (mesmo sinal de menos dos outros formatadores)."""
    sinal = "−" if valor < 0 else ""
    return f"{sinal}{_numero_br(abs(valor), casas)}%"


def configurar_tabelas() -> None:
    """Mostra os números das tabelas do pandas no padrão brasileiro, sem notação científica."""
    pd.options.display.float_format = lambda valor: _numero_br(valor, 2)


def texto_fonte(fonte: str, nota: str | None = None) -> str:
    """Rodapé padrão: fonte e, se houver, uma nota de leitura."""
    texto = f"Fonte: {fonte}, elaboração própria."
    return f"{texto}\n{nota}" if nota else texto


# -- base comum ----------------------------------------------------------------------------------

def _seguro(texto: str) -> str:
    """Escapa '$': no matplotlib, dois '$' num texto viram fórmula (ex.: 'de R$ 1 a R$ 2')."""
    return texto.replace("$", r"\$")


def _rotulador(formatar: Formatador) -> Formatador:
    return lambda valor: _seguro(formatar(valor))


def _eixo(formatar: Formatador) -> FuncFormatter:
    return FuncFormatter(lambda valor, _: _seguro(formatar(valor)))


def _nova_figura(altura: float | None = None) -> tuple[Figure, Axes]:
    fig = Figure(figsize=(TAMANHO[0], altura or TAMANHO[1]), facecolor=PALETA["fundo"],
                 layout="constrained")
    fig.get_layout_engine().set(rect=(0, 0.08, 1, 0.92))  # espaço do rodapé
    ax = fig.subplots()
    ax.set_facecolor(PALETA["fundo"])
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(PALETA["neutra"])
    ax.tick_params(colors=PALETA["texto_secundario"], labelsize=9)
    return fig, ax


def _finalizar(fig: Figure, ax: Axes, titulo: str, fonte: str, nota: str | None) -> Figure:
    ax.set_title(_seguro(titulo), loc="left", fontsize=12, fontweight="bold", color=PALETA["texto"],
                 pad=12)
    ax.xaxis.label.set_color(PALETA["texto_secundario"])
    ax.yaxis.label.set_color(PALETA["texto_secundario"])
    ax.set_xlabel(_seguro(ax.get_xlabel()))
    ax.set_ylabel(_seguro(ax.get_ylabel()))
    fig.text(0.01, 0.01, _seguro(texto_fonte(fonte, nota)), ha="left", va="bottom", fontsize=8,
             color=PALETA["texto_secundario"])
    return fig


def _grade(ax: Axes, eixo: str) -> None:
    ax.grid(axis=eixo, color=PALETA["grade"], linewidth=0.8)
    ax.set_axisbelow(True)


# -- gráficos ------------------------------------------------------------------------------------

def barras_horizontais(rotulos: Sequence[str], valores: Sequence[float], *, titulo: str,
                       rotulo_eixo: str, fonte: str, formatar: Formatador,
                       cores: Sequence[str] | None = None, nota: str | None = None) -> Figure:
    """Barras horizontais, maior em cima, com o valor escrito na ponta de cada barra."""
    fig, ax = _nova_figura(altura=max(4.0, 0.42 * len(rotulos) + 2.0))
    posicoes = list(range(len(rotulos)))[::-1]
    cores = list(cores) if cores is not None else [PALETA["principal"]] * len(rotulos)
    barras = ax.barh(posicoes, valores, color=cores, height=0.68, edgecolor=PALETA["fundo"],
                     linewidth=2)
    ax.set_yticks(posicoes, labels=[_seguro(r) for r in rotulos])
    ax.bar_label(barras, labels=[_rotulador(formatar)(v) for v in valores], padding=4, fontsize=8.5,
                 color=PALETA["texto"])
    ax.xaxis.set_major_formatter(_eixo(formatar))
    ax.set_xlabel(rotulo_eixo)
    if min(valores) < 0:
        ax.axvline(0, color=PALETA["texto_secundario"], linewidth=0.8)
    ax.margins(x=0.18)
    _grade(ax, "x")
    return _finalizar(fig, ax, titulo, fonte, nota)


def histograma(valores: Sequence[float], *, titulo: str, rotulo_eixo: str, fonte: str,
               formatar: Formatador, faixas: int = 30, referencia_zero: bool = False,
               nota: str | None = None) -> Figure:
    """Distribuição com a mediana marcada (e, se pedido, a linha do zero)."""
    serie = pd.Series(valores, dtype=float).dropna()
    fig, ax = _nova_figura()
    ax.hist(serie, bins=faixas, color=PALETA["principal"], edgecolor=PALETA["fundo"],
            linewidth=1.5)
    mediana = float(serie.median())
    ax.axvline(mediana, color=PALETA["contraste"], linewidth=2,
               label=_seguro(f"Mediana: {formatar(mediana)}"))
    if referencia_zero:
        ax.axvline(0, color=PALETA["texto_secundario"], linewidth=0.8, linestyle="--")
    ax.xaxis.set_major_locator(MaxNLocator(6))
    ax.xaxis.set_major_formatter(_eixo(formatar))
    ax.set_xlabel(rotulo_eixo)
    ax.set_ylabel("Municípios (quantidade)")
    ax.legend(frameon=False, fontsize=9)
    _grade(ax, "y")
    return _finalizar(fig, ax, titulo, fonte, nota)


def serie_estimativa_por_base(segmentos: Sequence[tuple[str, pd.DataFrame]], *, titulo: str,
                              rotulo_eixo: str, fonte: str, formatar: Formatador,
                              nota: str | None = None) -> Figure:
    """Estimativa anual com uma linha por base (regra 12) e as quebras marcadas.

    Pontos de bases diferentes nunca são ligados. Só estimativa: o Censo não entra nesta linha
    (regra 2).
    """
    fig, ax = _nova_figura()
    for base, dados in segmentos:
        ax.plot(dados["ano"], dados["valor"], color=CORES_BASES[base], linewidth=2, marker="o",
                markersize=6, label=_seguro(ROTULOS_BASES[base]))
    for ano, texto in QUEBRAS_ESTIMATIVA.items():
        ax.axvline(ano - 0.5, color=PALETA["texto_secundario"], linewidth=1, linestyle="--")
        ax.annotate(texto, xy=(ano - 0.5, 1), xycoords=("data", "axes fraction"),
                    xytext=(4, -4), textcoords="offset points", va="top", fontsize=8.5,
                    color=PALETA["texto_secundario"])
    ax.yaxis.set_major_formatter(_eixo(formatar))
    ax.set_ylabel(rotulo_eixo)
    ax.set_xlabel("Ano (estimativa de 1º de julho)")
    anos = sorted({int(a) for _, d in segmentos for a in d["ano"]})
    ax.set_xticks(anos)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    _grade(ax, "y")
    return _finalizar(fig, ax, titulo, fonte, nota)


def serie_anual(anos: Sequence[int], valores: Sequence[float], *, titulo: str, rotulo_eixo: str,
                fonte: str, formatar: Formatador, nota: str | None = None) -> Figure:
    """Série anual com o primeiro e o último valor escritos no gráfico."""
    fig, ax = _nova_figura()
    ax.plot(anos, valores, color=PALETA["principal"], linewidth=2, marker="o", markersize=6)
    for indice in (0, len(anos) - 1):
        ax.annotate(_seguro(formatar(valores[indice])), xy=(anos[indice], valores[indice]),
                    xytext=(0, 9), textcoords="offset points", ha="center", fontsize=9,
                    color=PALETA["texto"])
    ax.yaxis.set_major_formatter(_eixo(formatar))
    ax.set_ylabel(rotulo_eixo)
    ax.set_xlabel("Ano")
    ax.set_xticks(list(anos))
    ax.margins(y=0.12)
    _grade(ax, "y")
    return _finalizar(fig, ax, titulo, fonte, nota)


def comparacao_dois_anos(rotulos: Sequence[str], inicio: Sequence[float], fim: Sequence[float],
                         *, ano_inicio: int, ano_fim: int, titulo: str, rotulo_eixo: str,
                         fonte: str, formatar: Formatador, nota: str | None = None) -> Figure:
    """Halteres: um ponto por ano, ligados por um traço, um município por linha."""
    fig, ax = _nova_figura(altura=max(4.0, 0.42 * len(rotulos) + 2.0))
    posicoes = list(range(len(rotulos)))[::-1]
    for y, a, b in zip(posicoes, inicio, fim):
        ax.plot([a, b], [y, y], color=PALETA["neutra"], linewidth=2, zorder=1)
    ax.scatter(inicio, posicoes, s=64, color=PALETA["neutra"], zorder=2, label=str(ano_inicio),
               edgecolors=PALETA["fundo"], linewidths=2)
    ax.scatter(fim, posicoes, s=64, color=PALETA["principal"], zorder=3, label=str(ano_fim),
               edgecolors=PALETA["fundo"], linewidths=2)
    for y, a, b in zip(posicoes, inicio, fim):
        # O rótulo fica do lado de fora do traço: à direita se subiu, à esquerda se caiu.
        lado = 1 if b >= a else -1
        ax.annotate(_seguro(formatar(b)), xy=(b, y), xytext=(8 * lado, 0),
                    textcoords="offset points", va="center", ha="left" if lado > 0 else "right",
                    fontsize=8.5, color=PALETA["texto"])
    ax.set_yticks(posicoes, labels=[_seguro(r) for r in rotulos])
    ax.xaxis.set_major_formatter(_eixo(formatar))
    ax.set_xlabel(rotulo_eixo)
    ax.margins(x=0.12)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    _grade(ax, "x")
    return _finalizar(fig, ax, titulo, fonte, nota)


def barras_pareadas(rotulos: Sequence[str], serie_a: Sequence[float], serie_b: Sequence[float],
                    *, nome_a: str, nome_b: str, titulo: str, rotulo_eixo: str, fonte: str,
                    formatar: Formatador, nota: str | None = None) -> Figure:
    """Duas barras por categoria (mesma unidade e mesmo eixo), com legenda e valores."""
    fig, ax = _nova_figura(altura=max(4.0, 0.62 * len(rotulos) + 2.0))
    posicoes = list(range(len(rotulos)))[::-1]
    altura = 0.38
    barras_a = ax.barh([p + altura / 2 for p in posicoes], serie_a, height=altura,
                       color=PALETA["principal"], label=_seguro(nome_a), edgecolor=PALETA["fundo"],
                       linewidth=2)
    barras_b = ax.barh([p - altura / 2 for p in posicoes], serie_b, height=altura,
                       color=PALETA["contraste"], label=_seguro(nome_b), edgecolor=PALETA["fundo"],
                       linewidth=2)
    for barras, serie in ((barras_a, serie_a), (barras_b, serie_b)):
        ax.bar_label(barras, labels=[_rotulador(formatar)(v) for v in serie], padding=3, fontsize=8,
                     color=PALETA["texto"])
    ax.set_yticks(posicoes, labels=[_seguro(r) for r in rotulos])
    ax.xaxis.set_major_formatter(_eixo(formatar))
    ax.set_xlabel(rotulo_eixo)
    ax.margins(x=0.15)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    _grade(ax, "x")
    return _finalizar(fig, ax, titulo, fonte, nota)


def cores_por_sinal(valores: Sequence[float]) -> list[str]:
    """Azul para valores >= 0 e laranja para negativos (ganho × perda)."""
    return [PALETA["principal"] if v >= 0 else PALETA["contraste"] for v in valores]
