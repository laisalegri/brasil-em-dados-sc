"""Testes do controle de execução (execucoes.jsonl)."""

from datetime import datetime, timezone

import pytest

from brasil_em_dados.extract.controle import ler_execucoes, registrar_execucao

INICIO = datetime(2026, 11, 14, 15, 30, 0, tzinfo=timezone.utc)
FIM = datetime(2026, 11, 14, 15, 30, 2, 500000, tzinfo=timezone.utc)


def test_registra_uma_linha_por_execucao(tmp_path):
    caminho = tmp_path / "controle" / "execucoes.jsonl"
    registrar_execucao(caminho, cod_serie="sidra_5938_v37", inicio=INICIO, fim=FIM,
                       status="sucesso", n_registros=4130,
                       arquivo="sidra_5938_v37/20261114T153002500Z.json", erro=None)
    registrar_execucao(caminho, cod_serie="sidra_5938_v37", inicio=INICIO, fim=FIM,
                       status="falha", n_registros=None, arquivo=None, erro="ErroHTTP: HTTP 503")
    execucoes = ler_execucoes(caminho)
    assert len(execucoes) == 2
    assert execucoes[0] == {
        "cod_serie": "sidra_5938_v37",
        "inicio": "2026-11-14T15:30:00.000Z",
        "fim": "2026-11-14T15:30:02.500Z",
        "status": "sucesso",
        "n_registros": 4130,
        "arquivo": "sidra_5938_v37/20261114T153002500Z.json",
        "erro": None,
    }
    assert execucoes[1]["status"] == "falha"
    assert execucoes[1]["erro"] == "ErroHTTP: HTTP 503"


def test_status_invalido_falha(tmp_path):
    with pytest.raises(ValueError, match="status inválido"):
        registrar_execucao(tmp_path / "x.jsonl", cod_serie="s", inicio=INICIO, fim=FIM,
                           status="ok", n_registros=None, arquivo=None, erro=None)


def test_ler_sem_arquivo_devolve_lista_vazia(tmp_path):
    assert ler_execucoes(tmp_path / "nao_existe.jsonl") == []
