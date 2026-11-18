"""Testes unitários do aplicador de DDL (sem banco)."""

import re
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from brasil_em_dados.config import PASTA_DDL
from brasil_em_dados.db import aplicar_ddl as modulo
from brasil_em_dados.db.aplicar_ddl import (
    ErroDDL,
    Registro,
    Script,
    calcular_sha256,
    executar_scripts,
    ler_scripts,
    planejar,
)


def _criar(pasta, nomes_e_sql: dict[str, str]):
    for nome, sql in nomes_e_sql.items():
        (pasta / nome).write_text(sql, encoding="utf-8")
    return pasta


def _script(nome: str, sql: str = "SELECT 1;") -> Script:
    return Script(Path(nome), sql)


def _registro(script: Script) -> Registro:
    return Registro(script.sha256, "2026-11-17 12:00:00+00")


# --- ler_scripts ------------------------------------------------------------------------------

def test_le_em_ordem_numerica_e_ignora_o_script_de_superusuario(tmp_path):
    _criar(tmp_path, {"02_b.sql": "SELECT 2;", "00_banco.sql": "\\connect x", "01_a.sql": "SELECT 1;",
                      "10_c.sql": "SELECT 10;"})
    assert [s.nome for s in ler_scripts(tmp_path)] == ["01_a.sql", "02_b.sql", "10_c.sql"]


@pytest.mark.parametrize("nome", ["1_a.sql", "01-a.sql", "01_A.sql", "a_01.sql", "01_.sql"])
def test_nome_fora_do_padrao_falha(tmp_path, nome):
    _criar(tmp_path, {nome: "SELECT 1;"})
    with pytest.raises(ErroDDL, match="fora do padrão"):
        ler_scripts(tmp_path)


def test_numero_repetido_falha(tmp_path):
    _criar(tmp_path, {"01_a.sql": "SELECT 1;", "01_b.sql": "SELECT 1;"})
    with pytest.raises(ErroDDL, match="Número repetido"):
        ler_scripts(tmp_path)


def test_comando_do_psql_falha(tmp_path):
    _criar(tmp_path, {"01_a.sql": "SELECT 1;\n  \\set ON_ERROR_STOP on\n"})
    with pytest.raises(ErroDDL, match="01_a.sql: comando do psql"):
        ler_scripts(tmp_path)


def test_barra_invertida_dentro_de_comentario_nao_e_comando_do_psql(tmp_path):
    _criar(tmp_path, {"01_a.sql": "-- sem comandos do psql (\\set)\nSELECT 1;"})
    assert len(ler_scripts(tmp_path)) == 1


@pytest.mark.parametrize("sql, comando", [
    ("CREATE TABLE t (x int);\nCOMMIT;", "COMMIT"),
    ("BEGIN;\nCREATE TABLE t (x int);", "BEGIN"),
    ("CREATE TABLE t (x int); rollback;", "ROLLBACK"),
    ("START TRANSACTION;\nSELECT 1;", "START TRANSACTION"),
    ("SELECT 1;\n  savepoint s1;", "SAVEPOINT"),
    ("SELECT 1;\nEND;", "END"),
])
def test_comando_de_transacao_falha(tmp_path, sql, comando):
    _criar(tmp_path, {"01_a.sql": sql})
    with pytest.raises(ErroDDL, match=f"comando de transação \\({comando}\\)"):
        ler_scripts(tmp_path)


@pytest.mark.parametrize("sql", [
    "DO $$\nBEGIN\n    IF true THEN NULL; END IF;\nEND\n$$;",
    "DO $corpo$ BEGIN PERFORM 1; END $corpo$;",
    "-- COMMIT só no comentário\nSELECT 1;",
    "COMMENT ON TABLE t IS 'texto';",
])
def test_begin_e_end_de_bloco_do_ou_de_comentario_sao_permitidos(tmp_path, sql):
    _criar(tmp_path, {"01_a.sql": sql})
    assert len(ler_scripts(tmp_path)) == 1


