"""Testes da orquestração da coleta: sucesso grava RAW e controle; falha não grava RAW."""

import errno
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from itertools import count
from unittest.mock import patch

import pytest

from brasil_em_dados.extract import catalogo, raw
from brasil_em_dados.extract.cliente_http import RespostaHTTP
from brasil_em_dados.extract.coleta import carregar_cadastro, coletar
from brasil_em_dados.extract.conteudo import validar_conteudo
from brasil_em_dados.extract.controle import ler_execucoes
from brasil_em_dados.extract.erros import ErroGravacao, ErroHTTP, ErroValidacao

COD = "sidra_5938_v37"
CABECALHO = {"V": "Valor", "D1C": "Município (Código)", "D2C": "Variável (Código)",
             "D3C": "Ano (Código)"}
SIDRA_OK = json.dumps([
    CABECALHO,
    {"V": "1", "D1C": "4205407", "D2C": "37", "D3C": "2010"},
    {"V": "...", "D1C": "4212650", "D2C": "37", "D3C": "2010"},
]).encode()


def _relogio():
    base = datetime(2026, 11, 14, 15, 30, 0, tzinfo=timezone.utc)
    passos = count()
    return lambda: base + timedelta(milliseconds=500 * next(passos))


def _baixar_com(conteudo: bytes, status: int = 200):
    def baixar_fn(url, sessao):
        return RespostaHTTP(url, status, conteudo, duracao_ms=10, tentativas=1)
    return baixar_fn


def _sem_validacao_de_conteudo(cod_serie, dados, *, cadastro=None):
    """Estes testes cobrem a orquestração; o conteúdo esperado é testado em test_conteudo.py."""


def _coletar(tmp_path, baixar_fn, validar_conteudo_fn=_sem_validacao_de_conteudo):
    return coletar(COD, pasta_raw=tmp_path / "raw", arquivo_controle=tmp_path / "controle.jsonl",
                   baixar_fn=baixar_fn, agora=_relogio(), versao="abc1234",
                   validar_conteudo_fn=validar_conteudo_fn)


def test_conteudo_fora_do_esperado_nao_grava_raw(tmp_path):
    with pytest.raises(ErroValidacao, match="esperadas 4130 linhas"):
        _coletar(tmp_path, _baixar_com(SIDRA_OK), validar_conteudo_fn=validar_conteudo)
    assert not (tmp_path / "raw").exists()
    [execucao] = ler_execucoes(tmp_path / "controle.jsonl")
    assert execucao["status"] == "falha"
    assert "esperadas 4130 linhas" in execucao["erro"]


def test_sucesso_grava_raw_e_controle(tmp_path):
    meta = _coletar(tmp_path, _baixar_com(SIDRA_OK))
    pasta = tmp_path / "raw" / COD
    assert (pasta / meta["arquivo_dados"]).read_bytes() == SIDRA_OK
    assert meta["n_registros"] == 2
    [execucao] = ler_execucoes(tmp_path / "controle.jsonl")
    assert execucao["status"] == "sucesso"
    assert execucao["n_registros"] == 2
    assert execucao["arquivo"] == f"{COD}/{meta['arquivo_dados']}"
    assert execucao["erro"] is None


def test_falha_http_nao_grava_raw_e_registra_erro(tmp_path):
    def baixar_falha(url, sessao):
        raise ErroHTTP("HTTP 503 após 3 tentativas", 503)

    with pytest.raises(ErroHTTP):
        _coletar(tmp_path, baixar_falha)
    assert not (tmp_path / "raw").exists()
    [execucao] = ler_execucoes(tmp_path / "controle.jsonl")
    assert execucao["status"] == "falha"
    assert execucao["arquivo"] is None
    assert execucao["erro"].startswith("ErroHTTP:")


def test_falha_no_meta_json_deixa_coleta_incompleta_e_ignorada(tmp_path, caplog):
    link_real = os.link

    def link_falha_no_meta(origem, destino):
        if str(destino).endswith(raw.SUFIXO_META):
            raise OSError(errno.EIO, "falha simulada")
        return link_real(origem, destino)

    with patch("brasil_em_dados.extract.raw.os.link", side_effect=link_falha_no_meta):
        with caplog.at_level(logging.WARNING), pytest.raises(ErroGravacao):
            _coletar(tmp_path, _baixar_com(SIDRA_OK))

    pasta_raw = tmp_path / "raw"
    assert raw.ultima_coleta_valida(pasta_raw, COD) is None
    assert len(raw.coletas_incompletas(pasta_raw / COD)) == 1
    assert "coleta incompleta será ignorada" in caplog.text
    [execucao] = ler_execucoes(tmp_path / "controle.jsonl")
    assert execucao["status"] == "falha"
    assert execucao["arquivo"] is None
    assert execucao["erro"].startswith("ErroGravacao:")


