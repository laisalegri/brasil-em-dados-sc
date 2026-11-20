"""Estudo do Claude Agent SDK (D28). Fora do pipeline.

Faz uma pergunta simples ao modelo, sem ferramentas, e imprime a resposta e o
uso reportado. Autentica pelo login do plano Claude Pro (decisão de 2026-11-20):
antes de chamar o SDK, para se houver no ambiente uma credencial que passaria
na frente da assinatura. Mostra só o nome da variável, nunca o valor.

Uso: python scripts/estudo_agent_sdk.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Mapping

# Pela ordem de autenticação do Claude Code, estas variáveis têm prioridade
# sobre o login do plano (https://code.claude.com/docs/en/authentication).
CREDENCIAIS_DE_API = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
PROVEDORES_DE_NUVEM = (
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_USE_ANTHROPIC_AWS",
)

PERGUNTA = "Em uma frase: por que variação de PIB nominal não é crescimento econômico real?"


def credenciais_fora_do_plano(ambiente: Mapping[str, str]) -> list[str]:
    """Nomes das variáveis definidas que tirariam a execução do plano Pro.

    Uma variável definida com valor vazio também conta: a regra é não defini-la.
    """
    return [nome for nome in (*CREDENCIAIS_DE_API, *PROVEDORES_DE_NUVEM) if nome in ambiente]


def mensagem_de_bloqueio(nomes: list[str]) -> str:
    """Mensagem de parada, só com os nomes das variáveis."""
    lista = ", ".join(nomes)
    return (
        f"Parei antes de chamar o modelo: {lista} está definida no ambiente.\n"
        "Ela tem prioridade sobre o login do plano Pro e a cobrança passaria a ser por API.\n"
        "Remova a variável deste terminal (por exemplo, Remove-Item Env:NOME) e rode de novo."
    )


async def perguntar(pergunta: str) -> int:
    """Faz a pergunta sem ferramentas e imprime resposta e uso. Devolve o código de saída."""
    # Import aqui dentro: a trava acima roda (e é testada) sem o SDK instalado.
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        SystemMessage,
        TextBlock,
        query,
    )

    opcoes = ClaudeAgentOptions(
        system_prompt="Responda em português do Brasil, em uma frase curta.",
        tools=[],  # nenhuma ferramenta embutida no contexto
        # Conectores da conta do claude.ai entram mesmo com tools=[] e setting_sources=[]
        # (visto na primeira execução); a regra de negação os tira do contexto.
        disallowed_tools=["mcp__claude_ai_*"],
        permission_mode="dontAsk",  # qualquer pedido de permissão vira recusa
        setting_sources=[],  # não carrega CLAUDE.md, settings nem agentes do projeto
        max_turns=1,
    )

    resultado: ResultMessage | None = None
    async for mensagem in query(prompt=pergunta, options=opcoes):
        if isinstance(mensagem, SystemMessage) and mensagem.subtype == "init":
            # "none" indica que não há chave de API em uso, só o login do plano.
            print(f"Origem da chave de API: {mensagem.data.get('apiKeySource')}")
            print(f"Modelo: {mensagem.data.get('model')}")
            print(f"Ferramentas disponíveis: {mensagem.data.get('tools')}")
        elif isinstance(mensagem, AssistantMessage):
            for bloco in mensagem.content:
                if isinstance(bloco, TextBlock):
                    print(f"\nResposta: {bloco.text}\n")
        elif isinstance(mensagem, ResultMessage):
            resultado = mensagem

    if resultado is None:
        print("A execução terminou sem mensagem de resultado.")
        return 1

    print(f"Situação: {resultado.subtype} (erro: {resultado.is_error})")
    print(f"Turnos: {resultado.num_turns} | duração: {resultado.duration_ms} ms "
          f"(API: {resultado.duration_api_ms} ms)")
    print(f"Uso (laço principal): {resultado.usage}")
    print(f"Uso por modelo: {resultado.model_usage}")
    print(f"Custo estimado a preço de API: US$ {resultado.total_cost_usd}"
          " (estimativa local; no plano Pro não é cobrança, consome o limite da assinatura)")
    return 1 if resultado.is_error else 0


def main() -> int:
    """Confere o ambiente e, se estiver limpo, faz a pergunta."""
    bloqueio = credenciais_fora_do_plano(os.environ)
    if bloqueio:
        print(mensagem_de_bloqueio(bloqueio), file=sys.stderr)
        return 2
    return asyncio.run(perguntar(PERGUNTA))


if __name__ == "__main__":
    sys.exit(main())
