"""Exceções da coleta. Qualquer ErroColeta significa que nada foi gravado como coleta válida."""


class ErroColeta(Exception):
    """Falha em uma coleta."""


class ErroHTTP(ErroColeta):
    """Falha de comunicação com a API (status inesperado, timeout ou conexão)."""

    def __init__(self, mensagem: str, status_http: int | None = None) -> None:
        super().__init__(mensagem)
        self.status_http = status_http


class ErroValidacao(ErroColeta):
    """Resposta recebida, mas fora do formato esperado."""


class ErroGravacao(ErroColeta):
    """Falha ao gravar na RAW sem risco de sobrescrita."""
