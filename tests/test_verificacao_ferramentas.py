"""Testes unitários das ferramentas do agente (sem banco)."""

import asyncio

import pytest

from brasil_em_dados.config import PASTA_CONSULTAS_VERIFICACAO
from brasil_em_dados.verificacao.executor import CARGA, PYTEST, ResultadoPasso
from brasil_em_dados.verificacao.ferramentas import (
    LIMITE_LINHAS,
    Contexto,
    ErroCatalogo,
    ErroFerramenta,
    criar_ferramentas,
    ler_catalogo,
    tabela_markdown,
)
from brasil_em_dados.verificacao.relatorio import caminho_relatorio, gravar
from tests.apoio_verificacao import ferramenta, resultado_ok

SENHA = "senha-de-teste-xyz"


def _contexto(tmp_path, resultados=None, engine=None) -> Contexto:
    return Contexto("20261120T120000", resultados or [], ler_catalogo(PASTA_CONSULTAS_VERIFICACAO),
                    tmp_path, engine, [SENHA])


# -- catálogo fechado --------------------------------------------------------------------------

def test_catalogo_do_projeto_so_tem_consultas_de_leitura():
    catalogo = ler_catalogo(PASTA_CONSULTAS_VERIFICACAO)
    assert set(catalogo) == {"cobertura_por_ano", "nulos_fora_da_regra", "resumo_fato",
                             "series_por_indicador_ano", "status_grade_gold", "valores_negativos"}
    assert all(c.descricao and c.sql.upper().lstrip().startswith(("SELECT", "WITH"))
               for c in catalogo.values())


@pytest.mark.parametrize("nome_arquivo, sql, motivo", [
    ("x.sql", "-- d\nINSERT INTO silver.dim_indicador VALUES ('x')", "só consultas SELECT"),
    ("x.sql", "-- d\nSELECT 1; DROP TABLE silver.fato_indicador_municipio", "um único comando"),
    ("x.sql", "SELECT 1", "primeira linha deve ser um comentário"),
    ("X-1.sql", "-- d\nSELECT 1", "snake_case"),
    ("x.sql", "-- d\nUPDATE silver.dim_serie SET fonte = 'x'", "só consultas SELECT"),
])
def test_arquivo_fora_do_formato_e_recusado(tmp_path, nome_arquivo, sql, motivo):
    (tmp_path / nome_arquivo).write_text(sql, encoding="utf-8")
    with pytest.raises(ErroCatalogo, match=motivo):
        ler_catalogo(tmp_path)


def test_pasta_vazia_e_recusada(tmp_path):
    with pytest.raises(ErroCatalogo, match="Nenhuma consulta"):
        ler_catalogo(tmp_path)


def test_consulta_fora_do_catalogo_e_recusada_sem_tocar_no_banco(tmp_path):
    contexto = _contexto(tmp_path, engine=None)
    with pytest.raises(ErroFerramenta, match="Consulta desconhecida"):
        contexto.consulta_qualidade("DROP TABLE silver.fato_indicador_municipio")


def test_ferramenta_sdk_devolve_erro_para_consulta_desconhecida(tmp_path):
    ferramentas = criar_ferramentas(_contexto(tmp_path))
    resposta = asyncio.run(ferramenta(ferramentas, "consulta_qualidade").handler({"nome": "x"}))
    assert resposta["is_error"] is True
    assert "Consulta desconhecida" in resposta["content"][0]["text"]


def test_schema_da_consulta_lista_so_o_catalogo(tmp_path):
    contexto = _contexto(tmp_path)
    schema = ferramenta(criar_ferramentas(contexto), "consulta_qualidade").input_schema
    assert schema["properties"]["nome"]["enum"] == sorted(contexto.catalogo)


# -- texto devolvido ao modelo -------------------------------------------------------------------

def test_saida_do_passo_volta_sem_url_nem_senha(tmp_path):
    arquivo = tmp_path / "carga.txt"
    arquivo.write_text(f"postgresql+psycopg://bed_app:{SENHA}@localhost/b\nerro {SENHA}\n",
                       encoding="utf-8")
    contexto = _contexto(tmp_path, [resultado_ok(CARGA, arquivo)])
    texto = contexto.saida_passo("carga")
    assert "postgresql" not in texto and SENHA not in texto
    assert "usuário do banco: bed_app" in texto


