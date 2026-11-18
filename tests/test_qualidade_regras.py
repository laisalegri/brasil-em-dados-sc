"""Testes sem banco das regras usadas em test_qualidade_dados.py (D22 + D26).

Conferem que as expectativas derivadas do catálogo e das regras de conteúdo continuam com o
tamanho esperado. Rodam na suíte rápida (sem o marcador integracao).
"""

from brasil_em_dados.extract import catalogo
from tests.test_qualidade_dados import (
    IND_PIB,
    IND_POP_CENSO,
    IND_POP_ESTIMADA,
    _divisores_de_conversao,
    _pares_coerencia_esperados,
)


def test_t10_cobre_pib_e_as_tres_series_de_populacao():
    series = {cod for cod, _ in _divisores_de_conversao()}
    esperadas = {s.cod_serie for s in catalogo.series()
                 if s.codigo_indicador in {IND_PIB, IND_POP_ESTIMADA, IND_POP_CENSO}}
    assert series == esperadas, f"séries do T10 {series} diferem das do catálogo {esperadas}"


def test_t11_numero_de_pares_esperado_e_o_do_relatorio():
    # Ancora a derivação: 12 anos × 295 − 4 (novos em 2011 e 2012) − 2 (Içara e Laguna 2012).
    assert _pares_coerencia_esperados() == 3534
