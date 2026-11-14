"""Testes da linha de comando das coletas, sem rede e sem escrever em data/ ou logs/."""

import logging
from unittest.mock import patch

import pytest

from brasil_em_dados.extract import __main__ as cli
from brasil_em_dados.extract import catalogo

META = {"n_registros": 295, "igual_a_anterior": False, "arquivo_dados": "x.json"}


def test_ordem_de_coleta_comeca_pelo_cadastro_e_cobre_o_catalogo():
    ordem = cli.ordem_de_coleta()
    assert ordem[0] == "ibge_localidades_sc"
    assert sorted(ordem) == sorted(catalogo.FONTES)


def test_executar_continua_depois_de_uma_falha():
    def coletar_fn(cod_serie):
        if cod_serie == "sidra_1378_v93":
            raise RuntimeError("falha simulada")
        return META

    resultados = cli.executar(cli.ordem_de_coleta(), coletar_fn)
    assert len(resultados) == len(catalogo.FONTES)
    falhas = [r for r in resultados if r.meta is None]
    assert [r.cod_serie for r in falhas] == ["sidra_1378_v93"]
    assert falhas[0].erro == "RuntimeError: falha simulada"


def test_main_devolve_1_se_alguma_coleta_falhar():
    def coletar_fn(cod_serie):
        raise RuntimeError("falha simulada")

    with patch.object(cli, "configurar_logging"), patch.object(cli, "coletar", coletar_fn):
        assert cli.main(["sidra_4709_v93"]) == 1


def test_main_todas_com_sucesso_devolve_0():
    with patch.object(cli, "configurar_logging"), patch.object(cli, "coletar", lambda c: META):
        assert cli.main(["todas"]) == 0


def test_alvo_desconhecido_e_recusado():
    with pytest.raises(SystemExit):
        cli.main(["nao_existe"])


# --- D16: falhas com "todas" ----------------------------------------------------------------

def test_executar_tenta_todas_as_fontes_mesmo_se_o_cadastro_falhar():
    chamadas = []

    def coletar_fn(cod_serie):
        chamadas.append(cod_serie)
        if cod_serie == "ibge_localidades_sc":
            raise ValueError("cadastro indisponível")
        return META

    resultados = cli.executar(cli.ordem_de_coleta(), coletar_fn)
    assert chamadas == cli.ordem_de_coleta()
    assert [r.cod_serie for r in resultados] == chamadas
    assert resultados[0].erro == "ValueError: cadastro indisponível"
    assert all(r.erro is None for r in resultados[1:])


def test_main_todas_com_uma_falha_devolve_1_e_tenta_todas():
    chamadas = []

    def coletar_fn(cod_serie):
        chamadas.append(cod_serie)
        if cod_serie == "sidra_5938_v37":
            raise RuntimeError("falha simulada")
        return META

    with patch.object(cli, "configurar_logging"), patch.object(cli, "coletar", coletar_fn):
        assert cli.main(["todas"]) == 1
    assert chamadas == cli.ordem_de_coleta()


def test_registrar_resumo_mostra_falha_em_nivel_error_e_total(caplog):
    resultados = [
        cli.Resultado("ibge_localidades_sc", META, None),
        cli.Resultado("sidra_4709_v93", None, "ErroValidacao: municípios fora do cadastro"),
    ]
    with caplog.at_level(logging.INFO, logger="brasil_em_dados"):
        cli.registrar_resumo(resultados)

    [erro] = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert "FALHA" in erro.getMessage()
    assert "sidra_4709_v93" in erro.getMessage()
    assert "municípios fora do cadastro" in erro.getMessage()
    assert "Total: 2 coleta(s), 1 sucesso(s), 1 falha(s)" in caplog.text


def test_registrar_resumo_sem_falhas_nao_gera_erro(caplog):
    resultados = [cli.Resultado(c, META, None) for c in cli.ordem_de_coleta()]
    with caplog.at_level(logging.INFO, logger="brasil_em_dados"):
        cli.registrar_resumo(resultados)
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert f"Total: {(n := len(catalogo.FONTES))} coleta(s), {n} sucesso(s), 0 falha(s)" in caplog.text
    assert "igual_a_anterior=False" in caplog.text
