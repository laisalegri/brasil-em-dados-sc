"""Testes do cliente HTTP, sem rede: a sessão é simulada com unittest.mock."""

from unittest.mock import Mock

import pytest
import requests

from brasil_em_dados.extract import cliente_http
from brasil_em_dados.extract.cliente_http import baixar
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


def test_sucesso_na_primeira_tentativa():
    sessao = _sessao(_resposta(200, b'[{"a": 1}]'))
    dormir = Mock()
    resposta = baixar(URL, sessao, dormir=dormir)
    assert resposta.status_http == 200
    assert resposta.conteudo == b'[{"a": 1}]'
    assert resposta.tentativas == 1
    dormir.assert_not_called()


def test_usa_timeout_de_conexao_e_leitura():
    sessao = _sessao(_resposta(200))
    baixar(URL, sessao, dormir=Mock())
    sessao.get.assert_called_once_with(URL, timeout=(10, 60))


def test_sessao_criada_tem_user_agent_sem_dados_pessoais():
    sessao = cliente_http.criar_sessao()
    assert sessao.headers["User-Agent"] == "brasil-em-dados-sc/0.1 (projeto de portfolio)"
    sessao.close()


def test_5xx_tenta_de_novo_com_backoff():
    sessao = _sessao(_resposta(503), _resposta(200))
    dormir = Mock()
    resposta = baixar(URL, sessao, dormir=dormir)
    assert resposta.tentativas == 2
    dormir.assert_called_once_with(1.0)


def test_429_respeita_retry_after():
    sessao = _sessao(_resposta(429, headers={"Retry-After": "5"}), _resposta(200))
    dormir = Mock()
    baixar(URL, sessao, dormir=dormir)
    dormir.assert_called_once_with(5.0)


def test_retry_after_invalido_usa_backoff():
    sessao = _sessao(_resposta(429, headers={"Retry-After": "amanhã"}), _resposta(200))
    dormir = Mock()
    baixar(URL, sessao, dormir=dormir)
    dormir.assert_called_once_with(1.0)


def test_retry_after_tem_teto():
    assert cliente_http.calcular_espera(1, 1.0, "3600") == cliente_http.ESPERA_MAXIMA_S


def test_timeout_esgota_tentativas_e_falha():
    sessao = _sessao(requests.Timeout(), requests.Timeout(), requests.Timeout())
    dormir = Mock()
    with pytest.raises(ErroHTTP, match="após 3 tentativas"):
        baixar(URL, sessao, dormir=dormir)
    assert sessao.get.call_count == 3
    assert [c.args[0] for c in dormir.call_args_list] == [1.0, 2.0]


def test_5xx_persistente_falha_com_status():
    sessao = _sessao(_resposta(500), _resposta(502), _resposta(500))
    with pytest.raises(ErroHTTP) as erro:
        baixar(URL, sessao, dormir=Mock())
    assert erro.value.status_http == 500


def test_4xx_falha_sem_nova_tentativa():
    sessao = _sessao(_resposta(404))
    dormir = Mock()
    with pytest.raises(ErroHTTP) as erro:
        baixar(URL, sessao, dormir=dormir)
    assert erro.value.status_http == 404
    assert sessao.get.call_count == 1
    dormir.assert_not_called()


def test_max_tentativas_menor_que_um_falha():
    with pytest.raises(ValueError, match="max_tentativas"):
        baixar(URL, _sessao(), max_tentativas=0, dormir=Mock())


def test_erro_de_conexao_falha_sem_nova_tentativa():
    sessao = _sessao(requests.ConnectionError("recusada"))
    with pytest.raises(ErroHTTP, match="Falha de conexão"):
        baixar(URL, sessao, dormir=Mock())
    assert sessao.get.call_count == 1
