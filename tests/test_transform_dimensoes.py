"""Testes da transformação das dimensões (sem banco), com a amostra real da API de Localidades."""

import copy
import json

import pytest

from brasil_em_dados.config import RAIZ_PROJETO
from brasil_em_dados.extract import catalogo
from brasil_em_dados.transform.dimensoes import (
    COLUNAS_DIM_MUNICIPIO,
    ErroTransformacao,
    codigo_municipio,
    linha_dim_municipio,
    linhas_dim_indicador,
    linhas_dim_municipio,
    linhas_dim_serie,
)

AMOSTRA = json.loads((RAIZ_PROJETO / "tests" / "fixtures" / "localidades_sc_amostra.json")
                     .read_text(encoding="utf-8"))


def _por_codigo() -> dict[str, dict[str, str]]:
    return {linha["cod_municipio"]: linha for linha in linhas_dim_municipio(AMOSTRA)}


# --- código do município ----------------------------------------------------------------------

def test_id_numerico_vira_texto_de_7_digitos():
    assert codigo_municipio(4205407) == "4205407"
    assert isinstance(codigo_municipio(4205407), str)


def test_zero_a_esquerda_e_preservado():
    # Nenhum código de SC começa com zero, mas a conversão não pode perder zeros (regra 1).
    assert codigo_municipio(420540) == "0420540"
    assert codigo_municipio("0420540") == "0420540"


def test_codigo_com_zero_a_esquerda_nao_passa_como_municipio_de_sc():
    municipio = copy.deepcopy(AMOSTRA[0])
    municipio["id"] = 420540
    with pytest.raises(ErroTransformacao, match="fora do padrão 42xxxxx: 0420540"):
        linha_dim_municipio(municipio)


# --- amostra real -----------------------------------------------------------------------------

def test_todas_as_colunas_sao_texto_e_nao_vazias():
    for linha in linhas_dim_municipio(AMOSTRA):
        assert tuple(linha) == COLUNAS_DIM_MUNICIPIO
        assert all(isinstance(v, str) and v for v in linha.values())


def test_florianopolis_nas_duas_hierarquias():
    assert _por_codigo()["4205407"] == {
        "cod_municipio": "4205407", "nome_municipio": "Florianópolis",
        "cod_regiao_imediata": "420001", "nome_regiao_imediata": "Florianópolis",
        "cod_regiao_intermediaria": "4201", "nome_regiao_intermediaria": "Florianópolis",
        "cod_microrregiao": "42016", "nome_microrregiao": "Florianópolis",
        "cod_mesorregiao": "4205", "nome_mesorregiao": "Grande Florianópolis",
        "cod_uf": "42", "sigla_uf": "SC",
    }


def test_apostrofo_no_nome_do_municipio_e_da_regiao():
    linha = _por_codigo()["4206702"]
    assert linha["nome_municipio"] == "Herval d'Oeste"
    assert linha["nome_regiao_imediata"] == "Joaçaba - Herval d'Oeste"


def test_hifen_e_acento_no_nome():
    assert _por_codigo()["4206108"]["nome_municipio"] == "Grão-Pará"


def test_municipios_instalados_em_2013_estao_presentes():
    codigos = _por_codigo()
    assert codigos["4212650"]["nome_municipio"] == "Pescaria Brava"
    assert codigos["4220000"]["nome_municipio"] == "Balneário Rincão"


def test_ids_de_meso_e_intermediaria_nao_sao_confundidos():
    # Mesma faixa de ids (4201–4207) para divisões diferentes (D06): cada uma vem da sua origem.
    linha = _por_codigo()["4205407"]
    assert linha["cod_mesorregiao"] == "4205"
    assert linha["cod_regiao_intermediaria"] == "4201"


# --- erros ------------------------------------------------------------------------------------

def test_municipio_sem_hierarquia_nova_falha_citando_o_id():
    municipio = copy.deepcopy(AMOSTRA[0])
    del municipio["regiao-imediata"]
    with pytest.raises(ErroTransformacao, match="4205407.*regiao-imediata"):
        linha_dim_municipio(municipio)


def test_uf_da_hierarquia_nova_sem_sigla_falha_com_erro_de_transformacao():
    municipio = copy.deepcopy(AMOSTRA[0])
    del municipio["regiao-imediata"]["regiao-intermediaria"]["UF"]["sigla"]
    with pytest.raises(ErroTransformacao, match="4205407.*falta o campo 'sigla'"):
        linha_dim_municipio(municipio)


def test_nivel_da_hierarquia_que_nao_e_objeto_falha_com_mensagem_propria():
    municipio = copy.deepcopy(AMOSTRA[0])
    municipio["microrregiao"] = "Florianópolis"
    with pytest.raises(ErroTransformacao, match="4205407.*não é um objeto"):
        linha_dim_municipio(municipio)


def test_uf_diferente_de_sc_falha():
    municipio = copy.deepcopy(AMOSTRA[0])
    municipio["regiao-imediata"]["regiao-intermediaria"]["UF"]["sigla"] = "RS"
    with pytest.raises(ErroTransformacao, match="UF diferente de 42/SC"):
        linha_dim_municipio(municipio)


def test_codigo_repetido_falha():
    with pytest.raises(ErroTransformacao, match="repetidos: \\['4205407'\\]"):
        linhas_dim_municipio([AMOSTRA[0], copy.deepcopy(AMOSTRA[0])])


def test_resposta_que_nao_e_lista_falha():
    with pytest.raises(ErroTransformacao, match="deveria ser uma lista"):
        linhas_dim_municipio({"id": 4205407})


# --- catálogo ---------------------------------------------------------------------------------

def test_dim_indicador_tem_os_4_indicadores_do_catalogo():
    linhas = linhas_dim_indicador()
    assert [l["codigo_indicador"] for l in linhas] == list(catalogo.INDICADORES)
    assert {l["tipo_medida"] for l in linhas} == {"estimativa", "censo", "nominal"}


def test_dim_serie_tem_as_5_series_ligadas_ao_indicador_certo():
    por_serie = {l["cod_serie"]: l["codigo_indicador"] for l in linhas_dim_serie()}
    assert por_serie == {
        "sidra_6579_v9324": "pop_estimada",
        "sidra_1378_v93": "pop_censo",
        "sidra_4709_v93": "pop_censo",
        "sidra_5938_v37": "pib_corrente",
        "pesquisas_38_i47001": "pib_per_capita",
    }


def test_dim_serie_nao_inclui_fonte_de_dimensao():
    assert "ibge_localidades_sc" not in {l["cod_serie"] for l in linhas_dim_serie()}


def test_serie_sem_atributo_no_catalogo_falha():
    incompleta = catalogo.FonteColeta(cod_serie="x", tipo=catalogo.TIPO_SERIE, fonte="sidra",
                                      url_extrator="https://x", codigo_indicador="pop_censo")
    with pytest.raises(ErroTransformacao, match="Série x sem"):
        linhas_dim_serie([incompleta])
