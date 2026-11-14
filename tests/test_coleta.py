"""Testes da orquestração da coleta: sucesso grava RAW e controle; falha não grava RAW."""

import errno
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from itertools import count
from unittest.mock import patch

import pytest

from brasil_em_dados.extract import raw
from brasil_em_dados.extract.cliente_http import RespostaHTTP
from brasil_em_dados.extract.coleta import coletar
from brasil_em_dados.extract.controle import ler_execucoes
from brasil_em_dados.extract.erros import ErroGravacao, ErroHTTP, ErroValidacao

COD = "sidra_5938_v37"
SIDRA_OK = json.dumps([{"NC": "Nível"}, {"NC": "6", "V": "1"}, {"NC": "6", "V": "..."}]).encode()


def _relogio():
    base = datetime(2026, 11, 14, 15, 30, 0, tzinfo=timezone.utc)
    passos = count()
    return lambda: base + timedelta(milliseconds=500 * next(passos))


def _baixar_com(conteudo: bytes, status: int = 200):
    def baixar_fn(url, sessao):
        return RespostaHTTP(url, status, conteudo, duracao_ms=10, tentativas=1)
    return baixar_fn


def _coletar(tmp_path, baixar_fn):
    return coletar(COD, pasta_raw=tmp_path / "raw", arquivo_controle=tmp_path / "controle.jsonl",
                   baixar_fn=baixar_fn, agora=_relogio(), versao="abc1234")


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


def test_resposta_invalida_nao_grava_raw(tmp_path):
    with pytest.raises(ErroValidacao):
        _coletar(tmp_path, _baixar_com(b"<html>Just a moment...</html>"))
    assert not (tmp_path / "raw").exists()
    [execucao] = ler_execucoes(tmp_path / "controle.jsonl")
    assert execucao["status"] == "falha"
    assert execucao["erro"].startswith("ErroValidacao:")
