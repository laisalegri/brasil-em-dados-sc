"""Apoio dos testes da verificação: cliente falso do Agent SDK e resultados de passos."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from claude_agent_sdk import ResultMessage, SystemMessage

from brasil_em_dados.verificacao.agente import FERRAMENTAS_ESPERADAS, MODELO
from brasil_em_dados.verificacao.executor import PYTEST, Passo, ResultadoPasso

USO = {"input_tokens": 10, "output_tokens": 200, "cache_creation_input_tokens": 3000,
       "cache_read_input_tokens": 500}
USO_POR_MODELO = {MODELO: {"inputTokens": 10, "outputTokens": 200, "cacheReadInputTokens": 500,
                           "cacheCreationInputTokens": 3000, "costUSD": 0.0123}}


def resultado_ok(passo: Passo = PYTEST, arquivo: Path | None = None) -> ResultadoPasso:
    return ResultadoPasso(passo, executado=True, codigo=0, duracao_s=1.5, arquivo_saida=arquivo)


def mensagem_resultado(is_error: bool = False, subtype: str = "success") -> ResultMessage:
    return ResultMessage(subtype=subtype, duration_ms=4200, duration_api_ms=4000,
                         is_error=is_error, num_turns=5, session_id="sessao-teste",
                         total_cost_usd=0.0123, usage=USO, model_usage=USO_POR_MODELO)


Roteiro = Callable[[], Awaitable[None]]


class ClienteFalso:
    """Substitui o ClaudeSDKClient: anuncia ferramentas, roda um roteiro e devolve o resultado.

    O "modelo falso" é o `roteiro`: uma corrotina que chama as ferramentas como o modelo faria.
    Se `interrupt()` for chamado ao receber o init, o roteiro não roda.
    """

    def __init__(self, opcoes: Any, ferramentas: list[str] | None = None,
                 roteiro: Roteiro | None = None, resultado: ResultMessage | None = None,
                 origem: str | None = "none", modelo: str | None = MODELO) -> None:
        self.opcoes = opcoes
        self.origem = origem
        self.modelo = modelo
        self.ferramentas = sorted(FERRAMENTAS_ESPERADAS) if ferramentas is None else ferramentas
        self.roteiro = roteiro
        self.resultado = resultado or mensagem_resultado()
        self.prompt: str | None = None
        self.interrompido = False

    async def __aenter__(self) -> "ClienteFalso":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def query(self, prompt: str) -> None:
        self.prompt = prompt

    async def interrupt(self) -> None:
        self.interrompido = True

    async def receive_response(self):
        yield SystemMessage(subtype="init", data={"tools": self.ferramentas, "model": self.modelo,
                                                   "apiKeySource": self.origem})
        if not self.interrompido and self.roteiro is not None:
            await self.roteiro()
        yield self.resultado


def ferramenta(ferramentas: list[Any], nome: str) -> Any:
    """SdkMcpTool pelo nome."""
    return next(f for f in ferramentas if f.name == nome)
