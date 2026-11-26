"""Blocos de tela reaproveitados pelas páginas (Streamlit)."""

from collections.abc import Iterable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from brasil_em_dados.dashboard import textos


def cabecalho(titulo: str, pergunta: str) -> None:
    """Título da página e a pergunta que ela responde."""
    st.title(titulo)
    st.markdown(f"*{pergunta}*")


def visual(id_visual: str, pergunta: str) -> None:
    """Subtítulo de um visual: o código da especificação e a pergunta."""
    st.subheader(f"{id_visual} · {pergunta}")


def grafico(fig: go.Figure) -> None:
    """Mostra a figura plotly sem o logo do plotly na barra de ferramentas."""
    st.plotly_chart(fig, config={"displaylogo": False})


def avisos(*mensagens: str) -> None:
    """Avisos de leitura junto do visual (regras 2, 3, 4, 12 e 13; alerta A1)."""
    for mensagem in mensagens:
        st.caption(f"⚠️ {mensagem}")


def tabela_dados(id_visual: str, tabela: pd.DataFrame) -> None:
    """Tabela com os números do visual, já formatados, num expansor 'Dados — ID'."""
    with st.expander(f"Dados — {id_visual}"):
        st.dataframe(tabela, hide_index=True)


def metricas(itens: Iterable[tuple[str, str]], ajuda: dict[str, str] | None = None) -> None:
    """Cartões lado a lado: (rótulo, valor já formatado)."""
    itens = list(itens)
    for coluna, (rotulo, valor) in zip(st.columns(len(itens)), itens):
        coluna.metric(rotulo, valor, help=(ajuda or {}).get(rotulo))


def rodape() -> None:
    """Fonte no fim de cada página (C9)."""
    st.divider()
    st.caption(textos.RODAPE)
