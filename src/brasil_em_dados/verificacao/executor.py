"""Executor determinístico da verificação: roda os passos e guarda as saídas.

O pytest roda sempre. Coleta, carga e GOLD só rodam com as flags --coleta, --carga e --gold,
que só a autora passa; o agente nunca dispara um passo. Se um passo do pipeline falhar, os
passos seguintes do pipeline não rodam, mas o pytest roda mesmo assim. As saídas vão para
reports/execucao_<carimbo>/<passo>.txt, já sem URL de conexão nem senha.
"""

import logging
import os
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from brasil_em_dados.config import RAIZ_PROJETO
from brasil_em_dados.verificacao.seguranca import limpar_texto

logger = logging.getLogger("brasil_em_dados.verificacao.executor")

TIMEOUT_PASSO_S = 30 * 60


@dataclass(frozen=True)
class Passo:
    """Um passo da verificação: comando (depois de `python`) e usuário do banco que ele usa."""

    nome: str
    argumentos: tuple[str, ...]
    usuario_banco: str

    @property
    def comando(self) -> str:
        """Comando legível, para o relatório."""
        return "python " + " ".join(self.argumentos)


COLETA = Passo("coleta", ("-m", "brasil_em_dados.extract", "todas"), "nenhum (grava só na RAW)")
CARGA = Passo("carga", ("-m", "brasil_em_dados.load", "tudo"), "bed_app")
GOLD = Passo("gold", ("-m", "brasil_em_dados.db.aplicar_gold"), "bed_app")
PYTEST = Passo("pytest", ("-m", "pytest", "-q", "-rfEs", "--tb=short"),
               "bed_app e bed_readonly (testes de integração, em transações desfeitas)")
PASSOS_DO_PIPELINE = (COLETA, CARGA, GOLD)


@dataclass(frozen=True)
class Saida:
    """Saída de um comando: código de retorno (None em timeout) e texto (stdout + stderr)."""

    codigo: int | None
    texto: str


@dataclass(frozen=True)
class ResultadoPasso:
    """O que aconteceu com um passo."""

    passo: Passo
    executado: bool
    codigo: int | None = None
    duracao_s: float | None = None
    arquivo_saida: Path | None = None
    motivo: str | None = None  # por que não rodou, ou por que falhou sem código

    @property
    def situacao(self) -> str:
        """'ok', 'falhou' ou 'não executado'."""
        if not self.executado:
            return "não executado"
        return "ok" if self.codigo == 0 else "falhou"


Rodar = Callable[[tuple[str, ...]], Saida]


def rodar_subprocesso(argumentos: tuple[str, ...]) -> Saida:
    """Roda `python <argumentos>` na raiz do projeto, com o Python do ambiente atual."""
    ambiente = {**os.environ, "PYTHONUTF8": "1"}  # saída em UTF-8 também no Windows
    try:
        processo = subprocess.run(
            [sys.executable, *argumentos], cwd=RAIZ_PROJETO, env=ambiente, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT_PASSO_S)
    except subprocess.TimeoutExpired as exc:
        parcial = _texto(exc.stdout) + _texto(exc.stderr)
        return Saida(None, parcial + f"\n[tempo esgotado após {TIMEOUT_PASSO_S} s]")
    return Saida(processo.returncode, processo.stdout + processo.stderr)


def _texto(saida: str | bytes | None) -> str:
    """Saída parcial do timeout: pode vir como texto, bytes ou None, conforme a plataforma."""
    if saida is None:
        return ""
    return saida.decode("utf-8", errors="replace") if isinstance(saida, bytes) else saida


def passos_pedidos(flags: Iterable[str]) -> list[Passo]:
    """Passos na ordem do pipeline, só os pedidos por flag, e o pytest no fim."""
    pedidos = set(flags)
    desconhecidos = pedidos - {p.nome for p in PASSOS_DO_PIPELINE}
    if desconhecidos:
        raise ValueError(f"Flags desconhecidas: {sorted(desconhecidos)}")
    return [p for p in PASSOS_DO_PIPELINE if p.nome in pedidos] + [PYTEST]


def executar(flags: Iterable[str], pasta_execucao: Path, segredos: Iterable[str] = (),
             rodar: Rodar = rodar_subprocesso) -> list[ResultadoPasso]:
    """Roda os passos pedidos e grava a saída limpa de cada um em `pasta_execucao`.

    A pasta não pode existir: saídas de uma execução anterior nunca são sobrescritas.
    """
    segredos = list(segredos)
    pasta_execucao.mkdir(parents=True, exist_ok=False)
    resultados: list[ResultadoPasso] = []
    pipeline_falhou = False
    for passo in passos_pedidos(flags):
        if pipeline_falhou and passo is not PYTEST:
            logger.warning("Passo %s não executado: um passo anterior do pipeline falhou", passo.nome)
            resultados.append(ResultadoPasso(passo, executado=False,
                                             motivo="um passo anterior do pipeline falhou"))
            continue
        logger.info("Passo %s: %s (usuário do banco: %s)", passo.nome, passo.comando,
                    passo.usuario_banco)
        inicio = time.monotonic()
        saida = rodar(passo.argumentos)
        duracao = time.monotonic() - inicio
        arquivo = pasta_execucao / f"{passo.nome}.txt"
        arquivo.write_text(limpar_texto(saida.texto, segredos), encoding="utf-8")
        resultado = ResultadoPasso(passo, executado=True, codigo=saida.codigo, duracao_s=duracao,
                                   arquivo_saida=arquivo,
                                   motivo="tempo esgotado" if saida.codigo is None else None)
        logger.info("Passo %s: %s em %.1f s", passo.nome, resultado.situacao, duracao)
        if resultado.situacao != "ok" and passo is not PYTEST:
            pipeline_falhou = True
        resultados.append(resultado)
    return resultados