def test_erro_de_ferramenta_volta_limpo(tmp_path):
    contexto = _contexto(tmp_path)

    def falha() -> str:
        raise RuntimeError(f"conexão postgresql://bed_readonly:{SENHA}@h/b recusada")

    from brasil_em_dados.verificacao.ferramentas import _resposta
    resposta = _resposta(falha, contexto)
    assert resposta["is_error"] is True
    assert SENHA not in resposta["content"][0]["text"]
    assert "postgresql" not in resposta["content"][0]["text"]


def test_sem_banco_configurado_a_ferramenta_avisa(tmp_path):
    with pytest.raises(ErroFerramenta, match="Banco não configurado"):
        _contexto(tmp_path, engine=None).controle_execucao()


def test_resultado_testes_e_passo_nao_pedido(tmp_path):
    arquivo = tmp_path / "pytest.txt"
    arquivo.write_text("\n".join(f"linha {i}" for i in range(100)) + "\n669 passed", encoding="utf-8")
    contexto = _contexto(tmp_path, [resultado_ok(PYTEST, arquivo)])
    texto = contexto.resultado_testes()
    assert "Passo pytest: ok" in texto and "669 passed" in texto and "linha 0\n" not in texto
    assert "não foi pedido" in contexto.saida_passo("gold")
    with pytest.raises(ErroFerramenta, match="resultado_testes"):
        contexto.saida_passo("pytest")


def test_passo_nao_executado_mostra_o_motivo(tmp_path):
    contexto = _contexto(tmp_path, [ResultadoPasso(CARGA, executado=False, motivo="anterior falhou")])
    assert "não executado" in contexto.saida_passo("carga")
    assert "anterior falhou" in contexto.saida_passo("carga")


def test_relatorio_anterior_pega_o_mais_recente_e_ignora_o_atual(tmp_path):
    (tmp_path / "verificacao_20261101T000000.md").write_text("antigo", encoding="utf-8")
    (tmp_path / "verificacao_20261110T000000.md").write_text(f"recente {SENHA}", encoding="utf-8")
    (tmp_path / "verificacao_20261120T120000.md").write_text("atual", encoding="utf-8")
    texto = _contexto(tmp_path).relatorio_anterior()
    assert "verificacao_20261110T000000.md" in texto and "recente" in texto
    assert SENHA not in texto


def test_sem_relatorio_anterior(tmp_path):
    assert "Não há relatório" in _contexto(tmp_path).relatorio_anterior()


def test_tabela_markdown_corta_e_avisa():
    texto = tabela_markdown(["a"], [(i,) for i in range(LIMITE_LINHAS + 5)])
    assert f"mostrando {LIMITE_LINHAS} de {LIMITE_LINHAS + 5}" in texto
    assert tabela_markdown(["a"], []) == "(nenhuma linha)"


# -- entrega e gravação do relatório -------------------------------------------------------------

def test_entregar_relatorio_guarda_na_memoria_sem_criar_arquivo(tmp_path):
    contexto = _contexto(tmp_path)
    contexto.entregar_relatorio(f"## Resumo\nTudo certo. {SENHA}")
    assert contexto.analise.startswith("## Resumo") and SENHA not in contexto.analise
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("texto", ["", "   ", "x" * 40_001])
def test_entregar_relatorio_recusa_vazio_ou_grande(tmp_path, texto):
    with pytest.raises(ErroFerramenta):
        _contexto(tmp_path).entregar_relatorio(texto)


def test_contexto_bloqueado_recusa_todas_as_ferramentas(tmp_path):
    contexto = _contexto(tmp_path)
    contexto.bloqueado = True
    for f in criar_ferramentas(contexto):
        args = {"texto": "x", "nome": "resumo_fato", "passo": "carga"}
        resposta = asyncio.run(f.handler(args))
        assert resposta["is_error"] is True, f.name
    assert contexto.analise is None


def test_relatorio_so_dentro_de_reports_e_nunca_sobrescreve(tmp_path):
    caminho = caminho_relatorio(tmp_path, "20261120T120000")
    assert caminho == tmp_path / "verificacao_20261120T120000.md"
    gravar(caminho, "primeiro")
    with pytest.raises(FileExistsError):
        gravar(caminho, "segundo")
    assert caminho.read_text(encoding="utf-8") == "primeiro"


@pytest.mark.parametrize("carimbo", ["../../src/x", "20261120", "20261120T12000a", ""])
def test_carimbo_fora_do_formato_e_recusado(tmp_path, carimbo):
    with pytest.raises(ValueError, match="Carimbo"):
        caminho_relatorio(tmp_path, carimbo)
