"""Reprodutibilidade dos notebooks de EDA (D31–D33).

Os testes estáticos olham o código das células. O de integração executa cópias dos notebooks
(nbclient, kernel python3 do .venv) numa pasta temporária, sem regravar os do repositório, e confere
que rodam sem erro e que nenhuma saída traz URL de conexão ou senha.
"""

import re
import shutil
import sys
from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient

from brasil_em_dados import db
from brasil_em_dados.config import RAIZ_PROJETO

PASTA = RAIZ_PROJETO / "notebooks"
NOTEBOOKS = ("01_populacao.ipynb", "02_pib.ipynb", "03_conclusoes.ipynb")
TIMEOUT_CELULA_S = 300

# Conversão de unidade só na carga da SILVER (regra 11): nada de multiplicar ou dividir por potências
# de 10 no notebook. Acesso ao banco só pelas funções de brasil_em_dados.analise.
PROIBIDOS_NO_CODIGO = {
    "conversão de unidade": re.compile(r"[*/]\s*(?:1e\d+|10{3,}(?:\.0*)?\b|1_000)"),
    "engine de escrita": re.compile(r"\bengine_app\b"),
    "conexão própria": re.compile(r"\bcreate_engine\b|\bpsycopg\b"),
    "SQL no notebook": re.compile(r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)\s", re.IGNORECASE),
    "pyplot": re.compile(r"\bpyplot\b|\bplt\."),
}
URL_DE_CONEXAO = re.compile(r"postgres(?:ql)?(?:\+\w+)?://", re.IGNORECASE)


def _codigo(nome: str) -> list[str]:
    nb = nbformat.read(PASTA / nome, as_version=4)
    return [c.source for c in nb.cells if c.cell_type == "code"]


def _textos_das_saidas(nb: nbformat.NotebookNode) -> str:
    partes: list[str] = []
    for celula in nb.cells:
        for saida in celula.get("outputs", []):
            partes.append(saida.get("text", ""))
            partes.extend(str(v) for k, v in saida.get("data", {}).items() if k.startswith("text/"))
            partes.append(" ".join(saida.get("traceback", [])))
    return "\n".join(partes)


@pytest.mark.parametrize("nome", NOTEBOOKS)
def test_notebook_e_fino_e_respeita_as_regras(nome):
    codigo = "\n".join(_codigo(nome))
    assert "from brasil_em_dados.analise import" in codigo
    for motivo, padrao in PROIBIDOS_NO_CODIGO.items():
        assert not padrao.search(codigo), f"{nome}: {motivo}"


@pytest.mark.parametrize("nome", NOTEBOOKS)
def test_notebook_versionado_tem_saidas_e_nenhum_erro(nome):
    nb = nbformat.read(PASTA / nome, as_version=4)
    saidas = [s for c in nb.cells if c.cell_type == "code" for s in c.get("outputs", [])]
    assert saidas, f"{nome} foi versionado sem executar"
    assert not [s for s in saidas if s.output_type == "error"]
    assert not URL_DE_CONEXAO.search(_textos_das_saidas(nb))


@pytest.mark.integracao
@pytest.mark.parametrize("nome", NOTEBOOKS)
def test_notebook_executa_sem_erro_e_sem_segredos(engine_readonly, tmp_path, nome):
    # engine_readonly (fixture): pula se o banco não estiver no ar, falha se recusar a conexão.
    copia = tmp_path / nome
    shutil.copy(PASTA / nome, copia)
    nb = nbformat.read(copia, as_version=4)
    # Só na cópia: a 1ª célula mostra qual Python o kernel usa (tem de ser o do .venv do pytest).
    nb.cells.insert(0, nbformat.v4.new_code_cell("import sys; print(sys.executable)"))
    NotebookClient(nb, timeout=TIMEOUT_CELULA_S, kernel_name="python3",
                   resources={"metadata": {"path": str(PASTA)}}).execute()  # erro numa célula falha aqui
    python_do_kernel = nb.cells[0].outputs[0].text.strip()
    assert Path(python_do_kernel).resolve() == Path(sys.executable).resolve()
    texto = _textos_das_saidas(nb)
    assert not URL_DE_CONEXAO.search(texto)
    ambiente = db.ler_ambiente()  # só em memória; nunca impresso
    for variavel in ("PG_PASSWORD", "PG_READONLY_PASSWORD"):
        valor = ambiente.get(variavel)
        if valor:
            assert valor not in texto, f"valor de {variavel} apareceu numa saída de {nome}"
