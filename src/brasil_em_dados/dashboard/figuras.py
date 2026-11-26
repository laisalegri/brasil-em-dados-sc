"""Gráficos plotly do app, no padrão dos notebooks (brasil_em_dados.analise.graficos).

- título que afirma o achado (montado por quem chama, a partir dos dados);
- unidade no título do eixo de valores;
- rodapé "Fonte: IBGE (...), elaboração própria." e, se houver, uma nota;
- a mesma paleta (PALETA, CORES_BASES) e separadores do padrão brasileiro.

Regra 11: os valores entram como vêm da GOLD; só o texto dos rótulos e dos ticks é formatado.
"""

import math
from collections.abc import Callable, Mapping, Sequence

import pandas as pd
import plotly.graph_objects as go

from brasil_em_dados.analise.graficos import CORES_BASES, PALETA, ROTULOS_BASES, texto_fonte
from brasil_em_dados.dashboard.textos import QUEBRAS_ESTIMATIVA, SEM_DADO

Formatador = Callable[[float], str]
CORES_SERIES = (PALETA["principal"], PALETA["contraste"], PALETA["terceira"], "#7a5bd6", "#c2417f")
ALTURA = 460
PASSOS_TICK = (1, 2, 2.5, 5, 10)


def _floats(valores: Sequence[object]) -> list[float | None]:
    """Valores para o plotly: ausente vira None (lacuna no gráfico), nunca zero (regra 5)."""
    return [None if v is None or pd.isna(v) else float(v) for v in valores]


def ticks(minimo: float, maximo: float, formatar: Formatador, quantidade: int = 5,
          incluir_zero: bool = True) -> tuple[list[float], list[str]]:
    """Ticks 'redondos' que cobrem [mínimo, máximo], com o texto formatado (só o texto muda).

    Barras partem do zero (incluir_zero=True); linhas podem começar perto do menor valor.
    """
    if incluir_zero:
        minimo, maximo = min(minimo, 0.0), max(maximo, 0.0)
    amplitude = maximo - minimo
    if amplitude <= 0:
        return [float(minimo)], [formatar(float(minimo))]
    bruto = amplitude / quantidade
    potencia = 10 ** math.floor(math.log10(bruto))
    passo = next(p * potencia for p in PASSOS_TICK if p * potencia >= bruto)
    inicio = math.floor(minimo / passo) * passo
    valores, atual = [], inicio
    while True:
        valores.append(round(atual, 10))
        if atual >= maximo - passo * 1e-9:
            break
        atual += passo
    return valores, [formatar(v) for v in valores]


def _eixo_valores(fig: go.Figure, eixo: str, valores: Sequence[float | None], titulo: str,
                  formatar: Formatador, incluir_zero: bool = True) -> None:
    presentes = [v for v in valores if v is not None]
    if not presentes:
        return
    vals, textos = ticks(min(presentes), max(presentes), formatar, incluir_zero=incluir_zero)
    atualizar = fig.update_xaxes if eixo == "x" else fig.update_yaxes
    atualizar(title_text=titulo, tickvals=vals, ticktext=textos, gridcolor=PALETA["grade"],
              zerolinecolor=PALETA["neutra"], range=[vals[0], vals[-1]] if not incluir_zero and len(vals) > 1 else None)


def _finalizar(fig: go.Figure, titulo: str, fonte: str, nota: str | None,
               altura: int = ALTURA) -> go.Figure:
    """Título, rodapé de fonte, paleta e separadores pt-BR (',' decimal, '.' milhar)."""
    rodape = texto_fonte(fonte, nota).replace("\n", "<br>")
    linhas = rodape.count("<br>") + 1
    fig.update_layout(
        title={"text": titulo, "x": 0, "xanchor": "left", "font": {"size": 16}},
        height=altura + 18 * linhas,
        margin={"l": 10, "r": 20, "t": 70, "b": 60 + 18 * linhas},
        paper_bgcolor=PALETA["fundo"], plot_bgcolor=PALETA["fundo"],
        font={"color": PALETA["texto"]},
        separators=",.",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.0, "x": 0, "title_text": ""},
    )
    fig.add_annotation(text=rodape, xref="paper", yref="paper", x=0, y=0, xanchor="left",
                       yanchor="top", yshift=-45, showarrow=False, align="left",
                       font={"size": 11, "color": PALETA["texto_secundario"]})
    return fig


def _marcar_ausentes(fig: go.Figure, posicoes: Sequence[object], valores: Sequence[float | None],
                     horizontal: bool) -> None:
    """Escreve 'sem dado' onde falta valor (C4, regra 5): a barra não é desenhada, nem como zero."""
    for posicao, valor in zip(posicoes, valores):
        if valor is None:
            eixos = {"x": 0, "y": posicao, "xanchor": "left"} if horizontal else {
                "x": posicao, "y": 0, "yanchor": "bottom"}
            fig.add_annotation(text=SEM_DADO, showarrow=False,
                               font={"color": PALETA["texto_secundario"]}, **eixos)


