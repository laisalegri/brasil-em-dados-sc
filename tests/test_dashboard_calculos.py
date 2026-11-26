"""Cálculos do app: recortes, totais lidos prontos (C1), participação regional e regra 12."""

import math

import pandas as pd
import pytest

from brasil_em_dados.dashboard import calculos as c

MUNICIPIOS = pd.DataFrame({
    "cod_municipio": ["1", "2", "3"],
    "cod_regiao_intermediaria": ["A", "A", "B"],
    "nome_regiao_intermediaria": ["Região A", "Região A", "Região B"],
})


def _agregado(linhas):
    return pd.DataFrame(linhas, columns=["cod_regiao", "nome_regiao", "ano", "valor"])


def test_recortar_regiao_junta_o_cadastro_quando_falta_a_regiao():
    df = pd.DataFrame({"cod_municipio": ["1", "2", "3"], "valor": [1.0, 2.0, 3.0]})
    assert c.recortar_regiao(df, "A", MUNICIPIOS)["valor"].tolist() == [1.0, 2.0]
    assert len(c.recortar_regiao(df, None)) == 3
    with pytest.raises(ValueError, match="cadastro"):
        c.recortar_regiao(df, "A")


def test_cadastro_com_municipio_repetido_e_recusado():
    df = pd.DataFrame({"cod_municipio": ["1"], "valor": [1.0]})
    with pytest.raises(ValueError, match="repetido"):
        c.com_regiao(df, pd.concat([MUNICIPIOS, MUNICIPIOS]))


def test_serie_territorio_le_o_total_pronto_sem_somar_municipios():
    estado = _agregado([("42", "SC", 2011, 10.0)])
    regioes = _agregado([("A", "Região A", 2011, 4.0), ("B", "Região B", 2011, 6.0)])
    assert c.serie_territorio(estado, regioes, None)["valor"].tolist() == [10.0]
    assert c.serie_territorio(estado, regioes, "B")["valor"].tolist() == [6.0]


def test_valor_no_ano():
    serie = pd.DataFrame({"ano": [2010, 2011], "valor": [1.0, 2.0]})
    assert c.valor_no_ano(serie, 2011) == 2.0
    assert c.valor_no_ano(serie, 2023) is None


def test_participacao_regional_usa_o_total_do_estado_do_mesmo_ano():
    estado = _agregado([("42", "SC", 2022, 200.0), ("42", "SC", 2010, 100.0)])
    regioes = _agregado([("A", "Região A", 2022, 50.0), ("B", "Região B", 2022, 150.0),
                         ("A", "Região A", 2010, 99.0)])
    resultado = c.participacao_regional(regioes, estado, 2022)
    assert resultado["participacao_percentual"].tolist() == [75.0, 25.0]


def test_participacao_regional_recusa_regiao_sem_valor():
    estado = _agregado([("42", "SC", 2022, 200.0)])
    regioes = _agregado([("A", "Região A", 2022, None)])
    with pytest.raises(ValueError, match="regra 5"):
        c.participacao_regional(regioes, estado, 2022)


def test_comparar_pib_populacao_so_compara_participacoes():
    pib_est = _agregado([("42", "SC", 2022, 100.0)])
    pop_est = _agregado([("42", "SC", 2022, 10.0)])
    pib_reg = _agregado([("A", "Região A", 2022, 60.0), ("B", "Região B", 2022, 40.0)])
    pop_reg = _agregado([("A", "Região A", 2022, 5.0), ("B", "Região B", 2022, 5.0)])
    tabela = c.comparar_pib_populacao(pib_reg, pib_est, pop_reg, pop_est, 2022)
    assert tabela["diferenca_pp"].tolist() == [10.0, -10.0]
    assert not any("per_capita" in coluna for coluna in tabela.columns)  # regra 4


def test_variacao_censo_territorios_poe_o_estado_primeiro():
    estado = _agregado([("42", "SC", 2010, 100.0), ("42", "SC", 2022, 120.0)])
    regioes = _agregado([("A", "Região A", 2010, 40.0), ("A", "Região A", 2022, 60.0),
                         ("B", "Região B", 2010, 60.0), ("B", "Região B", 2022, 60.0)])
    tabela = c.variacao_censo_territorios(regioes, estado)
    assert tabela["territorio"].tolist() == ["Santa Catarina", "Região A", "Região B"]
    assert tabela["variacao_percentual"].tolist() == [20.0, 50.0, 0.0]


def test_posicao_ignora_ausentes():
    df = pd.DataFrame({"cod_municipio": ["1", "2", "3"], "valor": [5.0, None, 9.0]})
    assert c.posicao(df, "3") == 1 and c.posicao(df, "1") == 2
    assert c.posicao(df, "2") is None


def test_mediana_ignora_ausentes():
    assert c.mediana(pd.Series([1.0, None, 3.0, 10.0])) == 3.0
    assert c.mediana(pd.Series([None, None], dtype="float64")) is None


def test_resumo_censo_e_ganhos_e_perdas():
    variacao = pd.DataFrame({
        "cod_municipio": ["1", "2", "3", "4"],
        "variacao_absoluta": [10.0, -5.0, 0.0, None],
        "variacao_percentual": [10.0, -5.0, 0.0, None],
    })
    assert c.resumo_censo(variacao) == {"comparaveis": 3, "cresceram": 1, "perderam": 1,
                                        "mediana": 0.0}
    extremos = c.ganhos_e_perdas(variacao, "variacao_percentual", n=1)
    assert extremos["cod_municipio"].tolist() == ["1", "2"]


def test_variacoes_entre_bases_conta_pares_e_comparaveis():
    variacao = pd.DataFrame({
        "ano": [2013, 2013, 2018, 2018, 2015],
        "variacao_percentual": [None, None, 1.0, 2.0, 1.0],
        "comparavel": [False, False, False, False, True],
        "motivo": ["quebra (regra 12)", "quebra (regra 12)", "revisão (regra 12)",
                   "revisão (regra 12)", None],
    })
    tabela = c.variacoes_entre_bases(variacao).set_index("pares")
    assert tabela.loc["2012→2013", ["municipios", "com_variacao", "comparaveis"]].tolist() == [2, 0, 0]
    assert tabela.loc["2017→2018", ["municipios", "com_variacao", "comparaveis"]].tolist() == [2, 2, 0]
    assert tabela.loc["2017→2018", "motivo"] == "revisão (regra 12)"


def test_saltos_pib_ordena_pelo_modulo():
    variacao = pd.DataFrame({"cod_municipio": ["1", "2", "3"],
                             "variacao_percentual": [60.0, -80.0, 10.0]})
    assert c.saltos_pib(variacao)["cod_municipio"].tolist() == ["2", "1"]


def test_participacao_2010_e_ano_deixa_sem_dado_quem_nao_existia_em_2010():
    serie = pd.DataFrame({
        "cod_municipio": ["1", "2", "1", "2"],
        "nome_municipio": ["Um", "Dois", "Um", "Dois"],
        "ano": [2010, 2010, 2023, 2023],
        "valor": [10.0, None, 30.0, 20.0],
        "participacao_percentual": [100.0, None, 60.0, 40.0],
    })
    tabela = c.participacao_2010_e_ano(serie, 2023)
    assert tabela["diferenca_pp"].iloc[0] == -40.0
    assert math.isnan(tabela["diferenca_pp"].iloc[1])
