"""Carga da fato_indicador_municipio (D21): RAW → silver, como bed_app.

- dim_serie e dim_municipio são lidas do banco (já carregadas no D20).
- Para cada série, a última coleta válida na RAW é revalidada (mesmas regras da coleta) e
  transformada (transform.fato); data_coleta = coletado_em do .meta.json usado.
- Upsert em lote pela chave (cod_municipio, codigo_indicador, ano). Só valor e sinal definem
  se a linha mudou: data_coleta acompanha a mudança e significa "a coleta que trouxe este
  valor". cod_serie não pode mudar numa linha existente. Nada é apagado.
"""

import json
import logging
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, text

from brasil_em_dados.config import PASTA_RAW
from brasil_em_dados.extract.conteudo import validar_conteudo
from brasil_em_dados.extract.erros import ErroValidacao
from brasil_em_dados.extract.raw import ultima_coleta_valida
from brasil_em_dados.load.upsert import (
    Chave,
    Classificacao,
    ErroCarga,
    EspecTabela,
    Linha,
    Resumo,
    aplicar_upsert,
)
from brasil_em_dados.transform.fato import COLUNAS_FATO, SerieFato, linhas_da_serie

logger = logging.getLogger("brasil_em_dados.load.fato")

FATO = EspecTabela(
    "silver.fato_indicador_municipio", ("cod_municipio", "codigo_indicador", "ano"),
    COLUNAS_FATO,
    imutaveis=("cod_serie",),
    comparadas=("valor", "sinal_origem"),
    orientacao_imutavel=("Cada (indicador, ano) vem de uma única série; trocar a série de um "
                         "valor já carregado exige uma decisão registrada em docs/decisoes.md."))


def ler_series_do_banco(conexao: Connection) -> list[SerieFato]:
    """Séries da dim_serie, na ordem do código."""
    linhas = conexao.execute(text(
        "SELECT cod_serie, codigo_indicador, fonte, variavel_ou_indicador, fator_conversao "
        "FROM silver.dim_serie ORDER BY cod_serie")).all()
    if not linhas:
        raise ErroCarga("silver.dim_serie vazia; rode antes: python -m brasil_em_dados.load "
                        "dimensoes")
    return [SerieFato(l.cod_serie, l.codigo_indicador, l.fonte, l.variavel_ou_indicador,
                      Decimal(l.fator_conversao)) for l in linhas]


def ler_cadastro_do_banco(conexao: Connection) -> list[str]:
    """Códigos de 7 dígitos da dim_municipio."""
    codigos = list(conexao.execute(text(
        "SELECT cod_municipio FROM silver.dim_municipio ORDER BY cod_municipio")).scalars())
    if not codigos:
        raise ErroCarga("silver.dim_municipio vazia; rode antes: python -m brasil_em_dados.load "
                        "dimensoes")
    return codigos


def ler_coleta(pasta_raw: Path, cod_serie: str) -> tuple[Any, datetime, Path]:
    """Dados, coletado_em e arquivo da última coleta válida da série."""
    ultima = ultima_coleta_valida(pasta_raw, cod_serie)
    if ultima is None:
        raise ErroCarga(f"Nenhuma coleta válida de {cod_serie} na RAW; colete antes")
    arquivo, meta = ultima
    try:
        dados = json.loads(arquivo.read_bytes())
        coletado_em = datetime.fromisoformat(meta["coletado_em"])
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, KeyError, ValueError,
            TypeError) as exc:
        raise ErroCarga(f"Coleta de {cod_serie} ilegível ({arquivo}): {exc}") from exc
    if coletado_em.tzinfo is None:
        raise ErroCarga(f"{arquivo}: coletado_em sem fuso horário")
    return dados, coletado_em, arquivo


def preparar_fato(conexao: Connection, pasta_raw: Path = PASTA_RAW
                  ) -> list[tuple[SerieFato, list[Linha]]]:
    """Lê, revalida e transforma a última coleta de cada série da dim_serie."""
    cadastro = ler_cadastro_do_banco(conexao)
    preparadas = []
    for serie in ler_series_do_banco(conexao):
        dados, coletado_em, arquivo = ler_coleta(pasta_raw, serie.cod_serie)
        try:
            validar_conteudo(serie.cod_serie, dados, cadastro=cadastro)
        except ErroValidacao as exc:
            raise ErroCarga(f"Coleta de {serie.cod_serie} reprovada na revalidação "
                            f"({arquivo}): {exc}") from exc
        linhas = linhas_da_serie(dados, serie, cadastro, coletado_em)
        logger.info("%s: %d linhas de %s (coletado em %s)", serie.cod_serie, len(linhas),
                    arquivo.name, coletado_em.isoformat())
        preparadas.append((serie, linhas))
    return preparadas


def resumir_por_serie(classificacao: Classificacao, linhas: list[Linha],
                      series: list[str]) -> list[Resumo]:
    """Contagens agrupadas pela série de origem de cada linha."""
    serie_da_chave: dict[Chave, str] = {
        tuple(l[c] for c in FATO.chave): l["cod_serie"] for l in linhas}
    contar = lambda chaves: Counter(serie_da_chave[c] for c in chaves)  # noqa: E731
    inseridas, atualizadas = contar(classificacao.inseridas), contar(classificacao.atualizadas)
    inalteradas = contar(classificacao.inalteradas)
    so_no_banco = Counter(l["cod_serie"] for l in classificacao.so_no_banco.values())
    # Séries que só existem no banco (fora da dim_serie atual) também aparecem no resumo.
    todas = list(series) + sorted(set(so_no_banco) - set(series))
    return [Resumo(f"fato {s}", inseridas[s], atualizadas[s], inalteradas[s], so_no_banco[s])
            for s in todas]


def carregar_fato(conexao: Connection, pasta_raw: Path = PASTA_RAW) -> list[Resumo]:
    """Prepara todas as séries e grava a fato num upsert só; devolve o resumo por série."""
    preparadas = preparar_fato(conexao, pasta_raw)
    linhas = [linha for _serie, linhas_serie in preparadas for linha in linhas_serie]
    classificacao = aplicar_upsert(conexao, FATO, linhas)
    return resumir_por_serie(classificacao, linhas, [s.cod_serie for s, _ in preparadas])
