"""Carga das dimensões da SILVER (D20): RAW + catálogo → silver.dim_*, como bed_app.

- dim_municipio vem da última coleta válida de ibge_localidades_sc na RAW, revalidada.
- dim_indicador e dim_serie vêm do catálogo (fonte única).
- As linhas são montadas ANTES de abrir a transação (preparar_linhas).
- Upsert idempotente (load.upsert); nada é apagado.
- Atributos que mudam o sentido da fato (fator, unidade, indicador da série, tipo de medida)
  não podem ser alterados numa linha existente: a carga é recusada (ErroCarga).
"""

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import Connection

from brasil_em_dados.config import PASTA_RAW
from brasil_em_dados.extract.conteudo import COD_LOCALIDADES, validar_localidades
from brasil_em_dados.extract.erros import ErroValidacao
from brasil_em_dados.extract.raw import ultima_coleta_valida
from brasil_em_dados.load.upsert import (  # noqa: F401  (reexportados para quem usa este módulo)
    Classificacao,
    ErroCarga,
    EspecTabela,
    Linha,
    Mudanca,
    Resumo,
    classificar,
    erro_mudanca_proibida,
    upsert,
)
from brasil_em_dados.transform.dimensoes import (
    COLUNAS_DIM_INDICADOR,
    COLUNAS_DIM_MUNICIPIO,
    COLUNAS_DIM_SERIE,
    linhas_dim_indicador,
    linhas_dim_municipio,
    linhas_dim_serie,
)

logger = logging.getLogger("brasil_em_dados.load.dimensoes")

# Ordem de carga respeita as FKs: dim_serie depende de dim_indicador.
DIM_INDICADOR = EspecTabela(
    "silver.dim_indicador", ("codigo_indicador",), COLUNAS_DIM_INDICADOR,
    imutaveis=("tipo_medida", "unidade_armazenada"),
    orientacao_imutavel=("Se o indicador mudou de fato, crie um novo codigo_indicador no "
                         "catálogo em vez de alterar o existente."))
DIM_SERIE = EspecTabela(
    "silver.dim_serie", ("cod_serie",), COLUNAS_DIM_SERIE,
    imutaveis=("fator_conversao", "unidade_origem", "codigo_indicador"),
    orientacao_imutavel=("Se a série mudou de fato, crie um novo cod_serie no catálogo em "
                         "vez de alterar o existente."))
DIM_MUNICIPIO = EspecTabela("silver.dim_municipio", ("cod_municipio",), COLUNAS_DIM_MUNICIPIO)


def ler_municipios_da_raw(pasta_raw: Path = PASTA_RAW) -> tuple[list[dict[str, Any]], Path]:
    """Lê e revalida a última coleta válida de municípios; devolve os dados e o arquivo."""
    ultima = ultima_coleta_valida(pasta_raw, COD_LOCALIDADES)
    if ultima is None:
        raise ErroCarga(f"Nenhuma coleta válida de {COD_LOCALIDADES} na RAW; colete antes")
    arquivo, _meta = ultima
    try:
        municipios = json.loads(arquivo.read_bytes())
        validar_localidades(municipios)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, ErroValidacao) as exc:
        raise ErroCarga(f"Coleta de municípios inválida ({arquivo}): {exc}") from exc
    logger.info("Municípios lidos de %s", arquivo)
    return municipios, arquivo


def preparar_linhas(municipios: list[dict[str, Any]]) -> list[tuple[EspecTabela, list[Linha]]]:
    """Monta as linhas das três dimensões, na ordem de carga (lógica pura)."""
    return [
        (DIM_INDICADOR, linhas_dim_indicador()),
        (DIM_SERIE, linhas_dim_serie()),
        (DIM_MUNICIPIO, linhas_dim_municipio(municipios)),
    ]


def carregar_dimensoes(conexao: Connection,
                       linhas_por_tabela: list[tuple[EspecTabela, list[Linha]]]) -> list[Resumo]:
    """Carrega as dimensões, em ordem, na transação aberta em `conexao`."""
    return [upsert(conexao, espec, linhas) for espec, linhas in linhas_por_tabela]
