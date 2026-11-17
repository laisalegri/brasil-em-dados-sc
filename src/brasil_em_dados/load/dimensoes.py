"""Carga das dimensões da SILVER (D20): RAW + catálogo → silver.dim_*, como bed_app.

- dim_municipio vem da última coleta válida de ibge_localidades_sc na RAW, revalidada.
- dim_indicador e dim_serie vêm do catálogo (fonte única).
- As linhas são montadas ANTES de abrir a transação; a carga roda numa transação só.
- Upsert idempotente (INSERT ... ON CONFLICT DO UPDATE só quando algo mudou).
- Nada é apagado: linha que está no banco e não está na fonte só gera aviso.
- Atributos que mudam o sentido da fato (fator, unidade, indicador da série, tipo de medida)
  não podem ser alterados numa linha existente: a carga é recusada (ErroCarga).
"""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, Engine, text

from brasil_em_dados.config import PASTA_RAW
from brasil_em_dados.extract.conteudo import COD_LOCALIDADES, validar_localidades
from brasil_em_dados.extract.erros import ErroValidacao
from brasil_em_dados.extract.raw import ultima_coleta_valida
from brasil_em_dados.transform.dimensoes import (
    COLUNAS_DIM_INDICADOR,
    COLUNAS_DIM_MUNICIPIO,
    COLUNAS_DIM_SERIE,
    linhas_dim_indicador,
    linhas_dim_municipio,
    linhas_dim_serie,
)

logger = logging.getLogger("brasil_em_dados.load.dimensoes")

_IDENTIFICADOR = re.compile(r"^[a-z_][a-z0-9_]*$")
_TABELA = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$")
MAX_EXEMPLOS = 10

Linha = dict[str, Any]
Chave = tuple[Any, ...]


class ErroCarga(Exception):
    """Falha na carga; a transação é desfeita e nada fica gravado."""


@dataclass(frozen=True)
class EspecTabela:
    """Tabela de destino: nome qualificado, chave primária, colunas e colunas imutáveis."""

    nome: str
    chave: tuple[str, ...]
    colunas: tuple[str, ...]
    imutaveis: tuple[str, ...] = ()
    orientacao_imutavel: str = ""

    def __post_init__(self) -> None:
        # Os nomes entram no SQL por f-string: só identificadores simples são aceitos.
        if not _TABELA.fullmatch(self.nome):
            raise ValueError(f"Nome de tabela inválido: {self.nome!r}")
        for coluna in (*self.chave, *self.colunas, *self.imutaveis):
            if not _IDENTIFICADOR.fullmatch(coluna):
                raise ValueError(f"Nome de coluna inválido: {coluna!r}")
        if not set(self.chave) <= set(self.colunas) or not set(self.imutaveis) <= set(self.colunas):
            raise ValueError(f"{self.nome}: chave e imutáveis precisam estar entre as colunas")


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


@dataclass(frozen=True)
class Mudanca:
    """Uma coluna que mudou numa linha existente."""

    chave: Chave
    coluna: str
    antigo: Any
    novo: Any

    def texto(self) -> str:
        return f"{'/'.join(map(str, self.chave))}.{self.coluna}: {self.antigo!r} → {self.novo!r}"


@dataclass(frozen=True)
class Classificacao:
    """Comparação entre a fonte e o banco, antes de gravar."""

    inseridas: list[Chave]
    atualizadas: dict[Chave, list[Mudanca]]
    inalteradas: int
    proibidas: list[Mudanca]
    so_no_banco: list[Chave]


@dataclass(frozen=True)
class Resumo:
    """Resultado da carga de uma tabela."""

    tabela: str
    inseridas: int
    atualizadas: int
    inalteradas: int
    so_no_banco: int = 0

    @property
    def na_fonte(self) -> int:
        return self.inseridas + self.atualizadas + self.inalteradas

    def texto(self) -> str:
        texto = (f"{self.tabela}: {self.inseridas} inseridas, {self.atualizadas} atualizadas, "
                 f"{self.inalteradas} inalteradas ({self.na_fonte} na fonte)")
        if self.so_no_banco:
            texto += f"; {self.so_no_banco} só no banco (mantidas)"
        return texto


# --- leitura da RAW e preparação (antes da transação) ------------------------------------------

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
    return municipios, arquivo


def preparar_linhas(municipios: list[dict[str, Any]]) -> list[tuple[EspecTabela, list[Linha]]]:
    """Monta as linhas das três dimensões, na ordem de carga (lógica pura)."""
    return [
        (DIM_INDICADOR, linhas_dim_indicador()),
        (DIM_SERIE, linhas_dim_serie()),
        (DIM_MUNICIPIO, linhas_dim_municipio(municipios)),
    ]


# --- comparação com o banco (lógica pura) -------------------------------------------------------

def _chave(linha: Linha, espec: EspecTabela) -> Chave:
    return tuple(linha[c] for c in espec.chave)


