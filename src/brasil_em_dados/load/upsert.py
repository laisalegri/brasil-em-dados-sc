"""Upsert idempotente em lote, compartilhado pelas cargas da SILVER (D20, D21).

- Compara a fonte com o banco ANTES de gravar: inseridas, atualizadas (com o que mudou),
  inalteradas, mudanças proibidas em colunas imutáveis e linhas que só existem no banco.
- Só as colunas "comparadas" definem se a linha mudou. As demais colunas não-chave são gravadas
  junto quando a linha muda (na fato, data_coleta acompanha valor e sinal).
- Linha igual não é reescrita (WHERE ... IS DISTINCT FROM); nada é apagado.
- As contagens são conferidas contra o que o banco devolve (RETURNING (xmax = 0)).
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, text

logger = logging.getLogger("brasil_em_dados.load.upsert")

_IDENTIFICADOR = re.compile(r"^[a-z_][a-z0-9_]*$")
_TABELA = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$")
MAX_EXEMPLOS = 10
TAMANHO_LOTE = 1000
MAX_PARAMETROS = 65535  # limite de parâmetros por comando no protocolo do PostgreSQL

Linha = dict[str, Any]
Chave = tuple[Any, ...]


class ErroCarga(Exception):
    """Falha na carga; a transação é desfeita e nada fica gravado."""


@dataclass(frozen=True)
class EspecTabela:
    """Tabela de destino.

    `comparadas`: colunas que definem se a linha mudou (padrão: todas as não-chave).
    `imutaveis`: colunas que não podem mudar numa linha existente (mudança = ErroCarga).
    """

    nome: str
    chave: tuple[str, ...]
    colunas: tuple[str, ...]
    imutaveis: tuple[str, ...] = ()
    orientacao_imutavel: str = ""
    comparadas: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        # Os nomes entram no SQL por f-string: só identificadores simples são aceitos.
        if not _TABELA.fullmatch(self.nome):
            raise ValueError(f"Nome de tabela inválido: {self.nome!r}")
        for coluna in (*self.chave, *self.colunas, *self.imutaveis, *(self.comparadas or ())):
            if not _IDENTIFICADOR.fullmatch(coluna):
                raise ValueError(f"Nome de coluna inválido: {coluna!r}")
        if not {*self.chave, *self.imutaveis, *(self.comparadas or ())} <= set(self.colunas):
            raise ValueError(f"{self.nome}: chave, imutáveis e comparadas precisam estar "
                             "entre as colunas")

    @property
    def nao_chave(self) -> tuple[str, ...]:
        return tuple(c for c in self.colunas if c not in self.chave)

    @property
    def colunas_comparadas(self) -> tuple[str, ...]:
        return self.nao_chave if self.comparadas is None else self.comparadas


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
    inalteradas: list[Chave]
    proibidas: list[Mudanca]
    so_no_banco: dict[Chave, Linha]


@dataclass(frozen=True)
class Resumo:
    """Resultado da carga de uma tabela (ou de uma série da fato)."""

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


def chave_de(linha: Linha, espec: EspecTabela) -> Chave:
    """Valores da chave primária da linha."""
    return tuple(linha[c] for c in espec.chave)


# --- comparação (lógica pura) -------------------------------------------------------------------

def classificar(espec: EspecTabela, no_banco: dict[Chave, Linha], linhas: list[Linha]
                ) -> Classificacao:
    """Separa a fonte em inseridas, atualizadas e inalteradas; lista mudanças proibidas."""
    chaves = [chave_de(linha, espec) for linha in linhas]
    repetidas = sorted(c for c, n in Counter(chaves).items() if n > 1)
    if repetidas:
        raise ErroCarga(f"{espec.nome}: chaves repetidas na fonte: {repetidas[:MAX_EXEMPLOS]}")
    inseridas: list[Chave] = []
    atualizadas: dict[Chave, list[Mudanca]] = {}
    inalteradas: list[Chave] = []
    proibidas: list[Mudanca] = []
    for chave, linha in zip(chaves, linhas):
        atual = no_banco.get(chave)
        if atual is None:
            inseridas.append(chave)
            continue
        # Python e PostgreSQL concordam: Decimal("1000") == 1000, numeric 1000 = 1000.
        proibidas += [Mudanca(chave, c, atual[c], linha[c])
                      for c in espec.imutaveis if atual[c] != linha[c]]
        mudancas = [Mudanca(chave, c, atual[c], linha[c])
                    for c in espec.colunas_comparadas if atual[c] != linha[c]]
        if mudancas:
            atualizadas[chave] = mudancas
        else:
            inalteradas.append(chave)
    fonte = set(chaves)
    so_no_banco = {chave: linha for chave, linha in sorted(no_banco.items()) if chave not in fonte}
    return Classificacao(inseridas, atualizadas, inalteradas, proibidas, so_no_banco)


def erro_mudanca_proibida(espec: EspecTabela, proibidas: list[Mudanca]) -> ErroCarga:
    """Mensagem com o que mudou (antigo → novo) e a orientação da tabela."""
    detalhes = "; ".join(m.texto() for m in proibidas[:MAX_EXEMPLOS])
    return ErroCarga(f"{espec.nome}: mudança não permitida em linha existente "
                     f"({', '.join(espec.imutaveis)}): {detalhes}. {espec.orientacao_imutavel}")


# --- gravação -----------------------------------------------------------------------------------

def sql_upsert(espec: EspecTabela, n_linhas: int) -> str:
    """INSERT de várias linhas com ON CONFLICT que só atualiza quando algo comparado mudou."""
    colunas = ", ".join(espec.colunas)
    valores = ", ".join(
        "(" + ", ".join(f":{c}_{i}" for c in espec.colunas) + ")" for i in range(n_linhas))
    atribuicoes = ", ".join(f"{c} = EXCLUDED.{c}" for c in espec.nao_chave)
    atuais = ", ".join(f"{espec.nome}.{c}" for c in espec.colunas_comparadas)
    novos = ", ".join(f"EXCLUDED.{c}" for c in espec.colunas_comparadas)
    # ROW(...) também funciona quando há uma coluna comparada só.
    # xmax = 0 identifica a linha recém-inserida (artifício conhecido do PostgreSQL).
    return (f"INSERT INTO {espec.nome} ({colunas}) VALUES {valores} "
            f"ON CONFLICT ({', '.join(espec.chave)}) DO UPDATE SET {atribuicoes} "
            f"WHERE ROW({atuais}) IS DISTINCT FROM ROW({novos}) "
            f"RETURNING {', '.join(espec.chave)}, (xmax = 0) AS inserida")


def tamanho_lote(espec: EspecTabela) -> int:
    """Linhas por INSERT sem passar do limite de parâmetros (colunas × linhas)."""
    return max(1, min(TAMANHO_LOTE, MAX_PARAMETROS // len(espec.colunas)))


def _parametros(espec: EspecTabela, lote: list[Linha]) -> dict[str, Any]:
    return {f"{c}_{i}": linha[c] for i, linha in enumerate(lote) for c in espec.colunas}


def linhas_no_banco(conexao: Connection, espec: EspecTabela) -> dict[Chave, Linha]:
    """Todas as linhas da tabela, indexadas pela chave."""
    resultado = conexao.execute(text(f"SELECT {', '.join(espec.colunas)} FROM {espec.nome}"))
    return {chave_de(dict(linha._mapping), espec): dict(linha._mapping) for linha in resultado}


def aplicar_upsert(conexao: Connection, espec: EspecTabela, linhas: list[Linha]) -> Classificacao:
    """Classifica, recusa mudança proibida, grava em lote e confere as contagens."""
    # Trava contra outra carga simultânea entre a leitura e a gravação (leituras continuam).
    conexao.execute(text(f"LOCK TABLE {espec.nome} IN SHARE ROW EXCLUSIVE MODE"))
    classificacao = classificar(espec, linhas_no_banco(conexao, espec), linhas)
    if classificacao.proibidas:
        raise erro_mudanca_proibida(espec, classificacao.proibidas)

    # Só o que mudou vai ao INSERT: linha inalterada não gasta sequência nem ida ao banco.
    a_gravar = set(classificacao.inseridas) | set(classificacao.atualizadas)
    pendentes = [linha for linha in linhas if chave_de(linha, espec) in a_gravar]
    inseridas_banco: set[Chave] = set()
    atualizadas_banco: set[Chave] = set()
    lote_max = tamanho_lote(espec)
    for inicio in range(0, len(pendentes), lote_max):
        lote = pendentes[inicio:inicio + lote_max]
        resultado = conexao.execute(text(sql_upsert(espec, len(lote))), _parametros(espec, lote))
        for retorno in resultado.all():
            chave = tuple(getattr(retorno, c) for c in espec.chave)
            (inseridas_banco if retorno.inserida else atualizadas_banco).add(chave)
    # Conferência chave a chave: o banco gravou exatamente o que a comparação previu.
    if (inseridas_banco, atualizadas_banco) != (set(classificacao.inseridas),
                                                set(classificacao.atualizadas)):
        raise ErroCarga(
            f"{espec.nome}: contagem divergente (banco: {len(inseridas_banco)} inseridas e "
            f"{len(atualizadas_banco)} atualizadas; esperado: {len(classificacao.inseridas)} e "
            f"{len(classificacao.atualizadas)})")

    for mudancas in classificacao.atualizadas.values():
        logger.info("%s: atualizada %s", espec.nome, "; ".join(m.texto() for m in mudancas))
    if classificacao.so_no_banco:
        logger.warning("%s: %d linha(s) no banco que não estão na fonte; mantidas (nada é "
                       "apagado): %s", espec.nome, len(classificacao.so_no_banco),
                       list(classificacao.so_no_banco)[:MAX_EXEMPLOS])
    return classificacao


def resumir(tabela: str, classificacao: Classificacao) -> Resumo:
    """Resumo com as contagens da classificação."""
    return Resumo(tabela, len(classificacao.inseridas), len(classificacao.atualizadas),
                  len(classificacao.inalteradas), len(classificacao.so_no_banco))


def upsert(conexao: Connection, espec: EspecTabela, linhas: list[Linha]) -> Resumo:
    """Upsert de uma tabela inteira, com resumo."""
    return resumir(espec.nome, aplicar_upsert(conexao, espec, linhas))
