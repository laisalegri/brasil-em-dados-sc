"""Testes do catálogo de séries: fonte única, conferida contra o dicionário de dados."""

import re

import pytest

from brasil_em_dados.config import RAIZ_PROJETO
from brasil_em_dados.extract import catalogo

DICIONARIO = RAIZ_PROJETO / "docs" / "dicionario_dados.md"


def _linhas_dim_serie() -> dict[str, list[str]]:
    """Lê as linhas da tabela 1.2 (dim_serie) do dicionário, indexadas por cod_serie."""
    texto = DICIONARIO.read_text(encoding="utf-8")
    secao = texto.split("### 1.2", 1)[1].split("\n### ", 1)[0]
    linhas = {}
    for linha in secao.splitlines():
        if linha.startswith("| `"):
            celulas = [c.strip().strip("`") for c in linha.strip().strip("|").split("|")]
            linhas[celulas[0]] = celulas
    return linhas


def _linhas_dim_indicador() -> dict[str, list[str]]:
    """Lê as linhas da tabela 1.1 (dim_indicador) do dicionário, indexadas pelo código."""
    texto = DICIONARIO.read_text(encoding="utf-8")
    secao = texto.split("### 1.1", 1)[1].split("\n### ", 1)[0]
    linhas = {}
    for linha in secao.splitlines():
        if linha.startswith("| `"):
            celulas = [c.strip().strip("`") for c in linha.strip().strip("|").split("|")]
            linhas[celulas[0]] = celulas
    return linhas


def test_indicadores_do_catalogo_iguais_aos_do_dicionario():
    assert set(catalogo.INDICADORES) == set(_linhas_dim_indicador())


@pytest.mark.parametrize("indicador", catalogo.indicadores(), ids=lambda i: i.codigo_indicador)
def test_atributos_do_indicador_iguais_aos_do_dicionario(indicador):
    celulas = _linhas_dim_indicador()[indicador.codigo_indicador]
    assert celulas[1:] == [indicador.nome, indicador.unidade_armazenada,
                           indicador.tipo_medida, indicador.descricao]


@pytest.mark.parametrize("indicador", catalogo.indicadores(), ids=lambda i: i.codigo_indicador)
def test_tipo_medida_do_indicador_e_valido(indicador):
    assert indicador.tipo_medida in {"estimativa", "censo", "nominal"}


@pytest.mark.parametrize("serie", catalogo.series(), ids=lambda s: s.cod_serie)
def test_toda_serie_aponta_para_um_indicador_do_catalogo(serie):
    assert serie.codigo_indicador in catalogo.INDICADORES


def test_chaves_do_catalogo_iguais_ao_cod_serie():
    for chave, fonte in catalogo.FONTES.items():
        assert chave == fonte.cod_serie


def test_series_do_catalogo_iguais_as_do_dicionario():
    no_dicionario = _linhas_dim_serie()
    no_catalogo = {s.cod_serie for s in catalogo.series()}
    assert no_catalogo == set(no_dicionario)


@pytest.mark.parametrize("serie", catalogo.series(), ids=lambda s: s.cod_serie)
def test_atributos_da_serie_iguais_aos_do_dicionario(serie):
    celulas = _linhas_dim_serie()[serie.cod_serie]
    assert celulas[1] == serie.codigo_indicador
    assert celulas[2] == serie.fonte
    assert celulas[6] == str(serie.fator_conversao)
    # As células abaixo têm texto explicativo extra no dicionário, por isso a comparação
    # é por número inteiro (tabela/variável) ou por início do texto (unidade/data).
    assert re.search(rf"\b{re.escape(serie.tabela_ou_pesquisa)}\b", celulas[3])
    assert re.search(rf"\b{re.escape(serie.variavel_ou_indicador)}\b", celulas[4])
    assert celulas[5].startswith(serie.unidade_origem)
    assert celulas[7].startswith(serie.data_referencia)


@pytest.mark.parametrize("fonte", list(catalogo.FONTES.values()), ids=lambda f: f.cod_serie)
def test_url_do_catalogo_aparece_no_dicionario(fonte):
    assert fonte.url_extrator in DICIONARIO.read_text(encoding="utf-8")


def test_localidades_e_fonte_de_dimensao_fora_das_series():
    localidades = catalogo.obter("ibge_localidades_sc")
    assert localidades.tipo == catalogo.TIPO_DIMENSAO
    assert localidades not in catalogo.series()


def test_obter_cod_serie_desconhecido_falha_com_mensagem_clara():
    with pytest.raises(KeyError, match="cod_serie desconhecido"):
        catalogo.obter("nao_existe")
