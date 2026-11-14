"""Falhas do cliente HTTP (padrão de coleta, seção 7): 429, 5xx, timeout e Retry-After.

Sem rede: a sessão é um Mock e `dormir` é injetado, então nenhum teste espera de verdade.
"""

import logging
from unittest.mock import Mock

import pytest
import requests

from brasil_em_dados.extract.cliente_http import ESPERA_MAXIMA_S, baixar
from brasil_em_dados.extract.erros import ErroHTTP

URL = "https://exemplo.invalido/api"


def _resposta(status: int, conteudo: bytes = b"[]", headers: dict | None = None) -> Mock:
    resposta = Mock()
    resposta.status_code = status
    resposta.content = conteudo
    resposta.headers = headers or {}
    return resposta


def _sessao(*efeitos) -> Mock:
    sessao = Mock()
    sessao.get.side_effect = list(efeitos)
    return sessao


def _esperas(dormir: Mock) -> list[float]:
    return [chamada.args[0] for chamada in dormir.call_args_list]


# --- 429 persistente ------------------------------------------------------------------------

def test_429_persistente_esgota_3_tentativas_e_levanta_erro_com_status_429():
    sessao = _sessao(_resposta(429), _resposta(429), _resposta(429))
    dormir = Mock()
    with pytest.raises(ErroHTTP, match="HTTP 429 .* após 3 tentativas") as erro:
        baixar(URL, sessao, dormir=dormir)
    assert erro.value.status_http == 429
    assert sessao.get.call_count == 3
    assert _esperas(dormir) == [1.0, 2.0]  # não espera depois da última tentativa


def test_429_persistente_com_retry_after_espera_o_valor_do_servidor_em_cada_tentativa():
    respostas = [_resposta(429, headers={"Retry-After": "5"}) for _ in range(3)]
    dormir = Mock()
    with pytest.raises(ErroHTTP):
        baixar(URL, _sessao(*respostas), dormir=dormir)
    assert _esperas(dormir) == [5.0, 5.0]


def test_cada_tentativa_que_falha_gera_aviso_no_log(caplog):
    sessao = _sessao(_resposta(429), _resposta(429), _resposta(429))
    with caplog.at_level(logging.WARNING, logger="brasil_em_dados.extract.cliente_http"):
        with pytest.raises(ErroHTTP):
            baixar(URL, sessao, dormir=Mock())
    avisos = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(avisos) == 2
    assert "Tentativa 1/3 falhou (HTTP 429)" in avisos[0]


# --- mistura de 5xx e timeout ---------------------------------------------------------------

def test_mistura_503_timeout_502_esgota_e_falha_com_o_ultimo_status():
    sessao = _sessao(_resposta(503), requests.Timeout(), _resposta(502))
    dormir = Mock()
    with pytest.raises(ErroHTTP, match="HTTP 502 .* após 3 tentativas") as erro:
        baixar(URL, sessao, dormir=dormir)
    assert erro.value.status_http == 502
    assert sessao.get.call_count == 3
    assert _esperas(dormir) == [1.0, 2.0]


def test_mistura_que_termina_em_timeout_falha_sem_status_http():
    sessao = _sessao(_resposta(503), _resposta(500), requests.Timeout())
    with pytest.raises(ErroHTTP, match="timeout") as erro:
        baixar(URL, sessao, dormir=Mock())
    assert erro.value.status_http is None


def test_timeout_de_leitura_tambem_tenta_de_novo():
    sessao = _sessao(requests.ReadTimeout(), _resposta(200, b'[{"id": 4205407}]'))
    resposta = baixar(URL, sessao, dormir=Mock())
    assert resposta.tentativas == 2


def test_timeout_503_e_200_devolve_sucesso_com_3_tentativas():
    sessao = _sessao(requests.Timeout(), _resposta(503), _resposta(200, b'[{"id": 4205407}]'))
    dormir = Mock()
    resposta = baixar(URL, sessao, dormir=dormir)
    assert resposta.status_http == 200
    assert resposta.conteudo == b'[{"id": 4205407}]'
    assert resposta.tentativas == 3
    assert _esperas(dormir) == [1.0, 2.0]


def test_4xx_depois_de_5xx_falha_na_hora_sem_esgotar_tentativas():
    sessao = _sessao(_resposta(503), _resposta(404), _resposta(200))
    dormir = Mock()
    with pytest.raises(ErroHTTP, match="sem nova tentativa") as erro:
        baixar(URL, sessao, dormir=dormir)
    assert erro.value.status_http == 404
    assert sessao.get.call_count == 2
    assert _esperas(dormir) == [1.0]


def test_erro_de_conexao_depois_de_5xx_interrompe_as_tentativas():
    sessao = _sessao(_resposta(502), requests.ConnectionError("recusada"), _resposta(200))
    with pytest.raises(ErroHTTP, match="Falha de conexão"):
        baixar(URL, sessao, dormir=Mock())
    assert sessao.get.call_count == 2


def test_backoff_exponencial_tem_teto_de_60_segundos():
    sessao = _sessao(_resposta(500), _resposta(500), _resposta(500))
    dormir = Mock()
    with pytest.raises(ErroHTTP):
        baixar(URL, sessao, espera_base=100.0, dormir=dormir)
    assert _esperas(dormir) == [ESPERA_MAXIMA_S, ESPERA_MAXIMA_S]


# --- Retry-After em 5xx ---------------------------------------------------------------------

def test_retry_after_em_503_e_respeitado():
    sessao = _sessao(_resposta(503, headers={"Retry-After": "7"}), _resposta(200))
    dormir = Mock()
    baixar(URL, sessao, dormir=dormir)
    assert _esperas(dormir) == [7.0]


def test_retry_after_em_503_acima_do_teto_espera_60_segundos():
    sessao = _sessao(_resposta(503, headers={"Retry-After": "3600"}), _resposta(200))
    dormir = Mock()
    baixar(URL, sessao, dormir=dormir)
    assert _esperas(dormir) == [60.0]


@pytest.mark.parametrize("retry_after", [
    "Wed, 21 Oct 2026 07:28:00 GMT",  # formato data HTTP: o padrão só aceita segundos
    "-5",
    "",
    "cinco",
])
def test_retry_after_invalido_em_5xx_cai_no_backoff(retry_after):
    sessao = _sessao(_resposta(502, headers={"Retry-After": retry_after}), _resposta(200))
    dormir = Mock()
    baixar(URL, sessao, dormir=dormir)
    assert _esperas(dormir) == [1.0]


def test_retry_after_zero_tenta_de_novo_sem_esperar():
    sessao = _sessao(_resposta(503, headers={"Retry-After": "0"}), _resposta(200))
    dormir = Mock()
    resposta = baixar(URL, sessao, dormir=dormir)
    assert resposta.tentativas == 2
    assert _esperas(dormir) == [0.0]


def test_retry_after_de_uma_tentativa_nao_vale_para_o_timeout_seguinte():
    sessao = _sessao(_resposta(503, headers={"Retry-After": "7"}), requests.Timeout(),
                     _resposta(200))
    dormir = Mock()
    baixar(URL, sessao, dormir=dormir)
    assert _esperas(dormir) == [7.0, 2.0]


def test_status_2xx_diferente_de_200_e_devolvido_sem_nova_tentativa():
    # O cliente não reprova 204; quem reprova é a validação mínima (status_http = 200).
    sessao = _sessao(_resposta(204, b""))
    dormir = Mock()
    resposta = baixar(URL, sessao, dormir=dormir)
    assert resposta.status_http == 204
    assert sessao.get.call_count == 1
    dormir.assert_not_called()
