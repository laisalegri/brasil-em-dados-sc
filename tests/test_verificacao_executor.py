"""Testes do executor determinístico (com comando falso, sem rodar subprocessos)."""

import pytest

from brasil_em_dados.verificacao.executor import (
    CARGA,
    COLETA,
    GOLD,
    PYTEST,
    Saida,
    _texto,
    executar,
    passos_pedidos,
)


class RodarFalso:
    """Registra os comandos e devolve o código pedido por passo."""

    def __init__(self, codigos: dict[str, int | None] | None = None, texto: str = "saída"):
        self.codigos = codigos or {}
        self.texto = texto
        self.chamadas: list[tuple[str, ...]] = []

    def __call__(self, argumentos: tuple[str, ...]) -> Saida:
        self.chamadas.append(argumentos)
        nome = next(p.nome for p in (COLETA, CARGA, GOLD, PYTEST) if p.argumentos == argumentos)
        return Saida(self.codigos.get(nome, 0), self.texto)


def test_sem_flags_roda_so_o_pytest(tmp_path):
    rodar = RodarFalso()
    resultados = executar([], tmp_path / "exec", rodar=rodar)
    assert rodar.chamadas == [PYTEST.argumentos]
    assert [r.passo for r in resultados] == [PYTEST]


def test_flags_rodam_na_ordem_do_pipeline_e_pytest_no_fim(tmp_path):
    rodar = RodarFalso()
    executar(["gold", "coleta", "carga"], tmp_path / "exec", rodar=rodar)
    assert rodar.chamadas == [COLETA.argumentos, CARGA.argumentos, GOLD.argumentos,
                              PYTEST.argumentos]


def test_flag_desconhecida_falha():
    with pytest.raises(ValueError, match="Flags desconhecidas"):
        passos_pedidos(["apagar"])


def test_falha_no_pipeline_pula_os_seguintes_mas_roda_o_pytest(tmp_path):
    rodar = RodarFalso({"coleta": 1})
    resultados = executar(["coleta", "carga", "gold"], tmp_path / "exec", rodar=rodar)
    assert rodar.chamadas == [COLETA.argumentos, PYTEST.argumentos]
    assert [r.situacao for r in resultados] == ["falhou", "não executado", "não executado", "ok"]
    assert resultados[1].motivo == "um passo anterior do pipeline falhou"


def test_timeout_conta_como_falha(tmp_path):
    resultados = executar(["carga"], tmp_path / "exec", rodar=RodarFalso({"carga": None}))
    assert resultados[0].situacao == "falhou"
    assert resultados[0].motivo == "tempo esgotado"


def test_usuario_do_banco_de_cada_passo():
    assert COLETA.usuario_banco.startswith("nenhum")
    assert CARGA.usuario_banco == GOLD.usuario_banco == "bed_app"
    assert "bed_app" in PYTEST.usuario_banco and "bed_readonly" in PYTEST.usuario_banco


def test_saida_gravada_sem_url_nem_senha(tmp_path):
    texto = ("Engine do perfil app: postgresql+psycopg://bed_app:***@localhost:5432/b\n"
             "falha com senha-super-secreta\n")
    resultados = executar(["carga"], tmp_path / "exec", segredos=["senha-super-secreta"],
                          rodar=RodarFalso(texto=texto))
    gravado = resultados[0].arquivo_saida.read_text(encoding="utf-8")
    assert resultados[0].arquivo_saida.parent == tmp_path / "exec"
    assert "postgresql" not in gravado and "senha-super-secreta" not in gravado


def test_pasta_de_execucao_existente_nao_e_reaproveitada(tmp_path):
    pasta = tmp_path / "exec"
    pasta.mkdir()
    (pasta / "pytest.txt").write_text("saída anterior", encoding="utf-8")
    rodar = RodarFalso()
    with pytest.raises(FileExistsError):
        executar([], pasta, rodar=rodar)
    assert rodar.chamadas == []
    assert (pasta / "pytest.txt").read_text(encoding="utf-8") == "saída anterior"


@pytest.mark.parametrize("saida, esperado", [
    (None, ""), ("texto", "texto"), ("ação".encode("utf-8"), "ação"), (bytes([0xFF]), "�"),
])
def test_saida_parcial_do_timeout_vira_texto(saida, esperado):
    assert _texto(saida) == esperado
