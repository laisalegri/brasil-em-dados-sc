"""Testes da carga da fato e do controle sem banco: RAW, JSONL, resumo por série e CLI."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from brasil_em_dados.extract import catalogo, raw
from brasil_em_dados.extract.cliente_http import RespostaHTTP
from brasil_em_dados.load import __main__ as cli
from brasil_em_dados.load import controle, fato
from brasil_em_dados.load.upsert import Classificacao, ErroCarga, Resumo

COLETADO_EM = datetime(2026, 11, 14, 23, 38, 1, 905000, tzinfo=timezone.utc)


def _gravar(pasta_raw, cod_serie: str, corpo: bytes, coletado_em=COLETADO_EM):
    fonte = catalogo.obter(cod_serie)
    return raw.gravar_coleta(fonte, RespostaHTTP(fonte.url_extrator, 200, corpo, 1, 1), 1,
                             pasta_raw=pasta_raw, coletado_em=coletado_em, versao="t")


# --- leitura da coleta ------------------------------------------------------------------------

def test_ler_coleta_devolve_dados_e_coletado_em_do_meta(tmp_path):
    _gravar(tmp_path, "sidra_4709_v93", b'[{"V": "Valor"}]')
    dados, coletado_em, arquivo = fato.ler_coleta(tmp_path, "sidra_4709_v93")
    assert dados == [{"V": "Valor"}]
    assert coletado_em == COLETADO_EM
    assert coletado_em.tzinfo is not None
    assert arquivo.parent.name == "sidra_4709_v93"


def test_ler_coleta_usa_a_ultima_valida(tmp_path):
    _gravar(tmp_path, "sidra_4709_v93", b"[1]", datetime(2026, 11, 1, tzinfo=timezone.utc))
    _gravar(tmp_path, "sidra_4709_v93", b"[2]", datetime(2026, 11, 2, tzinfo=timezone.utc))
    dados, coletado_em, _ = fato.ler_coleta(tmp_path, "sidra_4709_v93")
    assert (dados, coletado_em.day) == ([2], 2)


def test_ler_coleta_sem_coleta_falha(tmp_path):
    with pytest.raises(ErroCarga, match="Nenhuma coleta válida de sidra_4709_v93"):
        fato.ler_coleta(tmp_path, "sidra_4709_v93")


def test_ler_coleta_ilegivel_falha(tmp_path):
    _gravar(tmp_path, "sidra_4709_v93", b"<html>")
    with pytest.raises(ErroCarga, match="ilegível"):
        fato.ler_coleta(tmp_path, "sidra_4709_v93")


# --- controle de execução ---------------------------------------------------------------------

REGISTRO = {"cod_serie": "sidra_4709_v93", "inicio": "2026-11-14T23:38:01.372Z",
            "fim": "2026-11-14T23:38:01.906Z", "status": "sucesso", "n_registros": 295,
            "arquivo": "sidra_4709_v93/20261114T233801905Z.json", "erro": None}


def test_registro_do_controle_vira_linha_com_datas_em_utc():
    linha = controle.linha_controle(REGISTRO)
    assert linha["inicio"] == datetime(2026, 11, 14, 23, 38, 1, 372000, tzinfo=timezone.utc)
    assert linha["fim"].tzinfo is not None
    assert tuple(linha) == controle.COLUNAS_CONTROLE


@pytest.mark.parametrize("registro", [
    {k: v for k, v in REGISTRO.items() if k != "status"},
    {**REGISTRO, "inicio": "ontem"},
    {**REGISTRO, "inicio": "2026-11-14T23:38:01"},  # sem fuso
])
def test_registro_do_controle_fora_do_formato_falha(registro):
    with pytest.raises(ErroCarga, match="Registro do controle"):
        controle.linha_controle(registro)


def test_ler_controle_de_arquivo(tmp_path):
    arquivo = tmp_path / "execucoes.jsonl"
    arquivo.write_text(json.dumps(REGISTRO) + "\n", encoding="utf-8")
    assert len(controle.ler_controle(arquivo)) == 1
    assert controle.ler_controle(tmp_path / "nao_existe.jsonl") == []


def test_controle_ilegivel_falha(tmp_path):
    arquivo = tmp_path / "execucoes.jsonl"
    arquivo.write_text("{quebrado\n", encoding="utf-8")
    with pytest.raises(ErroCarga, match="ilegível"):
        controle.ler_controle(arquivo)


def test_execucao_registrada_nao_pode_mudar():
    assert set(controle.CONTROLE.imutaveis) == set(controle.COLUNAS_CONTROLE) - {
        "cod_serie", "inicio"}


# --- resumo por série -------------------------------------------------------------------------

def _linha(municipio: str, cod_serie: str) -> dict:
    return {"cod_municipio": municipio, "codigo_indicador": "pop_censo", "ano": 2010,
            "cod_serie": cod_serie}


def test_resumo_agrupa_pela_serie_de_origem():
    linhas = [_linha("4205407", "sidra_1378_v93"), _linha("4205506", "sidra_1378_v93"),
              _linha("4206702", "sidra_4709_v93")]
    chaves = [(l["cod_municipio"], "pop_censo", 2010) for l in linhas]
    classificacao = Classificacao(
        inseridas=[chaves[0]], atualizadas={chaves[1]: []}, inalteradas=[chaves[2]],
        proibidas=[], so_no_banco={("4299990", "pop_censo", 2010): {"cod_serie": "sidra_4709_v93"}})
    resumos = fato.resumir_por_serie(classificacao, linhas, ["sidra_1378_v93", "sidra_4709_v93"])
    assert resumos == [Resumo("fato sidra_1378_v93", 1, 1, 0, 0),
                       Resumo("fato sidra_4709_v93", 0, 0, 1, 1)]


def test_fato_compara_so_valor_e_sinal_e_nao_deixa_trocar_a_serie():
    assert fato.FATO.colunas_comparadas == ("valor", "sinal_origem")
    assert fato.FATO.imutaveis == ("cod_serie",)
    assert "data_coleta" in fato.FATO.nao_chave  # gravada junto quando o valor muda


# --- CLI --------------------------------------------------------------------------------------

def _engine_falso():
    engine = MagicMock()
    engine.begin.return_value.__enter__.return_value = MagicMock(name="conexao")
    engine.begin.return_value.__exit__.return_value = False
    return engine


def test_tudo_roda_dimensoes_fato_e_controle_numa_transacao_so(tmp_path):
    engine = _engine_falso()
    ordem = []
    with patch.object(cli.dimensoes, "ler_municipios_da_raw", return_value=([], tmp_path)), \
         patch.object(cli.dimensoes, "preparar_linhas", return_value=[]), \
         patch.object(cli.dimensoes, "carregar_dimensoes",
                      side_effect=lambda *a: ordem.append("dimensoes") or []), \
         patch.object(cli.fato, "carregar_fato",
                      side_effect=lambda *a: ordem.append("fato") or []), \
         patch.object(cli.controle, "carregar_controle",
                      side_effect=lambda *a: ordem.append("controle") or Resumo("c", 0, 0, 0)):
        cli.executar("tudo", engine, tmp_path, tmp_path / "x.jsonl")
    assert ordem == ["dimensoes", "fato", "controle"]
    engine.begin.assert_called_once()


def test_fato_nao_carrega_dimensoes(tmp_path):
    engine = _engine_falso()
    with patch.object(cli.dimensoes, "ler_municipios_da_raw") as ler, \
         patch.object(cli.fato, "carregar_fato", return_value=[]), \
         patch.object(cli.controle, "carregar_controle", return_value=Resumo("c", 0, 0, 0)):
        resumos = cli.executar("fato", engine, tmp_path, tmp_path / "x.jsonl")
    ler.assert_not_called()
    assert resumos == [Resumo("c", 0, 0, 0)]


def test_cli_fato_com_erro_devolve_1(caplog):
    engine = Mock()
    with patch.object(cli, "configurar_logging"), \
         patch.object(cli, "executar", side_effect=ErroCarga("dim_serie vazia")), \
         caplog.at_level("ERROR", logger=cli.logger.name):
        assert cli.main(["fato"], engine=engine) == 1
    assert "transação desfeita. dim_serie vazia" in caplog.text


def test_loggers_ficam_na_hierarquia_do_projeto():
    assert fato.logger.name.startswith("brasil_em_dados.")
    assert controle.logger.name.startswith("brasil_em_dados.")