def test_arquivo_vazio_falha(tmp_path):
    _criar(tmp_path, {"01_a.sql": "  \n"})
    with pytest.raises(ErroDDL, match="vazio"):
        ler_scripts(tmp_path)


def test_pasta_sem_scripts_falha(tmp_path):
    _criar(tmp_path, {"00_banco.sql": "SELECT 1;"})
    with pytest.raises(ErroDDL, match="Nenhum script"):
        ler_scripts(tmp_path)


# --- sha256 -----------------------------------------------------------------------------------

def test_sha256_ignora_diferenca_de_quebra_de_linha():
    # O Git troca CRLF por LF; o mesmo arquivo não pode parecer "editado" em outra máquina.
    assert calcular_sha256("SELECT 1;\r\nSELECT 2;\r\n") == calcular_sha256("SELECT 1;\nSELECT 2;\n")


def test_sha256_muda_quando_o_conteudo_muda():
    assert calcular_sha256("SELECT 1;") != calcular_sha256("SELECT 2;")
    assert re.fullmatch(r"[0-9a-f]{64}", calcular_sha256("SELECT 1;"))


# --- planejar ---------------------------------------------------------------------------------

def test_sem_registro_aplica_todos_em_ordem():
    scripts = [_script("01_a.sql"), _script("02_b.sql")]
    assert planejar(scripts, {}) == scripts


def test_registrados_com_mesmo_conteudo_nao_sao_reaplicados():
    a, b = _script("01_a.sql"), _script("02_b.sql", "SELECT 2;")
    assert planejar([a, b], {a.nome: _registro(a), b.nome: _registro(b)}) == []


def test_so_o_arquivo_novo_e_aplicado():
    a, b = _script("01_a.sql"), _script("02_b.sql", "SELECT 2;")
    assert planejar([a, b], {a.nome: _registro(a)}) == [b]


def test_arquivo_aplicado_e_editado_falha_sugerindo_arquivo_novo():
    original = _script("01_a.sql", "CREATE TABLE t (x int);")
    editado = _script("01_a.sql", "CREATE TABLE t (x int, y int);")
    with pytest.raises(ErroDDL) as erro:
        planejar([editado, _script("02_b.sql")], {original.nome: _registro(original)})
    mensagem = str(erro.value)
    assert "01_a.sql já foi aplicado em 2026-11-17" in mensagem
    assert "editado depois" in mensagem
    assert "crie um arquivo novo numerado (por exemplo, 03_descricao.sql)" in mensagem


def test_arquivo_aplicado_que_sumiu_da_pasta_falha():
    a, b = _script("01_a.sql"), _script("02_b.sql", "SELECT 2;")
    with pytest.raises(ErroDDL, match="não estão mais em sql/ddl/: 02_b.sql"):
        planejar([a], {a.nome: _registro(a), b.nome: _registro(b)})


def test_arquivo_novo_com_numero_menor_que_o_ultimo_aplicado_falha():
    a, c = _script("01_a.sql"), _script("03_c.sql", "SELECT 3;")
    novo = _script("02_b.sql", "SELECT 2;")
    with pytest.raises(ErroDDL, match="menor que o último aplicado \\(03\\): 02_b.sql"):
        planejar([a, novo, c], {a.nome: _registro(a), c.nome: _registro(c)})


# --- executar_scripts -------------------------------------------------------------------------

def test_executa_em_ordem():
    executados = []
    executar_scripts(executados.append, [_script("01_a.sql", "A;"), _script("02_b.sql", "B;")])
    assert executados == ["A;", "B;"]


def test_para_no_primeiro_erro_citando_o_arquivo():
    executados = []

    def executar(sql):
        if sql == "ERRO;":
            raise RuntimeError("syntax error")
        executados.append(sql)

    scripts = [_script("01_a.sql", "A;"), _script("02_b.sql", "ERRO;"), _script("03_c.sql", "C;")]
    with pytest.raises(ErroDDL, match="02_b.sql: syntax error"):
        executar_scripts(executar, scripts)
    assert executados == ["A;"]


