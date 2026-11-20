"""Testes da linha de comando da verificação (passos, banco e modelo falsos)."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from brasil_em_dados.verificacao import __main__ as cli
from brasil_em_dados.verificacao import agente
from brasil_em_dados.verificacao.executor import CARGA, COLETA, GOLD, PYTEST, Saida
from tests.apoio_verificacao import ClienteFalso

AGORA = datetime(2026, 11, 20, 12, 0, 0, tzinfo=timezone.utc)
CARIMBO = "20261120T120000"
SENHA = "senha-do-banco-teste"
SAIDA_SUJA = f"Engine: postgresql+psycopg://bed_app:***@localhost/b\nerro {SENHA}\n10 passed\n"


class RodarFalso:
    def __init__(self, codigos=None):
        self.codigos = codigos or {}
        self.chamadas = []

    def __call__(self, argumentos):
        self.chamadas.append(argumentos)
        nome = next(p.nome for p in (COLETA, CARGA, GOLD, PYTEST) if p.argumentos == argumentos)
        return Saida(self.codigos.get(nome, 0), SAIDA_SUJA)


@pytest.fixture(autouse=True)
def _sem_logs():
    with patch.object(cli, "configurar_logging"), patch.object(cli, "proteger_logs"):
        yield


def _main(tmp_path, argv=(), rodar=None, cliente=None, ambiente=None):
    rodar = rodar or RodarFalso()
    entregue = {}

    def fabrica(opcoes):
        # o "modelo falso" chama a ferramenta entregar_relatorio de verdade
        ferramentas = {f.name: f for f in entregue["ferramentas"]}

        async def roteiro():
            await ferramentas["entregar_relatorio"].handler({"texto": f"## Resumo\nOk. {SENHA}"})
        return ClienteFalso(opcoes, roteiro=roteiro)

    criar_ferramentas_original = cli.modulo_agente.criar_ferramentas

    def capturar(contexto):
        entregue["ferramentas"] = criar_ferramentas_original(contexto)
        return entregue["ferramentas"]

    with patch.object(cli.modulo_agente, "criar_ferramentas", side_effect=capturar):
        codigo = cli.main(list(argv), ambiente=ambiente or {"PATH": "x"},
                          ler_ambiente_banco=lambda: {"PG_PASSWORD": SENHA}, rodar=rodar,
                          criar_engine=Mock(), criar_cliente=cliente or fabrica,
                          pasta_reports=tmp_path, agora=lambda: AGORA)
    return codigo, rodar


def _relatorio(tmp_path) -> str:
    return (tmp_path / f"verificacao_{CARIMBO}.md").read_text(encoding="utf-8")


def test_sem_flags_roda_so_pytest_e_grava_relatorio_completo(tmp_path):
    codigo, rodar = _main(tmp_path)
    assert codigo == cli.SAIDA_OK
    assert rodar.chamadas == [PYTEST.argumentos]
    texto = _relatorio(tmp_path)
    assert "Flags recebidas: nenhuma (só pytest)" in texto
    assert "`python -m brasil_em_dados.verificacao`" in texto
    assert "| pytest |" in texto and PYTEST.usuario_banco in texto
    assert "bed_readonly, com SET TRANSACTION READ ONLY" in texto
    assert "## Análise do agente\n\n## Resumo\nOk." in texto
    assert "Origem da chave (apiKeySource): none (login do plano Pro" in texto
    assert "Turnos: 5" in texto and "US$ 0.0123" in texto and "saída 200" in texto
    assert SENHA not in texto and "postgresql" not in texto
    saida_pytest = (tmp_path / f"execucao_{CARIMBO}" / "pytest.txt").read_text(encoding="utf-8")
    assert SENHA not in saida_pytest and "postgresql" not in saida_pytest


def test_flags_e_usuarios_de_cada_passo_no_relatorio(tmp_path):
    codigo, rodar = _main(tmp_path, ["--coleta", "--carga", "--gold"])
    assert codigo == cli.SAIDA_OK
    assert len(rodar.chamadas) == 4
    texto = _relatorio(tmp_path)
    assert "Flags recebidas: --coleta --carga --gold" in texto
    assert "| coleta |" in texto and "nenhum (grava só na RAW)" in texto
    assert "| carga | `python -m brasil_em_dados.load tudo` | bed_app |" in texto
    assert "| gold | `python -m brasil_em_dados.db.aplicar_gold` | bed_app |" in texto


def test_trava_de_credenciais_para_antes_de_qualquer_passo(tmp_path):
    rodar = RodarFalso()
    codigo, _ = _main(tmp_path, rodar=rodar, ambiente={"ANTHROPIC_API_KEY": "nao-mostrar"})
    assert codigo == cli.SAIDA_CREDENCIAL
    assert rodar.chamadas == []
    assert list(tmp_path.iterdir()) == []


def test_ferramentas_inesperadas_param_com_erro_e_relatorio_explica(tmp_path):
    extras = ["mcp__claude_ai_Claude_Docs__delete"]

    def fabrica(opcoes):
        return ClienteFalso(opcoes, sorted(agente.FERRAMENTAS_ESPERADAS) + extras)

    codigo, _ = _main(tmp_path, cliente=fabrica)
    assert codigo == cli.SAIDA_FERRAMENTAS
    texto = _relatorio(tmp_path)
    assert "Análise não produzida" in texto and extras[0] in texto
    assert "Situação: interrompido" in texto


def test_passo_que_falha_da_codigo_1(tmp_path):
    codigo, _ = _main(tmp_path, rodar=RodarFalso({"pytest": 1}))
    assert codigo == cli.SAIDA_FALHA
    assert "| pytest |" in _relatorio(tmp_path) and "falhou" in _relatorio(tmp_path)


def test_agente_sem_analise_da_codigo_1(tmp_path):
    codigo, _ = _main(tmp_path, cliente=lambda opcoes: ClienteFalso(opcoes))
    assert codigo == cli.SAIDA_FALHA
    assert "Análise não produzida: o agente não entregou a análise." in _relatorio(tmp_path)


def test_relatorio_existente_nao_e_sobrescrito(tmp_path):
    existente = tmp_path / f"verificacao_{CARIMBO}.md"
    existente.write_text("original", encoding="utf-8")
    rodar = RodarFalso()
    codigo, _ = _main(tmp_path, rodar=rodar)
    assert codigo == cli.SAIDA_FALHA
    assert rodar.chamadas == []
    assert existente.read_text(encoding="utf-8") == "original"


def test_prompt_traz_a_situacao_decidida_pelo_executor(tmp_path):
    clientes = []

    def fabrica(opcoes):
        cliente = ClienteFalso(opcoes)
        clientes.append(cliente)
        return cliente

    _main(tmp_path, ["--carga"], cliente=fabrica)
    assert "Comando: python -m brasil_em_dados.verificacao --carga" in clientes[0].prompt
    assert "- carga: ok (usuário do banco: bed_app)" in clientes[0].prompt


def test_sessao_fora_do_login_do_plano_da_codigo_2_e_relatorio_explica(tmp_path):
    codigo, _ = _main(tmp_path, cliente=lambda opcoes: ClienteFalso(opcoes, origem="apiKeyHelper"))
    assert codigo == cli.SAIDA_CREDENCIAL
    texto = _relatorio(tmp_path)
    assert "Origem da chave (apiKeySource): apiKeyHelper" in texto
    assert "Análise não produzida" in texto and "login do plano" in texto


def test_pasta_de_execucao_existente_impede_a_execucao(tmp_path):
    (tmp_path / f"execucao_{CARIMBO}").mkdir()
    rodar = RodarFalso()
    codigo, _ = _main(tmp_path, rodar=rodar)
    assert codigo == cli.SAIDA_FALHA
    assert rodar.chamadas == []
    assert not (tmp_path / f"verificacao_{CARIMBO}.md").exists()


def test_relatorio_que_aparece_durante_a_execucao_nao_e_sobrescrito(tmp_path):
    caminho = tmp_path / f"verificacao_{CARIMBO}.md"

    def rodar(argumentos):
        caminho.write_text("outro processo", encoding="utf-8")  # corrida simulada
        return Saida(0, "ok")

    codigo, _ = _main(tmp_path, rodar=rodar)
    assert codigo == cli.SAIDA_FALHA
    assert caminho.read_text(encoding="utf-8") == "outro processo"


def test_erro_do_agente_nao_derruba_e_relatorio_sai_limpo(tmp_path):
    def fabrica(opcoes):
        raise RuntimeError(f"falha em postgresql://bed_readonly:{SENHA}@h/b")

    codigo, _ = _main(tmp_path, cliente=fabrica)
    assert codigo == cli.SAIDA_FALHA
    texto = _relatorio(tmp_path)
    assert "Situação: erro" in texto and SENHA not in texto and "postgresql" not in texto
