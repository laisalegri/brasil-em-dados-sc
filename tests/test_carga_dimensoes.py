"""Testes da carga das dimensões sem banco: leitura da RAW, SQL do upsert, resumo e CLI."""

import copy
import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from brasil_em_dados.config import RAIZ_PROJETO
from brasil_em_dados.extract import catalogo, raw
from brasil_em_dados.extract.cliente_http import RespostaHTTP
from brasil_em_dados.load import __main__ as cli
from brasil_em_dados.load import dimensoes
from brasil_em_dados.load import upsert as modulo_upsert
from brasil_em_dados.load.dimensoes import (
    DIM_INDICADOR,
    DIM_MUNICIPIO,
    DIM_SERIE,
    ErroCarga,
    Resumo,
    classificar,
)
from brasil_em_dados.transform.dimensoes import linhas_dim_indicador, linhas_dim_serie

AMOSTRA = json.loads((RAIZ_PROJETO / "tests" / "fixtures" / "localidades_sc_amostra.json")
                     .read_text(encoding="utf-8"))
CODIGOS = [f"42{i:04d}0" for i in range(1, 294)] + ["4212650", "4220000"]


def _municipios(codigos=CODIGOS) -> list[dict]:
    """295 municípios no formato real da API, a partir da amostra."""
    modelo = AMOSTRA[0]
    lista = []
    for codigo in codigos:
        municipio = copy.deepcopy(modelo)
        municipio["id"] = int(codigo)
        lista.append(municipio)
    return lista


def _gravar_na_raw(pasta_raw, corpo: bytes, coletado_em=None):
    fonte = catalogo.obter("ibge_localidades_sc")
    return raw.gravar_coleta(fonte, RespostaHTTP(fonte.url_extrator, 200, corpo, 1, 1), 295,
                             pasta_raw=pasta_raw,
                             coletado_em=coletado_em or datetime.now(timezone.utc), versao="t")


# --- leitura da RAW ---------------------------------------------------------------------------

def test_le_a_ultima_coleta_valida_da_raw(tmp_path):
    _gravar_na_raw(tmp_path, json.dumps(_municipios()).encode(),
                   datetime(2026, 11, 1, tzinfo=timezone.utc))
    meta = _gravar_na_raw(tmp_path, json.dumps(_municipios()[::-1]).encode(),
                          datetime(2026, 11, 2, tzinfo=timezone.utc))
    municipios, arquivo = dimensoes.ler_municipios_da_raw(tmp_path)
    assert arquivo.name == meta["arquivo_dados"]
    assert municipios[0]["id"] == 4220000  # a mais recente veio invertida


def test_sem_coleta_na_raw_falha_com_mensagem_clara(tmp_path):
    with pytest.raises(ErroCarga, match="Nenhuma coleta válida de ibge_localidades_sc"):
        dimensoes.ler_municipios_da_raw(tmp_path)


def test_coleta_com_294_municipios_e_revalidada_e_recusada(tmp_path):
    _gravar_na_raw(tmp_path, json.dumps(_municipios(CODIGOS[:-1])).encode())
    with pytest.raises(ErroCarga, match="esperados 295 municípios"):
        dimensoes.ler_municipios_da_raw(tmp_path)


def test_coleta_ilegivel_falha(tmp_path):
    _gravar_na_raw(tmp_path, b"<html>nao e json</html>")
    with pytest.raises(ErroCarga, match="Coleta de municípios inválida"):
        dimensoes.ler_municipios_da_raw(tmp_path)


# --- SQL do upsert e resumo -------------------------------------------------------------------