# --- aplicar_ddl e main -----------------------------------------------------------------------

def _engine_falso():
    engine = MagicMock()
    contexto = engine.begin.return_value
    contexto.__enter__.return_value = MagicMock(name="conexao")
    contexto.__exit__.return_value = False  # não engole a exceção
    return engine, contexto


def test_erro_no_script_atravessa_a_transacao_e_dispara_o_rollback(tmp_path):
    _criar(tmp_path, {"01_a.sql": "SELECT 1;"})
    engine, contexto = _engine_falso()
    with patch.object(modulo, "ler_registrados", return_value={}), \
         patch.object(modulo, "_executar_no_driver", side_effect=RuntimeError("falhou")):
        with pytest.raises(ErroDDL, match="01_a.sql: falhou"):
            modulo.aplicar_ddl(engine, tmp_path)
    # engine.begin() desfaz a transação quando __exit__ recebe a exceção.
    tipo_da_excecao = contexto.__exit__.call_args.args[0]
    assert tipo_da_excecao is ErroDDL


def test_aplicar_ddl_devolve_os_aplicados(tmp_path):
    _criar(tmp_path, {"01_a.sql": "SELECT 1;", "02_b.sql": "SELECT 2;"})
    engine, _ = _engine_falso()
    with patch.object(modulo, "ler_registrados", return_value={}), \
         patch.object(modulo, "_executar_no_driver"):
        assert modulo.aplicar_ddl(engine, tmp_path) == ["01_a.sql", "02_b.sql"]


def test_main_devolve_1_e_nao_usa_o_banco_se_os_scripts_forem_invalidos(tmp_path):
    _criar(tmp_path, {"01_a.sql": "\\connect x"})
    engine = Mock()
    with patch.object(modulo, "configurar_logging"):
        assert modulo.main(["--pasta", str(tmp_path)], engine=engine) == 1
    engine.begin.assert_not_called()
    engine.dispose.assert_called_once()


@pytest.mark.parametrize("aplicados, texto", [
    (["01_a.sql"], "DDL aplicado: 01_a.sql"),
    ([], "Nada a aplicar"),
])
def test_main_devolve_0_em_sucesso(caplog, aplicados, texto):
    engine = Mock()
    with patch.object(modulo, "configurar_logging"), \
         patch.object(modulo, "aplicar_ddl", return_value=aplicados), \
         caplog.at_level("INFO", logger=modulo.logger.name):
        assert modulo.main([], engine=engine) == 0
    assert texto in caplog.text
    engine.dispose.assert_called_once()


def test_logger_fica_na_hierarquia_do_projeto_mesmo_rodando_como_main():
    # Com `python -m`, __name__ é "__main__"; o logger precisa de nome fixo.
    assert modulo.logger.name.startswith("brasil_em_dados.")


# --- scripts reais do projeto -----------------------------------------------------------------

def test_scripts_do_projeto_sao_lidos_pelo_aplicador():
    nomes = [s.nome for s in ler_scripts(PASTA_DDL)]
    assert nomes == ["01_schemas.sql", "02_dimensoes.sql", "03_fato_e_controle.sql",
                     "04_comentario_data_coleta.sql"]


def test_scripts_do_projeto_so_criam_com_if_not_exists():
    # Defesa extra além do registro em public.ddl_aplicado.
    criacao = re.compile(r"\bCREATE\s+(?:TABLE|SCHEMA|INDEX|VIEW)\b(?!\s+IF\s+NOT\s+EXISTS)", re.I)
    for script in ler_scripts(PASTA_DDL):
        sem_comentarios = re.sub(r"--[^\n]*", "", script.sql)
        assert not criacao.search(sem_comentarios), f"{script.nome} sem IF NOT EXISTS"
