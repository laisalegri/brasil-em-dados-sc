"""Testes da gravação imutável na RAW e dos metadados, em pasta temporária (tmp_path)."""

import errno
import json
import logging
import subprocess
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from brasil_em_dados.extract import catalogo, raw
from brasil_em_dados.extract.cliente_http import RespostaHTTP
from brasil_em_dados.extract.erros import ErroGravacao

SERIE = catalogo.obter("sidra_5938_v37")
INSTANTE = datetime(2026, 11, 14, 15, 30, 12, 45000, tzinfo=timezone.utc)


def _resposta(conteudo: bytes) -> RespostaHTTP:
    return RespostaHTTP(SERIE.url_extrator, 200, conteudo, duracao_ms=120, tentativas=1)


def _gravar(pasta_raw, conteudo: bytes, instante: datetime = INSTANTE) -> dict:
    return raw.gravar_coleta(SERIE, _resposta(conteudo), 1, pasta_raw=pasta_raw,
                             coletado_em=instante, versao="abc1234")


def _arquivos_visiveis(pasta):
    return sorted(p.name for p in pasta.iterdir())


def test_carimbo_utc_com_milissegundos():
    assert raw.carimbo_utc(INSTANTE) == "20261114T153012045Z"


def test_carimbo_converte_fuso_para_utc():
    brasilia = timezone(timedelta(hours=-3))
    instante = datetime(2026, 11, 14, 12, 30, 12, 45000, tzinfo=brasilia)
    assert raw.carimbo_utc(instante) == "20261114T153012045Z"


def test_carimbo_sem_fuso_falha():
    with pytest.raises(ValueError):
        raw.carimbo_utc(datetime(2026, 11, 14))


def test_gravar_exclusivo_grava_bytes_e_remove_temporario(tmp_path):
    destino = tmp_path / "serie" / "a.json"
    raw.gravar_exclusivo(destino, b"conteudo")
    assert destino.read_bytes() == b"conteudo"
    assert _arquivos_visiveis(destino.parent) == ["a.json"]


def test_gravar_exclusivo_nunca_sobrescreve(tmp_path):
    destino = tmp_path / "a.json"
    destino.write_bytes(b"original")
    with pytest.raises(ErroGravacao, match="nunca é sobrescrita"):
        raw.gravar_exclusivo(destino, b"novo")
    assert destino.read_bytes() == b"original"
    assert _arquivos_visiveis(tmp_path) == ["a.json"]


def test_sem_suporte_a_os_link_falha_sem_caminho_alternativo(tmp_path):
    destino = tmp_path / "a.json"
    with patch("brasil_em_dados.extract.raw.os.link", side_effect=OSError(errno.EPERM, "não suportado")):
        with pytest.raises(ErroGravacao, match="hard links"):
            raw.gravar_exclusivo(destino, b"conteudo")
    assert not destino.exists()
    assert _arquivos_visiveis(tmp_path) == []


def test_falha_ao_gravar_temporario_vira_erro_gravacao(tmp_path):
    destino = tmp_path / "a.json"
    with patch("brasil_em_dados.extract.raw.open", create=True,
               side_effect=OSError(errno.ENOSPC, "disco cheio")):
        with pytest.raises(ErroGravacao, match="temporário"):
            raw.gravar_exclusivo(destino, b"conteudo")
    assert not destino.exists()


def test_meta_json_e_gravado_por_ultimo(tmp_path):
    espiao = Mock(wraps=raw.gravar_exclusivo)
    with patch("brasil_em_dados.extract.raw.gravar_exclusivo", espiao):
        _gravar(tmp_path, b"[1]")
    destinos = [chamada.args[0].name for chamada in espiao.call_args_list]
    assert destinos == ["20261114T153012045Z.json", "20261114T153012045Z.meta.json"]


def test_parametros_dos_metadados_sao_copia_do_catalogo(tmp_path):
    original = json.loads(json.dumps(SERIE.parametros))
    meta = _gravar(tmp_path, b"[1]")
    meta["parametros"]["tabela"] = "alterado"
    assert SERIE.parametros == original


def test_gravar_coleta_grava_par_com_bytes_originais(tmp_path):
    conteudo = b'[ {"NC":"Nivel"},\n  {"V":"1"} ]'
    meta = _gravar(tmp_path, conteudo)
    pasta = tmp_path / SERIE.cod_serie
    assert _arquivos_visiveis(pasta) == ["20261114T153012045Z.json", "20261114T153012045Z.meta.json"]
    assert (pasta / "20261114T153012045Z.json").read_bytes() == conteudo
    gravado = json.loads((pasta / "20261114T153012045Z.meta.json").read_text(encoding="utf-8"))
    assert gravado == meta
    assert meta["sha256"] == raw.calcular_sha256(conteudo)
    assert meta["tamanho_bytes"] == len(conteudo)
    assert meta["coletado_em"] == "2026-11-14T15:30:12.045Z"
    assert meta["parametros"] == SERIE.parametros
    assert meta["versao_extrator"] == "abc1234"
    assert meta["igual_a_anterior"] is False


def test_igual_a_anterior_compara_com_ultima_coleta_valida(tmp_path):
    _gravar(tmp_path, b"[1]", INSTANTE)
    segunda = _gravar(tmp_path, b"[1]", INSTANTE + timedelta(seconds=1))
    terceira = _gravar(tmp_path, b"[2]", INSTANTE + timedelta(seconds=2))
    assert segunda["igual_a_anterior"] is True
    assert terceira["igual_a_anterior"] is False


def test_coleta_incompleta_e_ignorada(tmp_path, caplog):
    _gravar(tmp_path, b"[1]", INSTANTE)
    incompleta = tmp_path / SERIE.cod_serie / "20261114T153013000Z.json"
    incompleta.write_bytes(b"[2]")
    with caplog.at_level(logging.WARNING):
        ultima = raw.ultima_coleta_valida(tmp_path, SERIE.cod_serie)
    assert ultima is not None
    assert ultima[0].name == "20261114T153012045Z.json"
    assert "Coleta incompleta ignorada" in caplog.text
    nova = _gravar(tmp_path, b"[1]", INSTANTE + timedelta(seconds=5))
    assert nova["igual_a_anterior"] is True


def test_ultima_coleta_valida_sem_coletas(tmp_path):
    assert raw.ultima_coleta_valida(tmp_path, SERIE.cod_serie) is None


def test_mesmo_carimbo_nao_sobrescreve(tmp_path):
    _gravar(tmp_path, b"[1]", INSTANTE)
    with pytest.raises(ErroGravacao):
        _gravar(tmp_path, b"[2]", INSTANTE)
    assert (tmp_path / SERIE.cod_serie / "20261114T153012045Z.json").read_bytes() == b"[1]"


def _processo(saida: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=saida, stderr="")


def test_versao_extrator_limpa():
    with patch("brasil_em_dados.extract.raw.subprocess.run",
               side_effect=[_processo("abc1234\n"), _processo("")]):
        assert raw.versao_extrator() == "abc1234"


def test_versao_extrator_com_mudancas_locais():
    with patch("brasil_em_dados.extract.raw.subprocess.run",
               side_effect=[_processo("abc1234\n"), _processo(" M src/x.py\n")]):
        assert raw.versao_extrator() == "abc1234-dirty"


def test_versao_extrator_sem_git():
    with patch("brasil_em_dados.extract.raw.subprocess.run", side_effect=FileNotFoundError):
        assert raw.versao_extrator() == "desconhecido"
