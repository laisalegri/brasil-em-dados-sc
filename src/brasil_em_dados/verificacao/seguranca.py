"""Travas de segurança do agente de verificação: credenciais e limpeza de texto.

- A execução precisa usar o login do plano Pro (decisão de 2026-11-20): variáveis que passariam
  na frente da assinatura fazem o agente parar antes de chamar o modelo, mostrando só o nome.
- Nenhum texto que vai para o modelo, para o relatório ou para os logs pode conter URL de
  conexão ou senha do banco.
"""

import logging
import re
import traceback
from collections.abc import Iterable, Mapping

from brasil_em_dados.db import PERFIL_APP, PERFIL_READONLY
from brasil_em_dados.logs import NOME_LOGGER

# Ordem de autenticação do Claude Code (https://code.claude.com/docs/en/authentication):
# estas variáveis têm prioridade sobre o login do plano.
CREDENCIAIS_DE_API = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
PROVEDORES_DE_NUVEM = (
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_USE_ANTHROPIC_AWS",
)

URL_OMITIDA = "<url de conexão omitida>"
SENHA_OMITIDA = "<senha omitida>"
_URL_BANCO = re.compile(r"postgres(?:ql)?(?:\+\w+)?://\S+", re.IGNORECASE)
TAMANHO_MINIMO_SEGREDO = 4  # evita trocar trechos curtos e comuns por engano


class ErroCredencial(Exception):
    """Há no ambiente uma credencial que tiraria a execução do plano Pro (sem o valor)."""


def credenciais_fora_do_plano(ambiente: Mapping[str, str]) -> list[str]:
    """Nomes das variáveis definidas que tirariam a execução do plano (vazia também conta)."""
    return [nome for nome in (*CREDENCIAIS_DE_API, *PROVEDORES_DE_NUVEM) if nome in ambiente]


def exigir_login_do_plano(ambiente: Mapping[str, str]) -> None:
    """Levanta ErroCredencial, só com os nomes, se alguma variável da lista estiver definida."""
    nomes = credenciais_fora_do_plano(ambiente)
    if nomes:
        raise ErroCredencial(
            f"Parei antes de chamar o modelo: {', '.join(nomes)} está definida no ambiente. "
            "Ela tem prioridade sobre o login do plano Pro e a cobrança passaria a ser por API. "
            "Remova a variável deste terminal (por exemplo, Remove-Item Env:NOME) e rode de novo.")


def segredos_do_banco(ambiente: Mapping[str, str]) -> list[str]:
    """Senhas dos dois perfis do banco presentes no ambiente (para limpar textos, nunca exibir)."""
    nomes = (PERFIL_APP.var_senha, PERFIL_READONLY.var_senha)
    return [ambiente[n] for n in nomes if len(ambiente.get(n) or "") >= TAMANHO_MINIMO_SEGREDO]


def limpar_texto(texto: str, segredos: Iterable[str] = ()) -> str:
    """Troca URLs de conexão e os segredos informados por marcadores."""
    limpo = _URL_BANCO.sub(URL_OMITIDA, texto)
    for segredo in sorted(set(segredos), key=len, reverse=True):
        limpo = limpo.replace(segredo, SENHA_OMITIDA)
    return limpo


class FiltroSegredos(logging.Filter):
    """Limpa mensagem, traceback e pilha de cada registro antes de ele chegar ao console ou a logs/."""

    def __init__(self, segredos: Iterable[str] = ()) -> None:
        super().__init__()
        self.segredos = list(segredos)

    def filter(self, registro: logging.LogRecord) -> bool:
        registro.msg = limpar_texto(registro.getMessage(), self.segredos)
        registro.args = None
        if registro.exc_info:
            # O Formatter usa exc_text quando ele existe; o traceback cru não é mais formatado.
            registro.exc_text = limpar_texto(
                "".join(traceback.format_exception(*registro.exc_info)).rstrip(), self.segredos)
            registro.exc_info = None
        elif registro.exc_text:
            registro.exc_text = limpar_texto(registro.exc_text, self.segredos)
        if registro.stack_info:
            registro.stack_info = limpar_texto(registro.stack_info, self.segredos)
        return True


def proteger_logs(segredos: Iterable[str], nome_logger: str = NOME_LOGGER) -> FiltroSegredos:
    """Põe o filtro em cada handler do logger do projeto (filtros de logger não valem para filhos)."""
    filtro = FiltroSegredos(segredos)
    for handler in logging.getLogger(nome_logger).handlers:
        handler.addFilter(filtro)
    return filtro
