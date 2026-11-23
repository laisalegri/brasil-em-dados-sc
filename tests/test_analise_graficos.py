"""Testes dos gráficos da análise: padrão visual e nenhuma alteração dos valores (regra 11)."""

import pandas as pd
import pytest
from matplotlib.colors import to_hex

from brasil_em_dados.analise import graficos as g
from brasil_em_dados.analise.calculos import segmentos_por_base


def _textos_do_rodape(fig) -> str:
    return "\n".join(t.get_text() for t in fig.texts)


def _sem_escape(texto: str) -> str:
    return texto.replace("\\$", "$")


def _padrao(fig, titulo: str, unidade: str, fonte: str) -> None:
    ax = fig.axes[0]
    assert _sem_escape(ax.get_title(loc="left")) == titulo
    assert unidade in _sem_escape(ax.get_xlabel() + ax.get_ylabel())
    rodape = _sem_escape(_textos_do_rodape(fig))
    assert f"Fonte: {fonte}, elaboração própria." in rodape


def test_titulo_com_dois_cifroes_nao_vira_formula():
    titulo = "PIB foi de R$ 153,7 bi para R$ 513,4 bi"
    fig = g.serie_anual([2010, 2023], [1.537e11, 5.134e11], titulo=titulo,
                        rotulo_eixo="PIB nominal (R$ correntes)", fonte=g.FONTE_PIB,
                        formatar=g.formatar_reais)
    texto = fig.axes[0]._left_title  # título alinhado à esquerda
    assert texto._preprocess_math(texto.get_text()) == (titulo, False)
    for marca in fig.axes[0].texts:  # rótulos do primeiro e do último valor
        assert marca._preprocess_math(marca.get_text())[1] is False


@pytest.mark.parametrize("valor, esperado", [
    (513_393_000_000, "R$ 513,4 bi"), (820_500_000, "R$ 820,5 mi"), (52_591.2, "R$ 52.591"),
    (-1_500_000_000, "−R$ 1,5 bi"),
])
def test_formatar_reais(valor, esperado):
    assert g.formatar_reais(valor) == esperado


@pytest.mark.parametrize("valor, esperado", [
    (7_610_361, "7,61 mi"), (616_317, "616,3 mil"), (850, "850"), (-8_777, "−8,8 mil"),
])
def test_formatar_habitantes(valor, esperado):
    assert g.formatar_habitantes(valor) == esperado


def test_formatar_percentual():
    assert g.formatar_percentual(8.0984) == "8,1%"
    assert g.formatar_percentual(40.5848, 2) == "40,58%"


def test_barras_desenham_os_valores_sem_conversao():
    valores = [616317.0, 537211.0, 361261.0]
    fig = g.barras_horizontais(["A", "B", "C"], valores, titulo="T", rotulo_eixo="Habitantes",
                               fonte=g.FONTE_CENSO_2022, formatar=g.formatar_habitantes)
    larguras = [p.get_width() for p in fig.axes[0].patches]
    assert larguras == valores
    _padrao(fig, "T", "Habitantes", g.FONTE_CENSO_2022)
    assert {to_hex(p.get_facecolor()) for p in fig.axes[0].patches} == {g.PALETA["principal"]}


def test_barras_com_negativos_tem_linha_do_zero_e_cores_informadas():
    fig = g.barras_horizontais(["ganho", "perda"], [10.0, -5.0], titulo="T",
                               rotulo_eixo="Variação (habitantes)", fonte="IBGE",
                               formatar=g.formatar_habitantes,
                               cores=[g.PALETA["principal"], g.PALETA["contraste"]])
    ax = fig.axes[0]
    assert any(list(linha.get_xdata()) == [0, 0] for linha in ax.lines)
    assert [to_hex(p.get_facecolor()) for p in ax.patches] == [g.PALETA["principal"],
                                                               g.PALETA["contraste"]]


def test_histograma_marca_a_mediana():
    fig = g.histograma([1.0, 2.0, 3.0, 100.0, 3.0], titulo="T", rotulo_eixo="PIB per capita (R$)",
                       fonte=g.FONTE_PER_CAPITA, formatar=g.formatar_reais, nota="Não é renda.")
    _padrao(fig, "T", "R$", g.FONTE_PER_CAPITA)
    legenda = fig.axes[0].get_legend().get_texts()[0]
    assert legenda._preprocess_math(legenda.get_text()) == ("Mediana: R$ 3", False)
    assert "Não é renda." in _textos_do_rodape(fig)


