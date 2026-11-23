"""Testes das consultas da análise: catálogo em sql/analise/ e leitura só da GOLD."""

from unittest.mock import Mock

import pytest
from sqlalchemy import text

from brasil_em_dados import db
from brasil_em_dados.analise import consultas
from brasil_em_dados.config import PASTA_CONSULTAS_ANALISE
from tests.apoio_banco import BLOQUEIOS_READONLY, sqlstate_em_savepoint

ARQUIVOS = sorted(p.stem for p in PASTA_CONSULTAS_ANALISE.glob("*.sql"))


@pytest.mark.parametrize("nome", ARQUIVOS)
def test_cada_consulta_le_so_a_gold(nome):
    sql = consultas.ler_sql(nome)
    assert "silver." not in sql.lower() and "public." not in sql.lower()


@pytest.mark.parametrize("nome", ["../ddl/00_banco_e_usuarios", "Painel", "x y", ""])
def test_nome_fora_do_padrao_e_recusado(nome):
    with pytest.raises(consultas.ErroConsulta, match="inválido"):
        consultas.ler_sql(nome)


def test_consulta_inexistente_e_recusada():
    with pytest.raises(consultas.ErroConsulta, match="inexistente"):
        consultas.ler_sql("nao_existe")


@pytest.mark.parametrize("sql", [
    "SELECT * FROM silver.fato_indicador_municipio",
    "SELECT * FROM gold.painel_municipio_ano JOIN silver.dim_serie USING (x)",
    "SELECT 1",
])
def test_sql_fora_da_gold_e_recusado(tmp_path, sql):
    (tmp_path / "x.sql").write_text(sql, encoding="utf-8")
    with pytest.raises(consultas.ErroConsulta, match="schema gold"):
        consultas.ler_sql("x", tmp_path)


@pytest.mark.parametrize("chamada", [
    lambda e: consultas.participacao(e, "pib_per_capita", 2023),
    lambda e: consultas.agregado(e, "pais", "pop_censo"),
    lambda e: consultas.agregado(e, "estado", "pib_per_capita"),
    lambda e: consultas.variacao_anual(e, "pop_censo"),
])
def test_parametro_invalido_falha_antes_de_tocar_no_banco(chamada):
    engine = Mock()
    with pytest.raises(consultas.ErroConsulta):
        chamada(engine)
    engine.connect.assert_not_called()


# -- integração (bed_readonly) -------------------------------------------------------------------

@pytest.mark.integracao
def test_transacao_da_analise_e_somente_leitura(engine_readonly):
    ambiente = db.ler_ambiente()
    with db.transacao_somente_leitura(engine_readonly) as conexao:
        assert conexao.execute(text("SELECT current_user")).scalar() == ambiente["PG_READONLY_USER"]
        assert conexao.execute(text("SHOW transaction_read_only")).scalar() == "on"
        estado = sqlstate_em_savepoint(conexao, lambda: conexao.execute(
            text("CREATE TEMP TABLE analise_nao_pode (a int)")))
    assert estado in BLOQUEIOS_READONLY


@pytest.mark.integracao
def test_consultas_devolvem_os_totais_oficiais(engine_readonly):
    censo = consultas.agregado(engine_readonly, "estado", "pop_censo").set_index("ano")["valor"]
    assert censo[2010] == 6_248_436 and censo[2022] == 7_610_361  # totais oficiais de SC
    part = consultas.participacao(engine_readonly, "pop_censo", 2022)
    assert len(part) == 295 and part["participacao_percentual"].sum() == pytest.approx(100, abs=0.01)
    assert len(consultas.variacao_censo(engine_readonly)) == 295
    assert len(consultas.painel(engine_readonly, 2023)) == 295
    pib = consultas.variacao_anual(engine_readonly, "pib_corrente")
    assert set(pib["tipo_medida"]) == {"nominal"}


@pytest.mark.parametrize("sql", [
    "SELECT * FROM fato_indicador_municipio",
    "SELECT * FROM gold.painel_municipio_ano p JOIN dim_serie s USING (cod_serie)",
])
def test_tabela_sem_schema_e_recusada(tmp_path, sql):
    (tmp_path / "x.sql").write_text(sql, encoding="utf-8")
    with pytest.raises(consultas.ErroConsulta, match="sem schema"):
        consultas.ler_sql("x", tmp_path)


def test_cte_e_subconsulta_sao_aceitas(tmp_path):
    sql = ("WITH base AS (SELECT * FROM gold.painel_municipio_ano), outra AS (SELECT 1 AS a) "
           "SELECT * FROM base JOIN outra ON true JOIN (SELECT 1) t ON true")
    (tmp_path / "x.sql").write_text(sql, encoding="utf-8")
    assert consultas.ler_sql("x", tmp_path) == sql