def classificar(espec: EspecTabela, no_banco: dict[Chave, Linha], linhas: list[Linha]
                ) -> Classificacao:
    """Separa as linhas da fonte em inseridas, atualizadas (com o que mudou) e inalteradas,
    e lista as mudanças proibidas em colunas imutáveis."""
    inseridas: list[Chave] = []
    atualizadas: dict[Chave, list[Mudanca]] = {}
    inalteradas = 0
    for linha in linhas:
        chave = _chave(linha, espec)
        atual = no_banco.get(chave)
        if atual is None:
            inseridas.append(chave)
            continue
        # Python e PostgreSQL concordam: Decimal("1000") == 1000, numeric 1000 = 1000.
        mudancas = [Mudanca(chave, c, atual[c], linha[c])
                    for c in espec.colunas if atual[c] != linha[c]]
        if mudancas:
            atualizadas[chave] = mudancas
        else:
            inalteradas += 1
    proibidas = [m for mudancas in atualizadas.values() for m in mudancas
                 if m.coluna in espec.imutaveis]
    so_no_banco = sorted(set(no_banco) - {_chave(linha, espec) for linha in linhas})
    return Classificacao(inseridas, atualizadas, inalteradas, proibidas, so_no_banco)


def erro_mudanca_proibida(espec: EspecTabela, proibidas: list[Mudanca]) -> ErroCarga:
    """Mensagem com o que mudou (antigo → novo) e a orientação da tabela."""
    detalhes = "; ".join(m.texto() for m in proibidas[:MAX_EXEMPLOS])
    return ErroCarga(f"{espec.nome}: mudança não permitida em linha existente "
                     f"({', '.join(espec.imutaveis)}): {detalhes}. {espec.orientacao_imutavel}")


# --- gravação no banco --------------------------------------------------------------------------

def _sql_upsert(espec: EspecTabela) -> str:
    colunas = ", ".join(espec.colunas)
    valores = ", ".join(f":{c}" for c in espec.colunas)
    nao_chave = [c for c in espec.colunas if c not in espec.chave]
    atribuicoes = ", ".join(f"{c} = EXCLUDED.{c}" for c in nao_chave)
    atuais = ", ".join(f"{espec.nome}.{c}" for c in nao_chave)
    novos = ", ".join(f"EXCLUDED.{c}" for c in nao_chave)
    # O WHERE evita reescrever linhas iguais: a segunda carga não toca no banco.
    # xmax = 0 identifica a linha recém-inserida (artifício conhecido do PostgreSQL).
    return (f"INSERT INTO {espec.nome} ({colunas}) VALUES ({valores}) "
            f"ON CONFLICT ({', '.join(espec.chave)}) DO UPDATE SET {atribuicoes} "
            f"WHERE ({atuais}) IS DISTINCT FROM ({novos}) RETURNING (xmax = 0) AS inserida")


def _linhas_no_banco(conexao: Connection, espec: EspecTabela) -> dict[Chave, Linha]:
    resultado = conexao.execute(text(f"SELECT {', '.join(espec.colunas)} FROM {espec.nome}"))
    return {_chave(dict(linha._mapping), espec): dict(linha._mapping) for linha in resultado}


def upsert(conexao: Connection, espec: EspecTabela, linhas: list[Linha]) -> Resumo:
    """Insere ou atualiza as linhas; recusa mudança em coluna imutável; confere as contagens."""
    # Trava contra outra carga simultânea entre a leitura e a gravação (leituras continuam).
    conexao.execute(text(f"LOCK TABLE {espec.nome} IN SHARE ROW EXCLUSIVE MODE"))
    classificacao = classificar(espec, _linhas_no_banco(conexao, espec), linhas)
    if classificacao.proibidas:
        raise erro_mudanca_proibida(espec, classificacao.proibidas)

    sql = text(_sql_upsert(espec))
    retornos = [r.inserida for linha in linhas for r in conexao.execute(sql, linha).all()]
    inseridas_banco, atualizadas_banco = retornos.count(True), retornos.count(False)
    esperado = (len(classificacao.inseridas), len(classificacao.atualizadas))
    if (inseridas_banco, atualizadas_banco) != esperado:
        raise ErroCarga(
            f"{espec.nome}: contagem divergente (banco: {inseridas_banco} inseridas e "
            f"{atualizadas_banco} atualizadas; esperado: {esperado[0]} e {esperado[1]})")

    for mudancas in list(classificacao.atualizadas.values())[:MAX_EXEMPLOS]:
        logger.info("%s: atualizada %s", espec.nome, "; ".join(m.texto() for m in mudancas))
    if classificacao.so_no_banco:
        logger.warning("%s: %d linha(s) no banco que não estão na fonte; mantidas (nada é "
                       "apagado): %s", espec.nome, len(classificacao.so_no_banco),
                       classificacao.so_no_banco[:MAX_EXEMPLOS])
    return Resumo(espec.nome, len(classificacao.inseridas), len(classificacao.atualizadas),
                  classificacao.inalteradas, len(classificacao.so_no_banco))


def carregar_dimensoes(conexao: Connection,
                       linhas_por_tabela: list[tuple[EspecTabela, list[Linha]]]) -> list[Resumo]:
    """Carrega as dimensões, em ordem, na transação aberta em `conexao`."""
    return [upsert(conexao, espec, linhas) for espec, linhas in linhas_por_tabela]


def executar(engine: Engine, pasta_raw: Path = PASTA_RAW) -> list[Resumo]:
    """Lê a RAW e monta as linhas; depois carrega tudo numa transação (em erro, nada fica)."""
    municipios, arquivo = ler_municipios_da_raw(pasta_raw)
    logger.info("Municípios lidos de %s", arquivo)
    linhas_por_tabela = preparar_linhas(municipios)
    with engine.begin() as conexao:
        return carregar_dimensoes(conexao, linhas_por_tabela)
