"""Testes unitários do upsert em lote compartilhado (sem banco)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from brasil_em_dados.load import upsert as modulo
from brasil_em_dados.load.fato import FATO
from brasil_em_dados.load.upsert import ErroCarga, EspecTabela, classificar, sql_upsert

COLETA = datetime(2026, 11, 14, 23, 38, tzinfo=timezone.utc)


def _fato(municipio="4205407", ano=2021, valor="23559947000.00", sinal=None,
          serie="sidra_5938_v37", data_coleta=COLETA) -> dict:
    return {"cod_municipio": municipio, "codigo_indicador": "pib_corrente", "ano": ano,
            "cod_serie": serie, "valor": None if valor is None else Decimal(valor),
            "sinal_origem": sinal, "data_coleta": data_coleta}


def _chave(linha: dict) -> tuple:
    return (linha["cod_municipio"], linha["codigo_indicador"], linha["ano"])


def _banco(*linhas: dict) -> dict:
    return {_chave(l): l for l in linhas}


# --- classificar: fato ------------------------------------------------------------------------

def test_chaves_repetidas_na_fonte_sao_erro():
    with pytest.raises(ErroCarga, match="chaves repetidas"):
        classificar(FATO, {}, [_fato(), _fato(valor="1.00")])


def test_so_data_coleta_diferente_e_linha_inalterada():
    # data_coleta = "a coleta que trouxe este valor": coleta nova com o mesmo valor não muda nada.
    nova = _fato(data_coleta=COLETA + timedelta(days=7))
    resultado = classificar(FATO, _banco(_fato()), [nova])
    assert (resultado.inseridas, resultado.atualizadas) == ([], {})
    assert resultado.inalteradas == [_chave(nova)]


@pytest.mark.parametrize("mudanca", [{"valor": "23559948000.00"},
                                     {"valor": None, "sinal": "..."}],
                         ids=["valor-revisado", "valor-virou-sinal"])
def test_valor_ou_sinal_diferente_e_linha_atualizada(mudanca):
    nova = _fato(**mudanca)
    resultado = classificar(FATO, _banco(_fato()), [nova])
    assert list(resultado.atualizadas) == [_chave(nova)]
    assert resultado.proibidas == []


def test_troca_de_serie_com_valor_igual_e_proibida():
    nova = _fato(serie="pesquisas_38_i47001")
    resultado = classificar(FATO, _banco(_fato()), [nova])
    assert [m.coluna for m in resultado.proibidas] == ["cod_serie"]
    assert resultado.atualizadas == {}  # valor e sinal iguais: não conta como atualização


# --- SQL --------------------------------------------------------------------------------------

def test_sql_da_fato_compara_valor_e_sinal_e_grava_data_coleta():
    sql = sql_upsert(FATO, 1)
    assert ("WHERE ROW(silver.fato_indicador_municipio.valor, "
            "silver.fato_indicador_municipio.sinal_origem) IS DISTINCT FROM "
            "ROW(EXCLUDED.valor, EXCLUDED.sinal_origem)") in sql
    assert "data_coleta = EXCLUDED.data_coleta" in sql
    assert "RETURNING cod_municipio, codigo_indicador, ano, (xmax = 0) AS inserida" in sql


def test_tamanho_do_lote_respeita_o_limite_de_parametros():
    assert modulo.tamanho_lote(FATO) == modulo.TAMANHO_LOTE
    larga = EspecTabela("silver.larga", ("c0",), tuple(f"c{i}" for i in range(200)))
    assert modulo.tamanho_lote(larga) * 200 <= modulo.MAX_PARAMETROS


# --- aplicar_upsert com conexão falsa ---------------------------------------------------------

def _conexao_falsa(no_banco: dict, gravar):
    """Conexão que devolve, para cada INSERT, as chaves dos parâmetros como inseridas."""
    conexao = MagicMock()
    inserts = []

    def execute(sql, parametros=None):
        resultado = MagicMock()
        if parametros is not None:
            n = len([k for k in parametros if k.startswith("cod_municipio_")])
            inserts.append(n)
            chaves = [(parametros[f"cod_municipio_{i}"], parametros[f"codigo_indicador_{i}"],
                       parametros[f"ano_{i}"]) for i in range(n)]
            resultado.all.return_value = [
                SimpleNamespace(cod_municipio=c[0], codigo_indicador=c[1], ano=c[2],
                                inserida=gravar(c)) for c in chaves]
        return resultado

    conexao.execute.side_effect = execute
    return conexao, inserts, patch.object(modulo, "linhas_no_banco", return_value=no_banco)


def test_varios_lotes_e_soma_dos_retornos():
    linhas = [_fato(ano=a, municipio=f"42{m:05d}") for a in (2020, 2021) for m in range(5)]
    conexao, inserts, ler = _conexao_falsa({}, gravar=lambda chave: True)
    with ler, patch.object(modulo, "TAMANHO_LOTE", 4):
        classificacao = modulo.aplicar_upsert(conexao, FATO, linhas)
    assert inserts == [4, 4, 2]
    assert len(classificacao.inseridas) == 10


def test_linhas_inalteradas_nao_vao_ao_insert():
    iguais = [_fato(ano=a) for a in (2019, 2020)]
    nova = _fato(ano=2021, valor="1.00")
    conexao, inserts, ler = _conexao_falsa(_banco(*iguais), gravar=lambda chave: True)
    with ler:
        classificacao = modulo.aplicar_upsert(conexao, FATO, [*iguais, nova])
    assert inserts == [1]  # só a nova; as iguais não gastam sequência nem ida ao banco
    assert len(classificacao.inalteradas) == 2


def test_nada_a_gravar_nao_executa_insert():
    conexao, inserts, ler = _conexao_falsa(_banco(_fato()), gravar=lambda chave: True)
    with ler:
        modulo.aplicar_upsert(conexao, FATO, [_fato()])
    assert inserts == []


def test_banco_devolve_chave_diferente_da_prevista_e_erro():
    # Mesma contagem, chaves trocadas: a conferência é por chave, não só por número.
    conexao, _, ler = _conexao_falsa({}, gravar=lambda chave: chave[2] != 2021)
    with ler, pytest.raises(ErroCarga, match="divergente"):
        modulo.aplicar_upsert(conexao, FATO, [_fato(ano=2020), _fato(ano=2021)])
