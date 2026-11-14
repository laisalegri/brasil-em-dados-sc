"""Validação mínima das respostas antes de gravar na RAW (D11, seção 6)."""

import json
from typing import Any

from brasil_em_dados.extract.erros import ErroValidacao


def carregar_json(conteudo: bytes) -> Any:
    """Interpreta os bytes como JSON; HTML ou texto inválido viram ErroValidacao."""
    try:
        return json.loads(conteudo)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        inicio = conteudo[:80].decode("utf-8", errors="replace")
        raise ErroValidacao(f"Resposta não é JSON válido (início: {inicio!r})") from exc


def contar_registros(dados: Any, fonte: str) -> int:
    """Conta os registros de dados conforme a estrutura de cada fonte."""
    if fonte == "sidra":
        if not isinstance(dados, list) or len(dados) < 2 or not isinstance(dados[0], dict):
            raise ErroValidacao("SIDRA: esperado cabeçalho e pelo menos uma linha de dados")
        return len(dados) - 1
    if fonte == "api_localidades":
        if not isinstance(dados, list) or not dados:
            raise ErroValidacao("API de Localidades: esperada lista não vazia")
        return len(dados)
    if fonte == "api_pesquisas":
        if not isinstance(dados, list) or not dados:
            raise ErroValidacao("API de Pesquisas: esperada lista não vazia")
        total = 0
        for item in dados:
            resultados = item.get("res") if isinstance(item, dict) else None
            if not isinstance(resultados, list) or not resultados:
                raise ErroValidacao("API de Pesquisas: indicador sem lista 'res' não vazia")
            total += len(resultados)
        return total
    raise ErroValidacao(f"Fonte desconhecida: {fonte!r}")


def validar_e_carregar(status_http: int, conteudo: bytes, fonte: str) -> tuple[Any, int]:
    """Valida status 200, JSON e estrutura; devolve (dados, n_registros)."""
    if status_http != 200:
        raise ErroValidacao(f"Status HTTP {status_http}; esperado 200")
    dados = carregar_json(conteudo)
    return dados, contar_registros(dados, fonte)


def validar_resposta(status_http: int, conteudo: bytes, fonte: str) -> int:
    """Valida status 200, JSON e estrutura; devolve n_registros."""
    return validar_e_carregar(status_http, conteudo, fonte)[1]