def test_sql_do_upsert_so_atualiza_quando_algo_mudou():
    sql = modulo_upsert.sql_upsert(DIM_MUNICIPIO, 2)
    assert sql.startswith("INSERT INTO silver.dim_municipio (cod_municipio, nome_municipio,")
    assert "VALUES (:cod_municipio_0, " in sql and "(:cod_municipio_1, " in sql  # lote de 2
    assert "ON CONFLICT (cod_municipio) DO UPDATE SET nome_municipio = EXCLUDED.nome_municipio" in sql
    assert "cod_municipio = EXCLUDED.cod_municipio" not in sql  # a chave não é atualizada
    assert "IS DISTINCT FROM" in sql
    assert "DELETE" not in sql.upper()


def test_resumo_em_texto():
    assert Resumo("silver.dim_serie", 1, 2, 3).texto() == (
        "silver.dim_serie: 1 inseridas, 2 atualizadas, 3 inalteradas (6 na fonte)")
    assert "1 só no banco (mantidas)" in Resumo("t", 0, 0, 5, so_no_banco=1).texto()


# --- CLI --------------------------------------------------------------------------------------

def test_cli_com_sucesso_devolve_0_e_registra_o_resumo(caplog):
    resumos = [Resumo("silver.dim_indicador", 4, 0, 0)]
    engine = Mock()
    with patch.object(cli, "configurar_logging"), \
         patch.object(cli, "executar", return_value=resumos), \
         caplog.at_level("INFO", logger=cli.logger.name):
        assert cli.main(["dimensoes"], engine=engine) == 0
    assert "silver.dim_indicador: 4 inseridas" in caplog.text
    engine.dispose.assert_called_once()


def test_cli_com_erro_devolve_1(caplog):
    engine = Mock()
    with patch.object(cli, "configurar_logging"), \
         patch.object(cli, "executar", side_effect=ErroCarga("sem coleta")), \
         caplog.at_level("ERROR", logger=cli.logger.name):
        assert cli.main(["dimensoes"], engine=engine) == 1
    assert "transação desfeita. sem coleta" in caplog.text


def test_cli_recusa_alvo_desconhecido():
    with pytest.raises(SystemExit):
        cli.main(["nada"])


def test_loggers_ficam_na_hierarquia_do_projeto():
    assert cli.logger.name.startswith("brasil_em_dados.")
    assert dimensoes.logger.name.startswith("brasil_em_dados.")


# --- EspecTabela ------------------------------------------------------------------------------

@pytest.mark.parametrize("nome, colunas", [
    ("silver.dim_x; DROP TABLE y", ("a",)),
    ("dim_sem_schema", ("a",)),
    ("silver.dim_x", ("a b",)),
    ("silver.dim_x", ("A",)),
])
def test_espec_recusa_identificadores_invalidos(nome, colunas):
    with pytest.raises(ValueError, match="inválido"):
        dimensoes.EspecTabela(nome, (colunas[0],), colunas)


def test_espec_recusa_imutavel_fora_das_colunas():
    with pytest.raises(ValueError, match="entre as colunas"):
        dimensoes.EspecTabela("silver.dim_x", ("a",), ("a", "b"), imutaveis=("c",))


# --- classificar (lógica pura) ------------------------------------------------------------------

def _serie(**mudancas) -> dict:
    linha = next(l for l in linhas_dim_serie() if l["cod_serie"] == "sidra_5938_v37")
    return {**linha, **mudancas}


def _no_banco(linha: dict, **mudancas) -> dict:
    return {(linha["cod_serie"],): {**linha, **mudancas}}


def test_decimal_do_banco_igual_ao_int_do_catalogo_nao_e_mudanca():
    nova = _serie()
    resultado = classificar(DIM_SERIE, _no_banco(nova, fator_conversao=Decimal("1000")), [nova])
    assert (resultado.inseridas, resultado.atualizadas) == ([], {})
    assert len(resultado.inalteradas) == 1


def test_linha_nova_e_inserida_e_linha_so_no_banco_e_listada():
    nova = _serie()
    antiga = _serie(cod_serie="sidra_antiga")
    resultado = classificar(DIM_SERIE, _no_banco(antiga), [nova])
    assert resultado.inseridas == [("sidra_5938_v37",)]
    assert list(resultado.so_no_banco) == [("sidra_antiga",)]


