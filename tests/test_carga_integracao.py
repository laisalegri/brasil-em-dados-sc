"""Testes de integração da carga das dimensões (D20).

Tudo numa transação de bed_app que é SEMPRE desfeita: nada fica no banco. Usa o catálogo real
e a amostra real de 5 municípios; funciona com o banco vazio ou já carregado.
"""

import copy
import json
import logging
from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from brasil_em_dados.config import RAIZ_PROJETO
from brasil_em_dados.load.dimensoes import (
    DIM_INDICADOR,
    DIM_MUNICIPIO,
    DIM_SERIE,
    ErroCarga,
    carregar_dimensoes,
    preparar_linhas,
    upsert,
)
from brasil_em_dados.transform.dimensoes import (
    linhas_dim_indicador,
    linhas_dim_municipio,
    linhas_dim_serie,
)

pytestmark = pytest.mark.integracao

AMOSTRA = json.loads((RAIZ_PROJETO / "tests" / "fixtures" / "localidades_sc_amostra.json")
                     .read_text(encoding="utf-8"))


@pytest.fixture
def conexao(engine_app) -> Iterator[Connection]:
    with engine_app.connect() as conexao:
        transacao = conexao.begin()
        try:
            yield conexao
        finally:
            transacao.rollback()


@pytest.fixture
def carregada(conexao) -> Connection:
    """Conexão com as dimensões da amostra já carregadas (na transação desfeita)."""
    carregar_dimensoes(conexao, preparar_linhas(AMOSTRA))
    return conexao


def _valor(conexao: Connection, sql: str):
    return conexao.execute(text(sql)).scalar()


def test_segunda_carga_nao_muda_nada(carregada):
    segunda = {r.tabela: r for r in carregar_dimensoes(carregada, preparar_linhas(AMOSTRA))}
    for resumo in segunda.values():
        assert (resumo.inseridas, resumo.atualizadas) == (0, 0), resumo.texto()
    assert segunda["silver.dim_indicador"].inalteradas == 4
    assert segunda["silver.dim_serie"].inalteradas == 5
    assert segunda["silver.dim_municipio"].inalteradas == 5


def test_carga_grava_os_valores_da_fonte(carregada):
    linha = carregada.execute(text(
        "SELECT nome_municipio, nome_regiao_imediata, cod_mesorregiao "
        "FROM silver.dim_municipio WHERE cod_municipio = '4206702'")).one()
    [herval] = [m for m in AMOSTRA if m["id"] == 4206702]
    assert tuple(linha) == ("Herval d'Oeste", "Joaçaba - Herval d'Oeste",
                            str(herval["microrregiao"]["mesorregiao"]["id"]))
    serie = carregada.execute(text(
        "SELECT codigo_indicador, fator_conversao FROM silver.dim_serie "
        "WHERE cod_serie = 'sidra_5938_v37'")).one()
    assert (serie.codigo_indicador, int(serie.fator_conversao)) == ("pib_corrente", 1000)


def test_mudanca_na_fonte_atualiza_so_a_linha_alterada_e_registra_a_chave(carregada, caplog):
    alterada = copy.deepcopy(AMOSTRA)
    alterada[0]["nome"] = "Florianópolis (nome alterado no teste)"
    with caplog.at_level(logging.INFO, logger="brasil_em_dados.load.dimensoes"):
        resumo = upsert(carregada, DIM_MUNICIPIO, linhas_dim_municipio(alterada))
    assert (resumo.inseridas, resumo.atualizadas, resumo.inalteradas) == (0, 1, 4)
    assert _valor(carregada, "SELECT nome_municipio FROM silver.dim_municipio "
                             "WHERE cod_municipio = '4205407'") == alterada[0]["nome"]
    assert "atualizada 4205407.nome_municipio: 'Florianópolis' →" in caplog.text


def test_campo_descritivo_da_serie_e_atualizado(carregada):
    linhas = linhas_dim_serie()
    linhas[0] = {**linhas[0], "data_referencia": "texto alterado no teste"}
    resumo = upsert(carregada, DIM_SERIE, linhas)
    assert (resumo.inseridas, resumo.atualizadas) == (0, 1)


@pytest.mark.parametrize("espec, linhas, chave, coluna, novo", [
    (DIM_SERIE, linhas_dim_serie, "sidra_5938_v37", "fator_conversao", 1),
    (DIM_SERIE, linhas_dim_serie, "sidra_5938_v37", "unidade_origem", "Reais"),
    (DIM_SERIE, linhas_dim_serie, "sidra_6579_v9324", "codigo_indicador", "pop_censo"),
    (DIM_INDICADOR, linhas_dim_indicador, "pop_censo", "tipo_medida", "estimativa"),
    (DIM_INDICADOR, linhas_dim_indicador, "pib_corrente", "unidade_armazenada", "Mil Reais"),
], ids=["fator", "unidade-origem", "indicador-da-serie", "tipo-medida", "unidade-armazenada"])
def test_mudanca_que_altera_o_sentido_e_recusada_sem_gravar(carregada, espec, linhas, chave,
                                                           coluna, novo):
    coluna_chave = espec.chave[0]
    fonte = [{**l, coluna: novo} if l[coluna_chave] == chave else l for l in linhas()]
    antes = _valor(carregada, f"SELECT {coluna}::text FROM {espec.nome} "
                              f"WHERE {coluna_chave} = '{chave}'")
    with pytest.raises(ErroCarga, match=f"{chave}.{coluna}: .* → {novo!r}") as erro:
        upsert(carregada, espec, fonte)
    assert "crie um novo" in str(erro.value)
    assert _valor(carregada, f"SELECT {coluna}::text FROM {espec.nome} "
                             f"WHERE {coluna_chave} = '{chave}'") == antes


def test_nada_e_apagado_linha_fora_da_fonte_e_mantida(carregada):
    so_quatro = upsert(carregada, DIM_MUNICIPIO, linhas_dim_municipio(AMOSTRA[1:]))
    assert so_quatro.so_no_banco >= 1
    assert _valor(carregada, "SELECT count(*) FROM silver.dim_municipio "
                             "WHERE cod_municipio = '4205407'") == 1


def test_falha_na_ultima_tabela_desfaz_as_anteriores(carregada):
    # Indicador com descrição alterada (permitido) + município que viola um CHECK do banco.
    linhas = preparar_linhas(AMOSTRA)
    _, indicadores = linhas[0]
    indicadores[0] = {**indicadores[0], "descricao": "descrição alterada no teste"}
    _, municipios = linhas[2]
    municipios[0] = {**municipios[0], "cod_microrregiao": "4299"}  # micro tem 5 dígitos
    sql_descricao = ("SELECT descricao FROM silver.dim_indicador "
                     f"WHERE codigo_indicador = '{indicadores[0]['codigo_indicador']}'")
    antes = _valor(carregada, sql_descricao)

    with pytest.raises(IntegrityError):
        with carregada.begin_nested():  # mesmo papel da transação de executar()
            carregar_dimensoes(carregada, linhas)

    assert _valor(carregada, sql_descricao) == antes
