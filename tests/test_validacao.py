"""Testes da validação mínima das respostas."""

import json

import pytest

from brasil_em_dados.config import RAIZ_PROJETO
from brasil_em_dados.extract.erros import ErroValidacao
from brasil_em_dados.extract.validacao import validar_resposta

CABECALHO_SIDRA = {"NC": "Nível Territorial (Código)", "V": "Valor"}
LINHA_SIDRA = {"NC": "6", "V": "427298"}


def _bytes(dados) -> bytes:
    return json.dumps(dados).encode("utf-8")


def test_sidra_conta_linhas_sem_cabecalho():
    conteudo = _bytes([CABECALHO_SIDRA, LINHA_SIDRA, LINHA_SIDRA])
    assert validar_resposta(200, conteudo, "sidra") == 2


def test_sidra_so_com_cabecalho_falha():
    with pytest.raises(ErroValidacao, match="pelo menos uma linha"):
        validar_resposta(200, _bytes([CABECALHO_SIDRA]), "sidra")


def test_html_com_status_200_falha():
    html = b"<!DOCTYPE html><html><title>Just a moment...</title></html>"
    with pytest.raises(ErroValidacao, match="não é JSON"):
        validar_resposta(200, html, "sidra")


def test_status_diferente_de_200_falha():
    with pytest.raises(ErroValidacao, match="esperado 200"):
        validar_resposta(204, b"", "sidra")


def test_localidades_conta_municipios_da_fixture():
    conteudo = (RAIZ_PROJETO / "tests" / "fixtures" / "localidades_sc_amostra.json").read_bytes()
    assert validar_resposta(200, conteudo, "api_localidades") == 5


def test_localidades_vazia_falha():
    with pytest.raises(ErroValidacao):
        validar_resposta(200, b"[]", "api_localidades")


def test_pesquisas_conta_localidades():
    dados = [{"id": 47001, "res": [
        {"localidade": "420540", "res": {"2021": "50000.00"}},
        {"localidade": "421265", "res": {"2011": "-"}},
    ]}]
    assert validar_resposta(200, _bytes(dados), "api_pesquisas") == 2


def test_pesquisas_sem_resultados_falha():
    with pytest.raises(ErroValidacao, match="'res'"):
        validar_resposta(200, _bytes([{"id": 47001, "res": []}]), "api_pesquisas")


def test_fonte_desconhecida_falha():
    with pytest.raises(ErroValidacao, match="Fonte desconhecida"):
        validar_resposta(200, b"[1]", "outra")
