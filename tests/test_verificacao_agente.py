"""Testes do agente de verificação com modelo falso (cliente do SDK substituído)."""

import asyncio

import pytest

from brasil_em_dados.config import PASTA_CONSULTAS_VERIFICACAO
from brasil_em_dados.verificacao import agente
from brasil_em_dados.verificacao.ferramentas import Contexto, ler_catalogo, nome_completo
from brasil_em_dados.verificacao.seguranca import ErroCredencial
from tests.apoio_verificacao import ClienteFalso, mensagem_resultado

AMBIENTE_LIMPO = {"PATH": "x"}


def _contexto(tmp_path) -> Contexto:
    return Contexto("20261120T120000", [], ler_catalogo(PASTA_CONSULTAS_VERIFICACAO), tmp_path,
                    None, [])


def _rodar(contexto, fabrica, ambiente=AMBIENTE_LIMPO):
    return asyncio.run(agente.executar_agente(contexto, "verifique", fabrica, ambiente))


def test_opcoes_fechadas(tmp_path):
    opcoes = agente.montar_opcoes(_contexto(tmp_path))
    assert opcoes.model == agente.MODELO == "claude-sonnet-5-5"
    assert opcoes.max_turns == agente.MAX_TURNOS
    assert opcoes.tools == []
    assert opcoes.disallowed_tools == ["mcp__claude_ai_*"]
    assert opcoes.permission_mode == "dontAsk"
    assert opcoes.setting_sources == []
    assert set(opcoes.allowed_tools) == agente.FERRAMENTAS_ESPERADAS
    assert not any("*" in nome for nome in opcoes.allowed_tools)
    assert list(opcoes.mcp_servers) == ["verif"]


def test_ferramentas_esperadas_sao_as_sete_proprias():
    assert agente.FERRAMENTAS_ESPERADAS == {
        "mcp__verif__resultado_testes", "mcp__verif__saida_passo",
        "mcp__verif__controle_execucao", "mcp__verif__consulta_qualidade",
        "mcp__verif__referencias_dashboards", "mcp__verif__relatorio_anterior",
        "mcp__verif__entregar_relatorio"}


def test_agente_com_modelo_falso_entrega_analise_e_consumo(tmp_path):
    contexto = _contexto(tmp_path)
    clientes = []

    def fabrica(opcoes):
        async def roteiro():
            contexto.entregar_relatorio("## Resumo\nTestes passaram (resultado_testes).")
        cliente = ClienteFalso(opcoes, roteiro=roteiro)
        clientes.append(cliente)
        return cliente

    resultado = _rodar(contexto, fabrica)
    assert clientes[0].prompt == "verifique"
    assert contexto.analise.startswith("## Resumo")
    assert resultado.situacao == "success" and resultado.erro is None
    assert resultado.turnos == 5 and resultado.custo_estimado_usd == pytest.approx(0.0123)
    assert resultado.usage["output_tokens"] == 200
    assert resultado.modelo == agente.MODELO


@pytest.mark.parametrize("extras", [
    ["mcp__claude_ai_Claude_Docs__delete"],
    ["Bash", "Write"],
    ["mcp__outro__ferramenta"],
])
def test_ferramenta_inesperada_interrompe_e_lista_os_nomes(tmp_path, extras):
    contexto = _contexto(tmp_path)
    clientes = []

    def fabrica(opcoes):
        async def roteiro():  # não deve rodar: o agente foi interrompido no init
            contexto.analise = "não devia"
        cliente = ClienteFalso(opcoes, sorted(agente.FERRAMENTAS_ESPERADAS) + extras, roteiro)
        clientes.append(cliente)
        return cliente

    with pytest.raises(agente.ErroFerramentasInesperadas) as erro:
        _rodar(contexto, fabrica)
    assert clientes[0].interrompido is True
    assert contexto.bloqueado is True and contexto.analise is None
    for nome in extras:
        assert nome in str(erro.value)
    assert erro.value.resultado.situacao == "interrompido"


def test_ferramenta_propria_ausente_tambem_interrompe(tmp_path):
    faltando = nome_completo("entregar_relatorio")
    recebidas = sorted(agente.FERRAMENTAS_ESPERADAS - {faltando})
    with pytest.raises(agente.ErroFerramentasInesperadas, match="ausentes: " + faltando):
        _rodar(_contexto(tmp_path), lambda opcoes: ClienteFalso(opcoes, recebidas))


def test_lista_de_ferramentas_ausente_interrompe():
    assert "não informou" in agente.problemas_de_ferramentas(None)
    assert agente.problemas_de_ferramentas(sorted(agente.FERRAMENTAS_ESPERADAS)) is None


def test_trava_de_credenciais_para_antes_de_criar_o_cliente(tmp_path):
    def fabrica(opcoes):
        raise AssertionError("o cliente não pode ser criado")

    with pytest.raises(ErroCredencial):
        _rodar(_contexto(tmp_path), fabrica, {"ANTHROPIC_API_KEY": "x"})


def test_resultado_com_erro_fica_registrado(tmp_path):
    resultado = _rodar(_contexto(tmp_path), lambda opcoes: ClienteFalso(
        opcoes, resultado=mensagem_resultado(is_error=True, subtype="error_max_turns")))
    assert resultado.situacao == "error_max_turns"
    assert "error_max_turns" in resultado.erro


@pytest.mark.parametrize("origem", ["ANTHROPIC_API_KEY", "apiKeyHelper", None])
def test_sessao_fora_do_login_do_plano_interrompe(tmp_path, origem):
    contexto = _contexto(tmp_path)
    clientes = []

    def fabrica(opcoes):
        cliente = ClienteFalso(opcoes, origem=origem)
        clientes.append(cliente)
        return cliente

    with pytest.raises(agente.ErroOrigemDaChave, match="login do plano") as erro:
        _rodar(contexto, fabrica)
    assert clientes[0].interrompido is True and contexto.bloqueado is True
    assert erro.value.resultado.origem_chave == origem


def test_modelo_diferente_do_fixado_interrompe(tmp_path):
    with pytest.raises(agente.ErroFerramentasInesperadas, match="claude-opus-5-5"):
        _rodar(_contexto(tmp_path), lambda opcoes: ClienteFalso(opcoes, modelo="claude-opus-5-5"))


def test_origem_da_chave_fica_no_resultado(tmp_path):
    resultado = _rodar(_contexto(tmp_path), lambda opcoes: ClienteFalso(opcoes))
    assert resultado.origem_chave == "none"
