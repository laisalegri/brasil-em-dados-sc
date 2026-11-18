"""Linha de comando da carga na SILVER (bed_app).

Uso: python -m brasil_em_dados.load {dimensoes,fato,tudo}

- dimensoes: dim_indicador, dim_serie e dim_municipio (D20).
- fato: fato_indicador_municipio e controle_execucao (D21).
- tudo: dimensoes + fato + controle, numa transação só.
Em qualquer erro, a transação é desfeita e nada fica gravado.
"""

import argparse
import logging
import sys
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from brasil_em_dados.config import ARQUIVO_CONTROLE, PASTA_RAW
from brasil_em_dados.db import engine_app
from brasil_em_dados.extract.erros import ErroValidacao
from brasil_em_dados.load import controle, dimensoes, fato
from brasil_em_dados.load.upsert import ErroCarga, Resumo
from brasil_em_dados.logs import configurar_logging
from brasil_em_dados.transform.dimensoes import ErroTransformacao

# Nome fixo: com `python -m`, __name__ vira "__main__" e o log ficaria fora de "brasil_em_dados".
logger = logging.getLogger("brasil_em_dados.load.cli")

DIMENSOES, FATO, TUDO = "dimensoes", "fato", "tudo"
ALVOS = (DIMENSOES, FATO, TUDO)


def executar(alvo: str, engine: Engine, pasta_raw: Path = PASTA_RAW,
             arquivo_controle: Path = ARQUIVO_CONTROLE) -> list[Resumo]:
    """Carrega o alvo numa transação só; a preparação das dimensões vem antes dela."""
    linhas_dimensoes = None
    if alvo in (DIMENSOES, TUDO):
        municipios, _arquivo = dimensoes.ler_municipios_da_raw(pasta_raw)
        linhas_dimensoes = dimensoes.preparar_linhas(municipios)
    with engine.begin() as conexao:
        resumos: list[Resumo] = []
        if linhas_dimensoes is not None:
            resumos += dimensoes.carregar_dimensoes(conexao, linhas_dimensoes)
        if alvo in (FATO, TUDO):
            resumos += fato.carregar_fato(conexao, pasta_raw)
            resumos.append(controle.carregar_controle(conexao, arquivo_controle))
    return resumos


def main(argv: list[str] | None = None, engine: Engine | None = None) -> int:
    """Executa a carga pedida; devolve 0 em sucesso e 1 em erro (transação desfeita)."""
    parser = argparse.ArgumentParser(prog="python -m brasil_em_dados.load",
                                     description="Carga na SILVER (bed_app).")
    parser.add_argument("alvo", choices=ALVOS, help="o que carregar")
    args = parser.parse_args(argv)
    configurar_logging()
    engine = engine or engine_app()
    try:
        resumos = executar(args.alvo, engine)
    except (ErroCarga, ErroTransformacao, ErroValidacao, SQLAlchemyError) as exc:
        logger.error("Carga não feita; transação desfeita. %s", exc)
        return 1
    finally:
        engine.dispose()
    logger.info("Resumo da carga (%s):", args.alvo)
    for resumo in resumos:
        logger.info("  %s", resumo.texto())
    return 0


if __name__ == "__main__":
    sys.exit(main())
