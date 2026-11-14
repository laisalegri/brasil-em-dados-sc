"""Controle de execução das coletas em data/controle/execucoes.jsonl (D11, seção 9)."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from brasil_em_dados.extract.raw import iso_utc

STATUS_VALIDOS = frozenset({"sucesso", "falha"})


def registrar_execucao(
    caminho: Path,
    *,
    cod_serie: str,
    inicio: datetime,
    fim: datetime,
    status: str,
    n_registros: int | None,
    arquivo: str | None,
    erro: str | None,
) -> dict[str, Any]:
    """Acrescenta uma linha JSON ao controle de execução e devolve o registro."""
    if status not in STATUS_VALIDOS:
        raise ValueError(f"status inválido: {status!r}; use 'sucesso' ou 'falha'")
    registro = {
        "cod_serie": cod_serie,
        "inicio": iso_utc(inicio),
        "fim": iso_utc(fim),
        "status": status,
        "n_registros": n_registros,
        "arquivo": arquivo,
        "erro": erro,
    }
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "a", encoding="utf-8", newline="\n") as saida:
        saida.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return registro


def ler_execucoes(caminho: Path) -> list[dict[str, Any]]:
    """Lê todas as execuções registradas (lista vazia se o arquivo não existir)."""
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8") as entrada:
        return [json.loads(linha) for linha in entrada if linha.strip()]
