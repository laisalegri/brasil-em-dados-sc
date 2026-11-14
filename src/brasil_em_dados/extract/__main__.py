"""Linha de comando das coletas: python -m brasil_em_dados.extract <cod_serie>|todas."""

import argparse
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from brasil_em_dados.extract import catalogo
from brasil_em_dados.extract.coleta import coletar
from brasil_em_dados.logs import configurar_logging

logger = logging.getLogger("brasil_em_dados.extract.cli")

TODAS = "todas"


@dataclass(frozen=True)
class Resultado:
    """Resultado de uma coleta na linha de comando."""

    cod_serie: str
    meta: dict[str, Any] | None
    erro: str | None


def ordem_de_coleta() -> list[str]:
    """Dimensões primeiro (a validação da API de Pesquisas usa o cadastro), depois as séries."""
    dimensoes = [f.cod_serie for f in catalogo.FONTES.values() if f.tipo == catalogo.TIPO_DIMENSAO]
    return dimensoes + [s.cod_serie for s in catalogo.series()]


def executar(alvos: list[str], coletar_fn: Callable[[str], dict[str, Any]] | None = None
             ) -> list[Resultado]:
    """Coleta cada alvo; uma falha não interrompe os demais."""
    coletar_fn = coletar_fn or coletar
    resultados = []
    for cod_serie in alvos:
        try:
            resultados.append(Resultado(cod_serie, coletar_fn(cod_serie), None))
        except Exception as exc:  # o erro já foi registrado no log e no controle
            resultados.append(Resultado(cod_serie, None, f"{type(exc).__name__}: {exc}"))
    return resultados


def registrar_resumo(resultados: list[Resultado]) -> None:
    """Escreve no log uma linha por coleta e o total de sucessos e falhas."""
    logger.info("Resumo da execução:")
    for r in resultados:
        if r.meta is not None:
            logger.info("  OK     %-22s n_registros=%-5s igual_a_anterior=%-5s arquivo=%s",
                        r.cod_serie, r.meta["n_registros"], r.meta["igual_a_anterior"],
                        r.meta["arquivo_dados"])
        else:
            logger.error("  FALHA  %-22s %s", r.cod_serie, r.erro)
    falhas = sum(r.meta is None for r in resultados)
    logger.info("Total: %d coleta(s), %d sucesso(s), %d falha(s)",
                len(resultados), len(resultados) - falhas, falhas)


def main(argv: list[str] | None = None) -> int:
    """Executa a linha de comando; devolve 0 se todas as coletas tiveram sucesso, 1 caso contrário."""
    parser = argparse.ArgumentParser(prog="python -m brasil_em_dados.extract",
                                     description="Coleta fontes do catálogo para a RAW.")
    parser.add_argument("alvo", choices=[*catalogo.FONTES, TODAS],
                        help="cod_serie do catálogo ou 'todas'")
    args = parser.parse_args(argv)

    configurar_logging()
    alvos = ordem_de_coleta() if args.alvo == TODAS else [args.alvo]
    resultados = executar(alvos)
    registrar_resumo(resultados)
    return 0 if all(r.meta is not None for r in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