@pytest.mark.parametrize("coluna, antigo", [
    ("url_extrator", "https://apisidra.ibge.gov.br/antiga"),
    ("data_referencia", "outra"),
])
def test_campo_descritivo_da_serie_pode_ser_atualizado(coluna, antigo):
    nova = _serie()
    resultado = classificar(DIM_SERIE, _no_banco(nova, **{coluna: antigo}), [nova])
    assert list(resultado.atualizadas) == [("sidra_5938_v37",)]
    assert resultado.proibidas == []


@pytest.mark.parametrize("coluna, antigo", [
    ("fator_conversao", Decimal("1")),
    ("unidade_origem", "Reais"),
    ("codigo_indicador", "pib_per_capita"),
])
def test_mudanca_que_altera_o_sentido_da_serie_e_proibida(coluna, antigo):
    nova = _serie()
    resultado = classificar(DIM_SERIE, _no_banco(nova, **{coluna: antigo}), [nova])
    assert [m.coluna for m in resultado.proibidas] == [coluna]


@pytest.mark.parametrize("coluna, permitida", [
    ("tipo_medida", False), ("unidade_armazenada", False), ("nome", True), ("descricao", True),
])
def test_imutaveis_do_indicador(coluna, permitida):
    nova = linhas_dim_indicador()[0]
    no_banco = {(nova["codigo_indicador"],): {**nova, coluna: "valor antigo"}}
    resultado = classificar(DIM_INDICADOR, no_banco, [nova])
    assert (resultado.proibidas == []) is permitida


def test_mensagem_da_mudanca_proibida_mostra_antigo_novo_e_orienta():
    nova = _serie()
    proibidas = classificar(DIM_SERIE, _no_banco(nova, fator_conversao=Decimal("1")),
                            [nova]).proibidas
    mensagem = str(dimensoes.erro_mudanca_proibida(DIM_SERIE, proibidas))
    assert "sidra_5938_v37.fator_conversao: Decimal('1') → 1000" in mensagem
    assert "crie um novo cod_serie no catálogo" in mensagem


# --- upsert sem banco: contagem divergente ------------------------------------------------------

def _conexao_falsa(no_banco: dict, retornos_por_execucao: list[list]):
    conexao = MagicMock()
    resultados = iter(retornos_por_execucao)

    def execute(sql, parametros=None):
        resultado = MagicMock()
        if parametros is not None:  # o INSERT do upsert
            resultado.all.return_value = [SimpleNamespace(cod_serie="sidra_5938_v37", inserida=x)
                                          for x in next(resultados)]
        return resultado

    conexao.execute.side_effect = execute
    return conexao, patch.object(modulo_upsert, "linhas_no_banco", return_value=no_banco)


def test_contagem_divergente_do_banco_e_erro():
    nova = _serie()
    # A comparação espera 1 inserida, mas o banco "não gravou" nada.
    conexao, ler = _conexao_falsa({}, [[]])
    with ler, pytest.raises(ErroCarga, match="contagem divergente"):
        dimensoes.upsert(conexao, DIM_SERIE, [nova])


def test_banco_reporta_atualizada_onde_se_esperava_inserida_e_erro():
    conexao, ler = _conexao_falsa({}, [[False]])
    with ler, pytest.raises(ErroCarga, match="0 inseridas e 1 atualizadas; esperado: 1 e 0"):
        dimensoes.upsert(conexao, DIM_SERIE, [_serie()])


def test_mudanca_proibida_nao_chega_a_gravar():
    nova = _serie()
    conexao, ler = _conexao_falsa(_no_banco(nova, unidade_origem="Reais"), [])
    with ler, pytest.raises(ErroCarga, match="mudança não permitida"):
        dimensoes.upsert(conexao, DIM_SERIE, [nova])
    gravacoes = [c for c in conexao.execute.call_args_list if len(c.args) > 1]
    assert gravacoes == []
