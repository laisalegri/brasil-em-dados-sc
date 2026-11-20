"""Linha de comando da verificação.

Uso: python -m brasil_em_dados.verificacao [--coleta] [--carga] [--gold]

Sem flags, roda só o pytest. Códigos de saída:

- 0: todos os passos passaram e o agente entregou a análise;
- 1: algum passo falhou, o agente não entregou a análise ou o relatório já existia;
- 2: a trava de credenciais parou a execução (nada roda) ou a sessão não usou o login do plano;
- 3: a sessão do agente recebeu ferramentas inesperadas ou outro modelo.
"""

import argparse
import asyncio
import logging
import os
import sys
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Engine

from brasil_em_dados.config import PASTA_CONSULTAS_VERIFICACAO, PASTA_REPORTS, RAIZ_PROJETO
from brasil_em_dados.db import ErroConfiguracao, engine_readonly, ler_ambiente
from brasil_em_dados.logs import configurar_logging
from brasil_em_dados.verificacao import agente as modulo_agente
from brasil_em_dados.verificacao import executor, relatorio
from brasil_em_dados.verificacao.ferramentas import Contexto, ErroCatalogo, ler_catalogo
from brasil_em_dados.verificacao.seguranca import (
    ErroCredencial,
    exigir_login_do_plano,
    proteger_logs,
    segredos_do_banco,
)

logger = logging.getLogger("brasil_em_dados.verificacao.cli")

SAIDA_OK, SAIDA_FALHA, SAIDA_CREDENCIAL, SAIDA_FERRAMENTAS = 0, 1, 2, 3


def montar_prompt(carimbo: str, flags: list[str], resultados: list[executor.ResultadoPasso]) -> str:
    """Pedido ao agente, com a situação de cada passo decidida pelo executor."""
    linhas = [f"Verificação {carimbo} (UTC). Comando: {relatorio.comando(flags)}.",
              "Situação dos passos, decidida pelo executor:"]
    linhas += [f"- {r.passo.nome}: {r.situacao} (usuário do banco: {r.passo.usuario_banco})"
               for r in resultados]
    linhas.append("Faça a verificação seguindo o roteiro e entregue a análise com "
                  "entregar_relatorio.")
    return "\n".join(linhas)


def _engine_leitura(criar: Callable[[], Engine]) -> Engine | None:
    try:
        return criar()
    except ErroConfiguracao as exc:
        logger.error("Banco não configurado para leitura; as consultas do agente vão falhar. %s", exc)
        return None


def _caminho_legivel(pasta: Path) -> str:
    return pasta.relative_to(RAIZ_PROJETO).as_posix() if pasta.is_relative_to(RAIZ_PROJETO) \
        else str(pasta)


def _rodar_agente(contexto: Contexto, prompt: str, criar_cliente: Callable[[Any], Any],
                  ambiente: Mapping[str, str]) -> tuple[modulo_agente.ResultadoAgente, int]:
    """Roda o agente; erros viram resultado (o relatório sai mesmo assim) e código de saída."""
    try:
        resultado = asyncio.run(modulo_agente.executar_agente(contexto, prompt, criar_cliente,
                                                              ambiente))
        return resultado, SAIDA_OK
    except modulo_agente.ErroOrigemDaChave as exc:
        return exc.resultado, SAIDA_CREDENCIAL
    except modulo_agente.ErroFerramentasInesperadas as exc:
        return exc.resultado, SAIDA_FERRAMENTAS
    except Exception as exc:  # o log passa pelo filtro de segredos
        logger.exception("Agente não concluiu")
        return modulo_agente.ResultadoAgente(situacao="erro",
                                             erro=f"{type(exc).__name__}: {exc}"), SAIDA_OK


def main(argv: list[str] | None = None, *, ambiente: Mapping[str, str] | None = None,
         ler_ambiente_banco: Callable[[], Mapping[str, str]] = ler_ambiente,
         rodar: executor.Rodar = executor.rodar_subprocesso,
         criar_engine: Callable[[], Engine] = engine_readonly,
         criar_cliente: Callable[[Any], Any] | None = None,
         pasta_reports: Path = PASTA_REPORTS,
         pasta_consultas: Path = PASTA_CONSULTAS_VERIFICACAO,
         agora: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> int:
    """Executa a verificação e grava o relatório; devolve o código de saída (ver docstring)."""
    parser = argparse.ArgumentParser(prog="python -m brasil_em_dados.verificacao",
                                     description="Verificação do pipeline com relatório do agente.")
    for passo in executor.PASSOS_DO_PIPELINE:
        parser.add_argument(f"--{passo.nome}", action="store_true",
                            help=f"roda também: {passo.comando} (usuário: {passo.usuario_banco})")
    args = parser.parse_args(argv)
    flags = [p.nome for p in executor.PASSOS_DO_PIPELINE if getattr(args, p.nome)]
    ambiente = os.environ if ambiente is None else ambiente
    segredos = segredos_do_banco(ler_ambiente_banco())
    configurar_logging()
    proteger_logs(segredos)  # nada vai para o console ou para logs/ com URL de conexão ou senha

    try:
        exigir_login_do_plano(ambiente)  # antes de qualquer passo: nada roda se a trava parar
        catalogo = ler_catalogo(pasta_consultas)
    except ErroCredencial as exc:
        logger.error("%s", exc)
        return SAIDA_CREDENCIAL
    except ErroCatalogo as exc:
        logger.error("Catálogo de consultas inválido: %s", exc)
        return SAIDA_FALHA

    carimbo = agora().strftime(relatorio.FORMATO_CARIMBO)
    caminho = relatorio.caminho_relatorio(pasta_reports, carimbo)
    pasta_execucao = pasta_reports / f"execucao_{carimbo}"
    existentes = [p.name for p in (caminho, pasta_execucao) if p.exists()]
    if existentes:
        logger.error("Já existe %s; nada será sobrescrito.", ", ".join(existentes))
        return SAIDA_FALHA

    resultados = executor.executar(flags, pasta_execucao, segredos, rodar)

    engine = _engine_leitura(criar_engine)
    contexto = Contexto(carimbo, resultados, catalogo, pasta_reports, engine, segredos)
    try:
        resultado_agente, codigo = _rodar_agente(
            contexto, montar_prompt(carimbo, flags, resultados),
            criar_cliente or modulo_agente._cliente_padrao, ambiente)
    finally:
        if engine is not None:
            engine.dispose()

    texto = relatorio.montar(carimbo, flags, resultados, resultado_agente, contexto.analise,
                             _caminho_legivel(pasta_execucao), segredos)
    try:
        relatorio.gravar(caminho, texto)
    except FileExistsError:
        logger.error("O relatório %s apareceu durante a execução; não foi sobrescrito.",
                     caminho.name)
        return SAIDA_FALHA
    logger.info("Relatório gravado: %s", caminho)

    if codigo == SAIDA_OK and (any(r.situacao != "ok" for r in resultados)
                               or contexto.analise is None or resultado_agente.erro):
        codigo = SAIDA_FALHA
    return codigo


if __name__ == "__main__":
    sys.exit(main())