def cores_destaque(chaves: Sequence[str], destaque: str | None, base: str = PALETA["principal"],
                   cor_destaque: str = PALETA["contraste"]) -> list[str]:
    """Uma cor por barra; a do item destacado (filtro Município) em contraste."""
    return [cor_destaque if c == destaque else base for c in chaves]


def cores_por_sinal(valores: Sequence[float | None]) -> list[str]:
    """Ganho em azul, perda em laranja, ausente em cinza."""
    return [PALETA["neutra"] if v is None else PALETA["principal"] if v >= 0 else PALETA["contraste"]
            for v in valores]


def barras_horizontais(rotulos: Sequence[str], valores: Sequence[object], *, titulo: str,
                       rotulo_eixo: str, fonte: str, formatar: Formatador,
                       cores: Sequence[str] | None = None, nota: str | None = None,
                       referencia: tuple[float, str] | None = None) -> go.Figure:
    """Ranking: maior em cima. `referencia` = (valor, rótulo) desenha uma linha vertical."""
    vals = _floats(valores)
    textos = ["" if v is None else formatar(v) for v in vals]
    fig = go.Figure(go.Bar(
        y=list(rotulos), x=vals, orientation="h", text=textos, textposition="outside",
        cliponaxis=False, marker_color=list(cores) if cores else PALETA["principal"],
        hovertemplate="%{y}: %{text}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    _marcar_ausentes(fig, list(rotulos), vals, horizontal=True)
    extremos = [v for v in vals if v is not None]
    if referencia is not None:
        extremos.append(referencia[0])
        fig.add_vline(x=referencia[0], line_dash="dash", line_color=PALETA["texto_secundario"],
                      annotation_text=f"{referencia[1]}: {formatar(referencia[0])}",
                      annotation_position="top")
    _eixo_valores(fig, "x", extremos, rotulo_eixo, formatar)
    return _finalizar(fig, titulo, fonte, nota, altura=max(ALTURA, 28 * len(vals) + 140))


def colunas_anuais(anos: Sequence[int], valores: Sequence[object], *, titulo: str,
                   rotulo_eixo: str, fonte: str, formatar: Formatador,
                   ano_destaque: int | None = None, nota: str | None = None) -> go.Figure:
    """Série anual em colunas; o ano do filtro em contraste."""
    vals = _floats(valores)
    anos = [int(a) for a in anos]
    fig = go.Figure(go.Bar(
        x=anos, y=vals, marker_color=cores_destaque([str(a) for a in anos],
                                                    None if ano_destaque is None else str(ano_destaque)),
        text=["" if v is None else formatar(v) for v in vals], textposition="outside",
        cliponaxis=False, hovertemplate="%{x}: %{text}<extra></extra>"))
    fig.update_xaxes(tickmode="array", tickvals=anos, title_text="Ano")
    _marcar_ausentes(fig, anos, vals, horizontal=False)
    _eixo_valores(fig, "y", vals, rotulo_eixo, formatar)
    return _finalizar(fig, titulo, fonte, nota)


def linhas_por_base(dados: pd.DataFrame, *, titulo: str, rotulo_eixo: str, fonte: str,
                    formatar: Formatador, ano_destaque: int | None = None,
                    nota: str | None = None) -> go.Figure:
    """Estimativa (regra 12): uma linha por base_estimativa, sem ligar bases, com as quebras.

    `dados` tem as colunas ano, valor e base_estimativa.
    """
    if dados["base_estimativa"].isna().any():
        raise ValueError("Toda linha da estimativa precisa de base_estimativa (regra 12).")
    fig = go.Figure()
    todos: list[float | None] = []
    for base in dict.fromkeys(dados.sort_values("ano")["base_estimativa"]):
        trecho = dados[dados["base_estimativa"] == base].sort_values("ano")
        vals = _floats(trecho["valor"].tolist())
        todos.extend(vals)
        fig.add_trace(go.Scatter(
            x=trecho["ano"].astype(int).tolist(), y=vals, mode="lines+markers",
            name=ROTULOS_BASES.get(base, base), line={"color": CORES_BASES.get(base)},
            text=[formatar(v) if v is not None else "" for v in vals],
            hovertemplate="%{x}: %{text}<extra>%{fullData.name}</extra>"))
    for ano, texto in QUEBRAS_ESTIMATIVA.items():
        fig.add_vline(x=ano - 0.5, line_dash="dot", line_color=PALETA["texto_secundario"],
                      annotation_text=f"{ano}: {texto}", annotation_position="top left")
    if ano_destaque is not None and ano_destaque in set(dados["ano"]):
        fig.add_vline(x=ano_destaque, line_color=PALETA["contraste"], line_width=1)
    fig.update_xaxes(tickmode="array", tickvals=sorted(int(a) for a in dados["ano"].unique()),
                     title_text="Ano")
    _eixo_valores(fig, "y", todos, rotulo_eixo, formatar, incluir_zero=False)
    return _finalizar(fig, titulo, fonte, nota)


def halteres(rotulos: Sequence[str], inicio: Sequence[object], fim: Sequence[object], *,
             nome_inicio: str, nome_fim: str, titulo: str, rotulo_eixo: str, fonte: str,
             formatar: Formatador, nota: str | None = None) -> go.Figure:
    """Dois pontos por item ligados por um traço (ex.: participação 2010 × ano)."""
    a, b = _floats(inicio), _floats(fim)
    fig = go.Figure()
    for rotulo, x0, x1 in zip(rotulos, a, b):
        if x0 is not None and x1 is not None:
            fig.add_trace(go.Scatter(x=[x0, x1], y=[rotulo, rotulo], mode="lines",
                                     line={"color": PALETA["grade"], "width": 4},
                                     showlegend=False, hoverinfo="skip"))
    for nome, vals, cor in ((nome_inicio, a, PALETA["neutra"]), (nome_fim, b, PALETA["principal"])):
        fig.add_trace(go.Scatter(x=vals, y=list(rotulos), mode="markers", name=nome,
                                 marker={"color": cor, "size": 12},
                                 text=["" if v is None else formatar(v) for v in vals],
                                 hovertemplate="%{y}: %{text}<extra>" + nome + "</extra>"))
    fig.update_yaxes(autorange="reversed")
    _eixo_valores(fig, "x", a + b, rotulo_eixo, formatar)
    return _finalizar(fig, titulo, fonte, nota, altura=max(ALTURA, 34 * len(rotulos) + 140))


def barras_agrupadas(categorias: Sequence[str], series: Mapping[str, Sequence[object]], *,
                     titulo: str, rotulo_eixo: str, fonte: str, formatar: Formatador,
                     horizontal: bool = True, nota: str | None = None) -> go.Figure:
    """Barras lado a lado, uma cor por série (ex.: PIB × população; Censo 2010 × 2022)."""
    fig = go.Figure()
    todos: list[float | None] = []
    for cor, (nome, valores) in zip(CORES_SERIES, series.items()):
        vals = _floats(valores)
        todos.extend(vals)
        textos = [SEM_DADO if v is None else formatar(v) for v in vals]
        eixos = {"y": list(categorias), "x": vals} if horizontal else {"x": list(categorias), "y": vals}
        fig.add_trace(go.Bar(name=nome, orientation="h" if horizontal else "v", marker_color=cor,
                             text=textos, textposition="outside", cliponaxis=False,
                             hovertemplate="%{text}<extra>" + nome + "</extra>", **eixos))
    fig.update_layout(barmode="group")
    if horizontal:
        fig.update_yaxes(autorange="reversed")
    _eixo_valores(fig, "x" if horizontal else "y", todos, rotulo_eixo, formatar)
    altura = max(ALTURA, 22 * len(categorias) * max(len(series), 1) + 140) if horizontal else ALTURA
    return _finalizar(fig, titulo, fonte, nota, altura=altura)


def barras_divergentes(rotulos: Sequence[str], valores: Sequence[object], *, titulo: str,
                       rotulo_eixo: str, fonte: str, formatar: Formatador,
                       chaves: Sequence[str] | None = None, destaque: str | None = None,
                       nota: str | None = None) -> go.Figure:
    """Ganhos e perdas em torno do zero (ex.: variação entre os Censos).

    O destaque compara `chaves` (códigos IBGE), nunca o nome (regra 1).
    """
    vals = _floats(valores)
    cores = cores_por_sinal(vals)
    if destaque is not None:
        if chaves is None or len(chaves) != len(rotulos):
            raise ValueError("Destaque exige uma chave (código) por barra.")
        cores = [PALETA["terceira"] if k == destaque else c for k, c in zip(chaves, cores)]
    return barras_horizontais(rotulos, vals, titulo=titulo, rotulo_eixo=rotulo_eixo, fonte=fonte,
                              formatar=formatar, cores=cores, nota=nota)


def linhas(series: Mapping[str, tuple[Sequence[int], Sequence[object]]], *, titulo: str,
           rotulo_eixo: str, fonte: str, formatar: Formatador, ano_destaque: int | None = None,
           nota: str | None = None) -> go.Figure:
    """Uma linha por série (ex.: um município por linha); ausência fica como lacuna."""
    fig = go.Figure()
    todos: list[float | None] = []
    anos_todos: set[int] = set()
    for cor, (nome, (anos, valores)) in zip(CORES_SERIES, series.items()):
        vals = _floats(valores)
        todos.extend(vals)
        anos_todos.update(int(a) for a in anos)
        fig.add_trace(go.Scatter(x=[int(a) for a in anos], y=vals, mode="lines+markers", name=nome,
                                 line={"color": cor}, connectgaps=False,
                                 text=["" if v is None else formatar(v) for v in vals],
                                 hovertemplate="%{x}: %{text}<extra>" + nome + "</extra>"))
    if ano_destaque is not None and ano_destaque in anos_todos:
        fig.add_vline(x=ano_destaque, line_color=PALETA["neutra"], line_width=1)
    fig.update_xaxes(tickmode="array", tickvals=sorted(anos_todos), title_text="Ano")
    _eixo_valores(fig, "y", todos, rotulo_eixo, formatar, incluir_zero=False)
    return _finalizar(fig, titulo, fonte, nota)
