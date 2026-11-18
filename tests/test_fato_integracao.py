"""Testes de integração da carga da fato e do controle (D21).

Tudo numa transação de bed_app que é SEMPRE desfeita: nada fica no banco. Usa a RAW real
(só leitura) e as dimensões já carregadas (D20); pula se faltar alguma das duas.
"""

import copy
import json
import logging
from collections.abc import Iterator
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import Connection, text

from brasil_em_dados.config import ARQUIVO_CONTROLE, PASTA_RAW
from brasil_em_dados.extract import catalogo
from brasil_em_dados.extract.raw import ultima_coleta_valida
from brasil_em_dados.load import controle, fato
from brasil_em_dados.load.upsert import ErroCarga, aplicar_upsert

pytestmark = pytest.mark.integracao

TOTAL_ESPERADO = 12093
POR_SERIE = {"sidra_6579_v9324": 3245, "sidra_1378_v93": 293, "sidra_4709_v93": 295,
             "sidra_5938_v37": 4130, "pesquisas_38_i47001": 4130}


@pytest.fixture
def conexao(engine_app) -> Iterator[Connection]:
    faltando = [s.cod_serie for s in catalogo.series()
                if ultima_coleta_valida(PASTA_RAW, s.cod_serie) is None]
    if faltando:
        pytest.skip(f"RAW sem coleta válida de {faltando}; rode a coleta antes")
    with engine_app.connect() as conexao:
        transacao = conexao.begin()
        try:
            if not conexao.execute(text("SELECT count(*) FROM silver.dim_serie")).scalar():
                pytest.skip("Dimensões não carregadas; rode python -m brasil_em_dados.load dimensoes")
            yield conexao
        finally:
            transacao.rollback()


@pytest.fixture
def preparadas(conexao):
    return fato.preparar_fato(conexao)


@pytest.fixture
def carregada(conexao, preparadas) -> Connection:
    linhas = [l for _, ls in preparadas for l in ls]
    aplicar_upsert(conexao, fato.FATO, linhas)
    return conexao


def _linhas(preparadas) -> list[dict]:
    return [l for _, ls in preparadas for l in ls]


def _valor(conexao: Connection, sql: str, **parametros):
    return conexao.execute(text(sql), parametros).scalar()


def test_preparacao_tem_as_contagens_por_serie(preparadas):
    assert {s.cod_serie: len(ls) for s, ls in preparadas} == POR_SERIE
    assert sum(POR_SERIE.values()) == TOTAL_ESPERADO


def test_segunda_carga_nao_muda_nada(carregada):
    resumos = fato.carregar_fato(carregada)
    assert {r.tabela.removeprefix("fato "): r.inalteradas for r in resumos} == POR_SERIE
    assert all((r.inseridas, r.atualizadas) == (0, 0) for r in resumos)


def test_nulos_so_nos_municipios_novos_antes_de_2013(carregada):
    nulos = carregada.execute(text(
        "SELECT cod_municipio, ano, sinal_origem FROM silver.fato_indicador_municipio "
        "WHERE valor IS NULL")).all()
    assert len(nulos) == 14
    assert {m for m, _, _ in nulos} == {"4212650", "4220000"}
    assert all(ano < 2013 and sinal is not None for _, ano, sinal in nulos)


def test_valor_revisado_e_atualizado_e_registrado(carregada, preparadas, caplog):
    linhas = copy.deepcopy(_linhas(preparadas))
    alvo = next(l for l in linhas if l["cod_serie"] == "sidra_5938_v37"
                and l["cod_municipio"] == "4205407" and l["ano"] == 2021)
    antigo = alvo["valor"]
    alvo["valor"] = antigo + Decimal("1000.00")
    alvo["data_coleta"] = alvo["data_coleta"] + timedelta(days=1)
    with caplog.at_level(logging.INFO, logger="brasil_em_dados.load.upsert"):
        classificacao = aplicar_upsert(carregada, fato.FATO, linhas)
    assert (len(classificacao.inseridas), len(classificacao.atualizadas)) == (0, 1)
    assert f"4205407/pib_corrente/2021.valor: Decimal('{antigo}') →" in caplog.text
    gravado = carregada.execute(text(
        "SELECT valor, data_coleta FROM silver.fato_indicador_municipio "
        "WHERE cod_municipio = '4205407' AND codigo_indicador = 'pib_corrente' AND ano = 2021"
    )).one()
    assert (gravado.valor, gravado.data_coleta) == (alvo["valor"], alvo["data_coleta"])


def test_coleta_nova_com_valores_iguais_nao_reescreve_nem_muda_data_coleta(carregada, preparadas):
    # data_coleta = a coleta que trouxe o valor: sem mudança de valor/sinal, fica a antiga.
    linhas = copy.deepcopy(_linhas(preparadas))
    for linha in linhas:
        linha["data_coleta"] = linha["data_coleta"] + timedelta(days=7)
    antes = _valor(carregada, "SELECT max(data_coleta) FROM silver.fato_indicador_municipio")
    classificacao = aplicar_upsert(carregada, fato.FATO, linhas)
    assert (len(classificacao.inseridas), len(classificacao.atualizadas)) == (0, 0)
    assert _valor(carregada, "SELECT max(data_coleta) FROM silver.fato_indicador_municipio") == antes


def test_troca_de_serie_numa_linha_existente_e_recusada(carregada, preparadas):
    linhas = copy.deepcopy(_linhas(preparadas))
    alvo = next(l for l in linhas if l["cod_serie"] == "sidra_4709_v93")
    alvo["cod_serie"] = "sidra_1378_v93"
    with pytest.raises(ErroCarga, match="cod_serie: 'sidra_4709_v93' → 'sidra_1378_v93'"):
        aplicar_upsert(carregada, fato.FATO, linhas)


def test_linha_so_no_banco_e_mantida(carregada, preparadas):
    linhas = [l for l in _linhas(preparadas) if l["cod_serie"] != "sidra_4709_v93"]
    classificacao = aplicar_upsert(carregada, fato.FATO, linhas)
    assert len(classificacao.so_no_banco) == POR_SERIE["sidra_4709_v93"]
    assert _valor(carregada, "SELECT count(*) FROM silver.fato_indicador_municipio "
                             "WHERE cod_serie = 'sidra_4709_v93'") == 295


def test_controle_carrega_uma_vez_e_recusa_execucao_alterada(conexao, tmp_path):
    if not ARQUIVO_CONTROLE.exists():
        pytest.skip("Sem data/controle/execucoes.jsonl")
    primeira = controle.carregar_controle(conexao)
    segunda = controle.carregar_controle(conexao)
    assert (segunda.inseridas, segunda.atualizadas) == (0, 0)
    assert segunda.inalteradas == primeira.na_fonte
    # Altera a contagem da primeira execução com sucesso, qualquer que seja a ordem do arquivo.
    registros = [json.loads(l) for l in ARQUIVO_CONTROLE.read_text(encoding="utf-8").splitlines()]
    alvo = next(r for r in registros if r["status"] == "sucesso")
    original = alvo["n_registros"]
    alvo["n_registros"] = original - 1
    alterado = tmp_path / "execucoes.jsonl"
    alterado.write_text("".join(json.dumps(r) + "\n" for r in registros), encoding="utf-8")
    with pytest.raises(ErroCarga, match=f"n_registros: {original} → {original - 1}"):
        controle.carregar_controle(conexao, alterado)
