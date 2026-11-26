"""Gráficos plotly do app: padrão dos notebooks (título, unidade, fonte, paleta) e regras 5 e 12."""

import pandas as pd
import pytest

from brasil_em_dados.analise.graficos import CORES_BASES, PALETA
from brasil_em_dados.dashboard import figuras
from brasil_em_dados.dashboard import textos as t

FONTE = "IBGE (teste)"


def _rodape(fig) -> str:
    rodapes = [a.text for a in fig.layout.annotations if a.text.startswith("Fonte: ")]
    assert len(rodapes) == 1
    return rodapes[0]


@pytest.mark.parametrize(("minimo", "maximo", "zero"), [
    (0, 513_392_972_000, True), (-80, 215, True), (6_317_054, 7_338_473, False), (0.5, 0.5, False),
])
def test_ticks_cobrem_os_valores(minimo, maximo, zero):
    valores, textos = figuras.ticks(minimo, maximo, t.formatar_reais, incluir_zero=zero)
    assert valores[0] <= minimo and valores[-1] >= maximo
    assert len(valores) == len(textos)
    if zero:
        assert 0 in valores


def test_ticks_so_mudam_o_texto():
    valores, textos = figuras.ticks(0, 513_392_972_000, t.formatar_reais)
    assert valores[-1] >= 513_392_972_000  # o valor do tick continua em reais (regra 11)
    assert textos[-1].endswith("bi")


def test_barras_tem_titulo_unidade_fonte_e_paleta():
    fig = figuras.barras_horizontais(["A", "B"], [2.0, None], titulo="A lidera",
                                     rotulo_eixo="PIB nominal (R$)", fonte=FONTE,
                                     formatar=t.formatar_reais)
    assert fig.layout.title.text == "A lidera"
    assert fig.layout.xaxis.title.text == "PIB nominal (R$)"
    assert _rodape(fig) == f"Fonte: {FONTE}, elaboração própria."
    assert fig.layout.separators == ",."
    barra = fig.data[0]
    assert barra.x == (2.0, None)  # ausente vira lacuna, não zero (regra 5)
    assert barra.marker.color == PALETA["principal"]


def test_nota_entra_no_rodape():
    fig = figuras.colunas_anuais([2010], [1.0], titulo="x", rotulo_eixo="y", fonte=FONTE,
                                 formatar=str, nota="10 maiores")
    assert _rodape(fig).endswith("<br>10 maiores")


def test_referencia_desenha_a_mediana_com_o_rotulo():
    fig = figuras.barras_horizontais(["A"], [3.0], titulo="x", rotulo_eixo="y", fonte=FONTE,
                                     formatar=t.reais, referencia=(2.0, "Mediana entre os municípios"))
    textos = [a.text for a in fig.layout.annotations]
    assert any(texto.startswith("Mediana entre os municípios: R$ 2,00") for texto in textos)


def test_colunas_destacam_o_ano_do_filtro():
    fig = figuras.colunas_anuais([2022, 2023], [1.0, 2.0], titulo="x", rotulo_eixo="y",
                                 fonte=FONTE, formatar=str, ano_destaque=2023)
    assert list(fig.data[0].marker.color) == [PALETA["principal"], PALETA["contraste"]]


def test_estimativa_tem_uma_linha_por_base_e_marca_as_quebras():
    dados = pd.DataFrame({
        "ano": [2011, 2012, 2013, 2017, 2018],
        "valor": [1.0, 2.0, 3.0, 4.0, 5.0],
        "base_estimativa": ["ate_2012", "ate_2012", "2013_2017", "2013_2017", "desde_2018"],
    })
    fig = figuras.linhas_por_base(dados, titulo="x", rotulo_eixo="y", fonte=FONTE, formatar=str)
    assert [list(linha.x) for linha in fig.data] == [[2011, 2012], [2013, 2017], [2018]]
    assert [linha.line.color for linha in fig.data] == [CORES_BASES["ate_2012"],
                                                       CORES_BASES["2013_2017"],
                                                       CORES_BASES["desde_2018"]]
    quebras = {forma.x0 for forma in fig.layout.shapes}
    assert {2012.5, 2017.5} <= quebras
    textos = {a.text for a in fig.layout.annotations}
    assert {"2013: quebra de série: nova projeção", "2018: revisão da projeção"} <= textos


