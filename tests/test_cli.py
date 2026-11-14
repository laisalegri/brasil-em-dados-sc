"""Testes da linha de comando das coletas, sem rede e sem escrever em data/ ou logs/."""

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
