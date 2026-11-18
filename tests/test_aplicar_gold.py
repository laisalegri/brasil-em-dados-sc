"""Testes unitários do aplicador da GOLD (sem banco)."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from brasil_em_dados.config import PASTA_GOLD
from brasil_em_dados.db import aplicar_gold as modulo
from brasil_em_dados.db.aplicar_ddl import ErroDDL, Script, ler_scripts
from brasil_em_dados.db.aplicar_gold import views_do_script, views_em_ordem

VIEW = "CREATE VIEW gold.x AS SELECT 1 AS a;\nCOMMENT ON VIEW gold.x IS 'texto; com ponto e vírgula';"


def _script(sql: str, nome: str = "01_x.sql") -> Script:
    return Script(Path(nome), sql)


def test_le_as_views_do_script_na_ordem():
    sql = VIEW + "\nCREATE VIEW gold.y AS SELECT * FROM gold.x;"
    assert views_do_script(_script(sql)) == ["gold.x", "gold.y"]


def test_ponto_e_virgula_dentro_de_literal_ou_comentario_nao_quebra_a_leitura():
    sql = "-- comentário; com ponto e vírgula\n" + VIEW
    assert views_do_script(_script(sql)) == ["gold.x"]


@pytest.mark.parametrize("comando", [
    "CREATE TABLE gold.t (a int)",
    "INSERT INTO silver.dim_indicador VALUES ('x')",
    "DROP VIEW gold.x",
    "ALTER VIEW gold.x RENAME TO y",
    "GRANT SELECT ON gold.x TO PUBLIC",
    "CREATE OR REPLACE VIEW gold.x AS SELECT 2",
    "DELETE FROM silver.fato_indicador_municipio",
])
def test_so_create_view_e_comment_sao_permitidos(comando):
    with pytest.raises(ErroDDL, match="só CREATE VIEW gold.<nome> AS e COMMENT ON"):
        views_do_script(_script(VIEW + "\n" + comando + ";"))


def test_arquivo_sem_view_gold_falha():
    with pytest.raises(ErroDDL, match="nenhum CREATE VIEW gold"):
        views_do_script(_script("COMMENT ON VIEW gold.x IS 'x';"))


@pytest.mark.parametrize("sql, motivo", [
    # Casos da revisão do D30: o texto validado não pode ser diferente do executado.
    ("-- $$\nDROP TABLE silver.fato_indicador_municipio;\n-- $$\n" + VIEW, "DROP"),
    ("CREATE VIEW gold.x AS SELECT 1 /* ' */; DROP TABLE t; /* ' */;", "comentário de bloco"),
    ("COMMENT ON VIEW gold.x IS 'a -- b';\nDROP TABLE t;\n" + VIEW, "dentro de literal"),
    ("CREATE VIEW gold.x AS SELECT $q$;$q$ AS a;", "'\\$' fora de literal"),
    ("CREATE VIEW gold.x AS SELECT 'aberto;", "sem aspa de fechamento"),
], ids=["dolar-em-comentario", "bloco", "traco-em-literal", "dolar", "literal-aberto"])
def test_brechas_de_leitura_sao_recusadas(sql, motivo):
    with pytest.raises(ErroDDL, match=motivo):
        views_do_script(_script(sql))


@pytest.mark.parametrize("comando", [
    "CREATE VIEW silver.x AS SELECT 1",
    "CREATE VIEW x AS SELECT 1",
    'CREATE VIEW gold."X" AS SELECT 1',
    "CREATE VIEW gold.y (a) AS SELECT 1",
    "COMMENT ON TABLE silver.fato_indicador_municipio IS ''",
    "COMMENT ON COLUMN silver.fato_indicador_municipio.valor IS ''",
])
def test_comandos_fora_da_gold_sao_recusados(comando):
    with pytest.raises(ErroDDL, match="só CREATE VIEW gold"):
        views_do_script(_script(VIEW + "\n" + comando + ";"))


def test_comentario_sobre_view_de_outro_arquivo_e_recusado():
    with pytest.raises(ErroDDL, match="não é criada neste arquivo"):
        views_do_script(_script(VIEW + "\nCOMMENT ON VIEW gold.outra IS 'x';"))


def test_comentario_em_coluna_da_propria_view_e_aceito():
    assert views_do_script(_script(VIEW + "\nCOMMENT ON COLUMN gold.x.a IS 'x' 'y';")) == ["gold.x"]


def test_arquivo_00_na_pasta_gold_e_recusado(tmp_path):
    (tmp_path / "00_x.sql").write_text(VIEW, encoding="utf-8")
    (tmp_path / "01_x.sql").write_text(VIEW, encoding="utf-8")
    with pytest.raises(ErroDDL, match="00_\\*.sql não são permitidos"):
        modulo.aplicar_gold(Mock(), tmp_path)


def test_drop_em_ordem_inversa_e_sem_cascade():
    conexao = MagicMock()
    scripts = [_script(VIEW, "01_a.sql"),
               _script("CREATE VIEW gold.y AS SELECT * FROM gold.x;", "02_b.sql")]
    with patch.object(modulo, "_executar_no_driver") as executar, \
         patch.object(modulo, "_views_so_no_banco", return_value=[]):
        modulo.recriar_em_conexao(conexao, scripts)
    drops = [str(c.args[0]) for c in conexao.execute.call_args_list]
    assert drops == ["DROP VIEW IF EXISTS gold.y", "DROP VIEW IF EXISTS gold.x"]
    assert not any("CASCADE" in d.upper() for d in drops)
    assert [c.args[1] for c in executar.call_args_list] == [s.sql for s in scripts]


def test_view_repetida_em_dois_arquivos_falha():
    with pytest.raises(ErroDDL, match="mais de um arquivo"):
        views_em_ordem([_script(VIEW, "01_a.sql"), _script(VIEW, "02_b.sql")])


def test_views_do_projeto_na_ordem_de_dependencia():
    assert views_em_ordem(ler_scripts(PASTA_GOLD)) == [
        "gold.dim_municipio",
        "gold.grade_indicador_municipio_ano",
        "gold.painel_municipio_ano",
        "gold.variacao_populacao_censo",
        "gold.variacao_anual",
        "gold.agregado_regiao_ano",
        "gold.participacao_estadual",
    ]


def test_main_devolve_1_sem_usar_o_banco_se_um_script_for_invalido(tmp_path):
    (tmp_path / "01_x.sql").write_text("DROP VIEW gold.x;", encoding="utf-8")
    engine = Mock()
    with patch.object(modulo, "configurar_logging"):
        assert modulo.main(["--pasta", str(tmp_path)], engine=engine) == 1
    engine.begin.assert_not_called()
    engine.dispose.assert_called_once()


def test_logger_fica_na_hierarquia_do_projeto():
    assert modulo.logger.name.startswith("brasil_em_dados.")
