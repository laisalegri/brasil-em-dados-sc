"""Cliente HTTP das coletas: timeout, novas tentativas com backoff e Retry-After (D11)."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

import requests

from brasil_em_dados.extract.erros import ErroHTTP

logger = logging.getLogger(__name__)

USER_AGENT = "brasil-em-dados-sc/0.1 (projeto de portfolio)"
TIMEOUT: tuple[float, float] = (10, 60)
MAX_TENTATIVAS = 3
ESPERA_BASE_S = 1.0
ESPERA_MAXIMA_S = 60.0


@dataclass(frozen=True)
class RespostaHTTP:
    """Resposta bruta de uma requisição bem-sucedida."""

    url: str
    status_http: int
    conteudo: bytes
    duracao_ms: int
    tentativas: int


def criar_sessao() -> requests.Session:
    """Cria a sessão HTTP com o User-Agent do projeto."""
    sessao = requests.Session()
    sessao.headers["User-Agent"] = USER_AGENT
    return sessao


def deve_repetir(status_http: int) -> bool:
    """Indica se o status justifica nova tentativa (429 ou 5xx)."""
    return status_http == 429 or 500 <= status_http <= 599


def calcular_espera(tentativa: int, espera_base: float, retry_after: str | None) -> float:
    """Segundos até a próxima tentativa: Retry-After válido ou backoff exponencial, com teto."""
    if retry_after is not None:
        try:
            segundos = float(retry_after)
        except ValueError:
            segundos = -1.0
        if segundos >= 0:
            return min(segundos, ESPERA_MAXIMA_S)
    return min(espera_base * 2 ** (tentativa - 1), ESPERA_MAXIMA_S)


def baixar(
    url: str,
    sessao: requests.Session | None = None,
    *,
    timeout: tuple[float, float] = TIMEOUT,
    max_tentativas: int = MAX_TENTATIVAS,
    espera_base: float = ESPERA_BASE_S,
    dormir: Callable[[float], None] = time.sleep,
) -> RespostaHTTP:
    """Faz GET com novas tentativas para 429, 5xx e timeout; demais 4xx falham na hora."""
    if max_tentativas < 1:
        raise ValueError("max_tentativas deve ser pelo menos 1")
    sessao_propria = sessao is None
    if sessao is None:
        sessao = criar_sessao()
    ultimo_erro = ""
    ultimo_status: int | None = None
    try:
        for tentativa in range(1, max_tentativas + 1):
            retry_after: str | None = None
            inicio = time.perf_counter()
            try:
                resposta = sessao.get(url, timeout=timeout)
            except requests.Timeout as exc:
                ultimo_erro = f"timeout ({exc.__class__.__name__})"
                ultimo_status = None
            except requests.RequestException as exc:
                raise ErroHTTP(f"Falha de conexão em {url}: {exc}") from exc
            else:
                status = resposta.status_code
                if not deve_repetir(status):
                    if 400 <= status <= 499:
                        raise ErroHTTP(f"HTTP {status} em {url} (sem nova tentativa)", status)
                    duracao_ms = round((time.perf_counter() - inicio) * 1000)
                    return RespostaHTTP(url, status, resposta.content, duracao_ms, tentativa)
                ultimo_erro = f"HTTP {status}"
                ultimo_status = status
                retry_after = resposta.headers.get("Retry-After")

            if tentativa < max_tentativas:
                espera = calcular_espera(tentativa, espera_base, retry_after)
                logger.warning("Tentativa %d/%d falhou (%s) em %s; nova tentativa em %.1f s",
                               tentativa, max_tentativas, ultimo_erro, url, espera)
                dormir(espera)
    finally:
        if sessao_propria:
            sessao.close()

    raise ErroHTTP(f"{ultimo_erro} em {url} após {max_tentativas} tentativas", ultimo_status)