def test_falha_no_controle_nao_esconde_erro_original(tmp_path, caplog):
    def baixar_falha(url, sessao):
        raise ErroHTTP("HTTP 503 após 3 tentativas", 503)

    with patch("brasil_em_dados.extract.coleta.registrar_execucao",
               side_effect=OSError(errno.EACCES, "sem permissão")):
        with caplog.at_level(logging.WARNING), pytest.raises(ErroHTTP, match="HTTP 503"):
            _coletar(tmp_path, baixar_falha)
    assert "Não foi possível registrar a falha" in caplog.text


# --- cadastro de municípios e API de Pesquisas (integração com a RAW em tmp_path) -----------

CADASTRO = [f"42{i:04d}0" for i in range(1, 294)] + ["4212650", "4220000"]
COD_PESQUISAS = "pesquisas_38_i47001"


def _gravar_cadastro(pasta_raw, corpo: bytes):
    fonte = catalogo.obter("ibge_localidades_sc")
    raw.gravar_coleta(fonte, RespostaHTTP(fonte.url_extrator, 200, corpo, 1, 1), 295,
                      pasta_raw=pasta_raw, coletado_em=datetime.now(timezone.utc), versao="t")


def _corpo_cadastro(ids) -> bytes:
    return json.dumps([{"id": int(i), "nome": "x"} for i in ids]).encode()


def _corpo_pesquisas(codigos6) -> bytes:
    res = [{"localidade": c, "res": {"2021": "1.00"}} for c in codigos6]
    return json.dumps([{"id": 47001, "res": res}]).encode()


def _coletar_pesquisas(tmp_path, corpo: bytes):
    return coletar(COD_PESQUISAS, pasta_raw=tmp_path / "raw",
                   arquivo_controle=tmp_path / "controle.jsonl",
                   baixar_fn=_baixar_com(corpo), agora=_relogio(), versao="abc1234")


def test_carregar_cadastro_le_e_revalida_a_raw(tmp_path):
    _gravar_cadastro(tmp_path, _corpo_cadastro(CADASTRO))
    assert carregar_cadastro(tmp_path) == CADASTRO


def test_carregar_cadastro_sem_coleta_falha_com_mensagem_clara(tmp_path):
    with pytest.raises(ErroValidacao, match="colete ibge_localidades_sc antes"):
        carregar_cadastro(tmp_path)


def test_carregar_cadastro_ilegivel_falha(tmp_path):
    _gravar_cadastro(tmp_path, b"<html>nao e json</html>")
    with pytest.raises(ErroValidacao, match="ilegível"):
        carregar_cadastro(tmp_path)


def test_carregar_cadastro_fora_do_esperado_falha(tmp_path):
    _gravar_cadastro(tmp_path, _corpo_cadastro(CADASTRO[:-1]))
    with pytest.raises(ErroValidacao, match="esperados 295 municípios"):
        carregar_cadastro(tmp_path)


def test_pesquisas_com_cadastro_da_raw_grava_coleta(tmp_path):
    _gravar_cadastro(tmp_path / "raw", _corpo_cadastro(CADASTRO))
    meta = _coletar_pesquisas(tmp_path, _corpo_pesquisas([c[:6] for c in CADASTRO]))
    assert meta["n_registros"] == 295
    assert (tmp_path / "raw" / COD_PESQUISAS / meta["arquivo_dados"]).exists()


def test_pesquisas_fora_do_cadastro_nao_grava_raw(tmp_path):
    _gravar_cadastro(tmp_path / "raw", _corpo_cadastro(CADASTRO))
    codigos = [c[:6] for c in CADASTRO[:-1]] + ["429999"]
    with pytest.raises(ErroValidacao, match="não é 1:1"):
        _coletar_pesquisas(tmp_path, _corpo_pesquisas(codigos))
    assert not (tmp_path / "raw" / COD_PESQUISAS).exists()
    [execucao] = ler_execucoes(tmp_path / "controle.jsonl")
    assert execucao["status"] == "falha"


def test_resposta_invalida_nao_grava_raw(tmp_path):
    with pytest.raises(ErroValidacao):
        _coletar(tmp_path, _baixar_com(b"<html>Just a moment...</html>"))
    assert not (tmp_path / "raw").exists()
    [execucao] = ler_execucoes(tmp_path / "controle.jsonl")
    assert execucao["status"] == "falha"
    assert execucao["erro"].startswith("ErroValidacao:")