def test_serie_da_estimativa_tem_uma_linha_por_base_e_quebras_marcadas():
    df = pd.DataFrame({
        "ano": list(range(2011, 2022)),
        "base_estimativa": ["ate_2012"] * 2 + ["2013_2017"] * 5 + ["desde_2018"] * 4,
        "valor": [float(v) for v in range(11)],
    })
    fig = g.serie_estimativa_por_base(segmentos_por_base(df), titulo="T",
                                      rotulo_eixo="População estimada (habitantes)",
                                      fonte=g.FONTE_ESTIMATIVA, formatar=g.formatar_habitantes)
    ax = fig.axes[0]
    linhas_de_dados = [l for l in ax.lines if l.get_marker() == "o"]
    assert [list(l.get_xdata()) for l in linhas_de_dados] == [
        [2011, 2012], [2013, 2014, 2015, 2016, 2017], [2018, 2019, 2020, 2021]]
    verticais = sorted(l.get_xdata()[0] for l in ax.lines if l.get_linestyle() == "--")
    assert verticais == [2012.5, 2017.5]
    assert [to_hex(l.get_color()) for l in linhas_de_dados] == [
        g.CORES_BASES["ate_2012"], g.CORES_BASES["2013_2017"], g.CORES_BASES["desde_2018"]]
    _padrao(fig, "T", "habitantes", g.FONTE_ESTIMATIVA)


def test_serie_anual_e_halteres_e_barras_pareadas_seguem_o_padrao():
    fig = g.serie_anual([2010, 2011], [1e9, 2e9], titulo="T1", rotulo_eixo="PIB nominal (R$ correntes)",
                        fonte=g.FONTE_PIB, formatar=g.formatar_reais)
    _padrao(fig, "T1", "R$ correntes", g.FONTE_PIB)
    assert list(fig.axes[0].lines[0].get_ydata()) == [1e9, 2e9]

    fig = g.comparacao_dois_anos(["A"], [5.0], [7.0], ano_inicio=2010, ano_fim=2023, titulo="T2",
                                 rotulo_eixo="Participação no PIB de SC (%)", fonte=g.FONTE_PIB,
                                 formatar=g.formatar_percentual)
    _padrao(fig, "T2", "(%)", g.FONTE_PIB)

    fig = g.barras_pareadas(["R"], [40.0], [30.0], nome_a="PIB", nome_b="População", titulo="T3",
                            rotulo_eixo="Participação em SC (%)", fonte=g.FONTE_PIB_E_CENSO,
                            formatar=g.formatar_percentual)
    _padrao(fig, "T3", "(%)", g.FONTE_PIB_E_CENSO)
    assert [p.get_width() for p in fig.axes[0].patches] == [40.0, 30.0]


def test_cores_por_sinal():
    assert g.cores_por_sinal([3.0, 0.0, -1.0]) == [g.PALETA["principal"], g.PALETA["principal"],
                                                   g.PALETA["contraste"]]


def test_percentual_negativo_usa_o_mesmo_sinal_de_menos():
    assert g.formatar_percentual(-17.02) == "−17,0%"


def test_rotulo_do_haltere_fica_do_lado_de_fora():
    fig = g.comparacao_dois_anos(["sobe", "cai"], [2.0, 9.0], [5.0, 6.0], ano_inicio=2010,
                                 ano_fim=2023, titulo="T", rotulo_eixo="Participação (%)",
                                 fonte="IBGE", formatar=g.formatar_percentual)
    sobe, cai = fig.axes[0].texts
    assert sobe.get_ha() == "left" and cai.get_ha() == "right"


def test_configurar_tabelas_usa_padrao_brasileiro():
    import pandas as pd
    anterior = pd.options.display.float_format
    try:
        g.configurar_tabelas()
        assert pd.options.display.float_format(153726000000.0) == "153.726.000.000,00"
    finally:
        pd.options.display.float_format = anterior
