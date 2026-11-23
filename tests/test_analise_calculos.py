"""Testes dos cálculos da análise exploratória (sem banco)."""

import math

import pandas as pd
import pytest

from brasil_em_dados.analise import calculos


def test_top_n_ignora_nulos_e_ordena():
    df = pd.DataFrame({"m": list("abcd"), "v": [3.0, None, 10.0, 5.0]})
    assert list(calculos.top_n(df, "v", 2)["m"]) == ["c", "d"]
    assert list(calculos.top_n(df, "v", 2, maiores=False)["m"]) == ["a", "d"]


def test_participacao_acumulada_soma_os_n_maiores():
    df = pd.DataFrame({"participacao_percentual": [50.0, 30.0, 15.0, 5.0, None]})
    assert calculos.participacao_acumulada(df, 2) == pytest.approx(80.0)


def test_resumo_da_distribuicao():
    r = calculos.resumo(pd.Series([-2.0, 0.0, 1.0, 3.0, None]))
    assert (r.n, r.minimo, r.maximo, r.negativos) == (4, -2.0, 3.0, 1)
    assert r.mediana == pytest.approx(0.5)


def test_resumo_sem_valores_falha():
    with pytest.raises(ValueError, match="sem valores"):
        calculos.resumo(pd.Series([None], dtype=float))


def test_variacao_entre_anos_por_regiao():
    df = pd.DataFrame({
        "nome_regiao": ["A", "A", "B", "B", "B"],
        "ano": [2010, 2022, 2010, 2022, 2015],
        "valor": [100.0, 150.0, 200.0, 180.0, 999.0],
    })
    r = calculos.variacao_entre_anos(df, 2010, 2022).set_index("nome_regiao")
    assert r.loc["A", "variacao_absoluta"] == 50 and r.loc["A", "variacao_percentual"] == 50
    assert r.loc["B", "variacao_percentual"] == pytest.approx(-10)
    assert list(r.index) == ["A", "B"]  # maior variação primeiro


def test_variacao_entre_anos_com_ano_ausente_falha():
    df = pd.DataFrame({"nome_regiao": ["A"], "ano": [2010], "valor": [1.0]})
    with pytest.raises(ValueError, match="Anos ausentes"):
        calculos.variacao_entre_anos(df, 2010, 2022)


def test_variacao_percentual_com_inicio_zero_fica_nula():
    df = pd.DataFrame({"nome_regiao": ["A", "A"], "ano": [2010, 2022], "valor": [0.0, 5.0]})
    assert math.isnan(calculos.variacao_entre_anos(df, 2010, 2022)["variacao_percentual"][0])


def test_participacao_no_total_soma_100_e_exige_um_ano():
    df = pd.DataFrame({"nome_regiao": ["A", "B"], "ano": [2022, 2022], "valor": [30.0, 70.0]})
    r = calculos.participacao_no_total(df)
    assert list(r["nome_regiao"]) == ["B", "A"]
    assert r["participacao_percentual"].sum() == pytest.approx(100)
    with pytest.raises(ValueError, match="único ano"):
        calculos.participacao_no_total(df.assign(ano=[2021, 2022]))


def test_segmentos_por_base_separa_sem_misturar_anos():
    df = pd.DataFrame({
        "ano": [2013, 2011, 2012, 2018, 2017],
        "base_estimativa": ["2013_2017", "ate_2012", "ate_2012", "desde_2018", "2013_2017"],
        "valor": [3.0, 1.0, 2.0, 5.0, 4.0],
    })
    segmentos = calculos.segmentos_por_base(df)
    assert [b for b, _ in segmentos] == ["ate_2012", "2013_2017", "desde_2018"]
    assert [list(d["ano"]) for _, d in segmentos] == [[2011, 2012], [2013, 2017], [2018]]


def test_segmentos_exigem_base_em_toda_linha():
    df = pd.DataFrame({"ano": [2011], "base_estimativa": [None], "valor": [1.0]})
    with pytest.raises(ValueError, match="regra 12"):
        calculos.segmentos_por_base(df)


def test_saltos_anuais_usa_o_modulo_da_variacao():
    df = pd.DataFrame({"variacao_percentual": [51.0, -60.0, 49.9, None, 10.0]})
    assert list(calculos.saltos_anuais(df)["variacao_percentual"]) == [51.0, -60.0]


def test_anexar_junta_sem_duplicar_e_com_sufixo():
    df = pd.DataFrame({"cod_municipio": ["1", "2"], "v": [10.0, 20.0]})
    outro = pd.DataFrame({"cod_municipio": ["1"], "pop_censo": [5.0]})
    r = calculos.anexar(df, outro, ["pop_censo"], sufixo="_2022")
    assert list(r.columns) == ["cod_municipio", "v", "pop_censo_2022"]
    assert r["pop_censo_2022"].isna().tolist() == [False, True]


def test_anexar_recusa_chave_repetida():
    outro = pd.DataFrame({"cod_municipio": ["1", "1"], "x": [1, 2]})
    with pytest.raises(ValueError, match="Chave repetida"):
        calculos.anexar(pd.DataFrame({"cod_municipio": ["1"]}), outro, ["x"])


def test_quantos_somam_metade():
    df = pd.DataFrame({"participacao_percentual": [10.0, 40.0, 30.0, 20.0]})
    assert calculos.quantos_somam(df) == 2   # 40 + 30 = 70 >= 50
    assert calculos.quantos_somam(df, 40.0) == 1
    with pytest.raises(ValueError, match="não chegam"):
        calculos.quantos_somam(df, 101.0)


def test_extremos_do_maior_para_o_menor_sem_repetir():
    df = pd.DataFrame({"m": list("abcde"), "v": [5.0, -3.0, 1.0, 9.0, -8.0]})
    assert list(calculos.extremos(df, "v", 2)["m"]) == ["d", "a", "b", "e"]
    assert list(calculos.extremos(df, "v", 3)["m"]) == ["d", "a", "c", "b", "e"]


def test_variacao_sequencial_so_entre_anos_seguidos():
    df = pd.DataFrame({"ano": [2012, 2010, 2011, 2014], "valor": [121.0, 100.0, 110.0, 130.0]})
    r = calculos.variacao_sequencial(df)
    assert list(r["ano"]) == [2010, 2011, 2012, 2014]
    assert r["variacao_percentual"].tolist()[1:3] == pytest.approx([10.0, 10.0])
    assert math.isnan(r["variacao_percentual"][0]) and math.isnan(r["variacao_percentual"][3])


def test_variacao_entre_anos_nao_transforma_ausencia_em_zero():
    df = pd.DataFrame({"nome_regiao": ["A", "A", "B", "B"], "ano": [2010, 2022, 2010, 2022],
                       "valor": [None, None, 10.0, 12.0]})
    r = calculos.variacao_entre_anos(df, 2010, 2022).set_index("nome_regiao")
    assert math.isnan(r.loc["A", "valor_inicial"]) and math.isnan(r.loc["A", "variacao_percentual"])


def test_participacao_no_total_recusa_valor_ausente():
    df = pd.DataFrame({"nome_regiao": ["A", "B"], "ano": [2022, 2022], "valor": [None, 70.0]})
    with pytest.raises(ValueError, match="regra 5"):
        calculos.participacao_no_total(df)
