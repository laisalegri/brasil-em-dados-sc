"""Testes da conversão de códigos de 6 para 7 dígitos (correspondência 1:1, D09)."""

import pytest

from brasil_em_dados.transform.codigos import mapear_codigos_6_para_7

CADASTRO = ["4205407", "4212650", "4220000"]


def test_mapeia_um_para_um():
    mapa = mapear_codigos_6_para_7(["420540", "421265", "422000"], CADASTRO)
    assert mapa == {"420540": "4205407", "421265": "4212650", "422000": "4220000"}


def test_codigo_sem_correspondente_falha():
    with pytest.raises(ValueError, match="sem correspondente"):
        mapear_codigos_6_para_7(["420540", "421265", "999999"], CADASTRO)


def test_municipio_do_cadastro_sem_codigo_falha():
    with pytest.raises(ValueError, match="sem código na resposta"):
        mapear_codigos_6_para_7(["420540", "421265"], CADASTRO)


def test_codigo_repetido_falha():
    with pytest.raises(ValueError, match="repetidos"):
        mapear_codigos_6_para_7(["420540", "420540", "421265", "422000"], CADASTRO)


def test_prefixo_com_dois_correspondentes_falha():
    with pytest.raises(ValueError, match="mais de um correspondente"):
        mapear_codigos_6_para_7(["420540"], ["4205407", "4205408"])
