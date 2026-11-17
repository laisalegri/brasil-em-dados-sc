"""Linha de comando da carga na SILVER.

Uso: python -m brasil_em_dados.load dimensoes
"""

import argparse
import logging
import sys

from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from brasil_em_dados.db import engine_app
from brasil_em_dados.load import dimensoes
from brasil_em_dados.logs import configurar_logging
from brasil_em_dados.transform.dimensoes import ErroTransformacao

# Nome fixo: com `python -m`, __name__ vira "__main__" e o log ficaria fora de "brasil_em_dados".
logger = logging.getLogger("brasil_em_dados.load.cli")

ALVOS = ("dimensoes",)


def main(argv: list[str] | None = None, engine: Engine | None = None) -> int:
    """Executa a carga pedida; devolve 0 em sucesso e 1 em erro (transação desfeita)."""
    parser = argparse.ArgumentParser(prog="python -m brasil_em_dados.load",
                                     description="Carga na SILVER (bed_app).")
    parser.add_argument("alvo", choices=ALVOS, help="o que carregar")
    parser.parse_args(argv)
    configurar_logging()
    engine = engine or engine_app()
    try:
        resumos = dimensoes.executar(engine)
    except (dimensoes.ErroCarga, ErroTransformacao, SQLAlchemyError) as exc:
        logger.error("Carga não feita; transação desfeita. %s", exc)
        return 1
    finally:
        engine.dispose()
    logger.info("Resumo da carga:")
    for resumo in resumos:
        logger.info("  %s", resumo.texto())
    return 0


if __name__ == "__main__":
    sys.exit(main())
