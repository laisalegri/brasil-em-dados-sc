"""Textos do app: formatadores pt-BR (só texto, regra 11), 'sem dado' (regra 5) e títulos."""

import math

import pandas as pd
import pytest

from brasil_em_dados.dashboard import textos as t


@pytest.mark.parametrize(("funcao", "valor", "esperado"), [
    (t.inteiro, 7_610_361, "7.610.361"),
    (t.inteiro, -1_100, "−1.100"),
    (t.reais, 513_392_972_000.0, "R$ 513.392.972.000,00"),
    (t.reais, 218_625.97, "R$ 218.625,97"),
    (t.reais_abreviado, 513_392_972_000.0, "R$ 513,4 bi"),
    (t.habitantes_abreviado, 7_610_361, "7,61 mi"),
    (lambda v: t.percentual(v, 4), 8.0984, "8,0984%"),
    (t.percentual, 46.1, "46,1%"),
    (lambda v: t.variacao(v, 2), 27.53, "+27,53%"),
    (t.variacao, -17.0, "−17,0%"),
    (t.variacao, 0.0, "0,0%"),
    (t.pontos, 2.84, "+2,84 p.p."),
])
def test_formatadores(funcao, valor, esperado):
    assert funcao(valor) == esperado


@pytest.mark.parametrize("ausente", [None, math.nan, pd.NA, float("nan")])
@pytest.mark.parametrize("funcao", [t.inteiro, t.reais, t.reais_abreviado, t.percentual,
                                    t.variacao, t.pontos, t.habitantes_abreviado])
def test_ausencia_aparece_como_sem_dado_e_nunca_como_zero(funcao, ausente):
    assert funcao(ausente) == "sem dado"


def test_coluna_formata_cada_valor():
    serie = pd.Series([1_000.0, None])
    assert t.coluna(serie, t.inteiro).tolist() == ["1.000", "sem dado"]


def test_titulos_afirmam_o_achado_com_os_numeros():
    assert t.titulo_serie_pib("de Santa Catarina", 2010, 153_726_009_000, 2023, 513_392_972_000) == (
        "PIB nominal de Santa Catarina: de R$ 153,7 bi (2010) para R$ 513,4 bi (2023), em valores "
        "correntes")
    assert t.titulo_lider("Joinville", 8.0984, "a população no Censo 2022") == (
        "Joinville lidera a população no Censo 2022, com 8,1% do estado")
    assert "13,5 vezes" in t.titulo_per_capita("Araquari", 218_625.97, "Pescaria Brava",
                                                16_142.0, 2023)
    assert t.titulo_participacao("Itajaí", 2010, 6.5444, 2023, 9.3877).startswith("Itajaí ganhou")
    assert t.posicao_texto(3, 295) == "3º de 295" and t.posicao_texto(None, 295) == "sem dado"


def test_titulos_de_pib_dizem_nominal_e_de_estimativa_nao_trazem_variacao():
    assert "nominal" in t.titulo_serie_pib("de X", 2010, 1.0, 2023, 2.0)
    assert "nominal" in t.titulo_saltos(61, 51)
    estimativa = t.titulo_estimativa("de SC", 2011, 6_317_054, 2021, 7_338_473)
    assert "%" not in estimativa and "três bases" in estimativa  # regra 12


def test_avisos_citam_as_regras():
    assert "regra 3" in t.AVISO_PIB_NOMINAL and "crescimento real" in t.AVISO_PIB_NOMINAL
    assert "regra 4" in t.AVISO_PER_CAPITA and "não é renda" in t.AVISO_PER_CAPITA
    assert "regra 12" in t.AVISO_QUEBRAS and "regra 13" in t.AVISO_DUPLA_CONTAGEM
    assert "regra 2" in t.AVISO_CENSO_OFICIAL and "A1" in t.AVISO_A1
    assert t.ROTULO_MEDIANA == "mediana entre os municípios"  # decisão D34


def test_territorio_com_preposicao_nao_gera_de_a_regiao():
    assert t.de_territorio(None) == "de Santa Catarina"
    assert t.de_territorio("Florianópolis") == "da região de Florianópolis"
    titulos = [
        t.titulo_serie_pib(t.de_territorio("Caçador"), 2010, 1.0, 2023, 2.0),
        t.titulo_variacao_censo(3, 16, t.de_territorio("Caçador")),
        t.titulo_estimativa(t.de_territorio("Caçador"), 2011, 1.0, 2021, 2.0),
        t.titulo_serie_pib(t.de_municipio("Laguna"), 2010, 1.0, 2023, 2.0),
    ]
    for titulo in titulos:
        assert "de a região" not in titulo and "de de" not in titulo
    assert "municípios da região de Caçador perderam" in titulos[1]


def test_rotulo_da_mediana_diz_de_onde_e_nunca_per_capita_do_territorio():
    assert t.rotulo_mediana(None) == "mediana entre os municípios"
    assert t.rotulo_mediana("Lages") == "mediana entre os municípios da região de Lages"
    for rotulo in (t.rotulo_mediana(None), t.rotulo_mediana("Lages")):
        assert "per capita" not in rotulo


def test_marcacoes_das_quebras_seguem_a_c8():
    assert t.QUEBRAS_ESTIMATIVA == {2013: "quebra de série: nova projeção",
                                    2018: "revisão da projeção"}
    assert "2017→2018" in t.AVISO_REVISAO_2018 and "regra 12" in t.AVISO_REVISAO_2018