def test_estimativa_sem_base_e_recusada():
    dados = pd.DataFrame({"ano": [2011], "valor": [1.0], "base_estimativa": [None]})
    with pytest.raises(ValueError, match="regra 12"):
        figuras.linhas_por_base(dados, titulo="x", rotulo_eixo="y", fonte=FONTE, formatar=str)


def test_linhas_nao_ligam_lacunas():
    fig = figuras.linhas({"A": ([2010, 2011, 2012], [1.0, None, 3.0])}, titulo="x",
                         rotulo_eixo="y", fonte=FONTE, formatar=str)
    assert fig.data[0].connectgaps is False
    assert fig.data[0].y == (1.0, None, 3.0)


def test_cores_por_sinal_e_destaque():
    assert figuras.cores_por_sinal([1.0, -1.0, None]) == [PALETA["principal"], PALETA["contraste"],
                                                          PALETA["neutra"]]
    assert figuras.cores_destaque(["a", "b"], "b") == [PALETA["principal"], PALETA["contraste"]]


def _anotacoes(fig) -> list[str]:
    return [a.text for a in fig.layout.annotations]


def test_barra_ausente_mostra_sem_dado_e_nao_vira_zero():
    horizontal = figuras.barras_horizontais(["A", "B"], [2.0, None], titulo="x", rotulo_eixo="y",
                                            fonte=FONTE, formatar=t.reais)
    assert horizontal.data[0].x == (2.0, None)
    assert _anotacoes(horizontal).count("sem dado") == 1
    colunas = figuras.colunas_anuais([2010, 2022], [None, 5.0], titulo="x", rotulo_eixo="y",
                                     fonte=FONTE, formatar=t.reais)
    assert colunas.data[0].y == (None, 5.0)
    assert _anotacoes(colunas).count("sem dado") == 1


def test_divergentes_destacam_pelo_codigo_e_nao_pelo_nome():
    fig = figuras.barras_divergentes(["Mesmo nome", "Mesmo nome"], [1.0, -1.0], titulo="x",
                                     rotulo_eixo="y", fonte=FONTE, formatar=str,
                                     chaves=["1", "2"], destaque="2")
    assert list(fig.data[0].marker.color) == [PALETA["principal"], PALETA["terceira"]]
    with pytest.raises(ValueError, match="chave"):
        figuras.barras_divergentes(["A"], [1.0], titulo="x", rotulo_eixo="y", fonte=FONTE,
                                   formatar=str, destaque="A")


# -- figuras sem teste unitário até o D38 ---------------------------------------------------------

def _rodape(fig) -> str:
    return next(a.text for a in fig.layout.annotations if a.text.startswith("Fonte: "))


def test_halteres_liga_os_dois_pontos_e_nao_desenha_traco_com_ausencia():
    fig = figuras.halteres(["A", "B"], [6.5444, None], [9.3877, 3.0], nome_inicio="2010",
                           nome_fim="2023", titulo="T", rotulo_eixo="%", fonte="IBGE",
                           formatar=t.percentual)
    tracos = [d for d in fig.data if d.mode == "lines"]
    assert len(tracos) == 1 and list(tracos[0].y) == ["A", "A"]  # B não tem 2010: sem traço
    pontos = {d.name: d for d in fig.data if d.mode == "markers"}
    assert list(pontos["2010"].x) == [6.5444, None]  # ausência continua ausência, nunca zero
    assert list(pontos["2010"].text) == ["6,5%", ""]
    assert pontos["2023"].marker.color == PALETA["principal"]
    assert _rodape(fig).startswith("Fonte: IBGE")


@pytest.mark.parametrize("horizontal", [True, False])
def test_barras_agrupadas_uma_serie_por_cor_e_sem_dado_no_rotulo(horizontal):
    fig = figuras.barras_agrupadas(["Lages", "Caçador"], {"PIB": [3.57, None], "População": [4.8, 3.01]},
                                   titulo="T", rotulo_eixo="%", fonte="IBGE",
                                   formatar=t.percentual, horizontal=horizontal)
    assert [d.name for d in fig.data] == ["PIB", "População"]
    assert fig.data[0].marker.color != fig.data[1].marker.color
    assert list(fig.data[0].text) == ["3,6%", "sem dado"]
    valores = fig.data[0].x if horizontal else fig.data[0].y
    assert list(valores) == [3.57, None]
    assert fig.data[0].orientation == ("h" if horizontal else "v")
    assert fig.layout.barmode == "group"
