"""Gravação imutável na RAW e metadados de cada coleta (D11, seções 2 a 5)."""

import copy
import hashlib
import json
import logging
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brasil_em_dados.config import RAIZ_PROJETO
from brasil_em_dados.extract.catalogo import FonteColeta
from brasil_em_dados.extract.cliente_http import RespostaHTTP
from brasil_em_dados.extract.erros import ErroGravacao

logger = logging.getLogger(__name__)

SUFIXO_DADOS = ".json"
SUFIXO_META = ".meta.json"


def _em_utc(instante: datetime) -> datetime:
    if instante.tzinfo is None:
        raise ValueError("O instante precisa ter fuso horário (use UTC)")
    return instante.astimezone(timezone.utc)


def carimbo_utc(instante: datetime) -> str:
    """Formata o instante como AAAAMMDDTHHMMSSfffZ, em UTC com milissegundos."""
    utc = _em_utc(instante)
    return f"{utc:%Y%m%dT%H%M%S}{utc.microsecond // 1000:03d}Z"


def iso_utc(instante: datetime) -> str:
    """Formata o instante em ISO 8601, UTC com milissegundos e sufixo Z."""
    utc = _em_utc(instante)
    return f"{utc:%Y-%m-%dT%H:%M:%S}.{utc.microsecond // 1000:03d}Z"


def calcular_sha256(conteudo: bytes) -> str:
    """Hash SHA-256 dos bytes, em hexadecimal."""
    return hashlib.sha256(conteudo).hexdigest()


def caminhos_coleta(pasta_raw: Path, cod_serie: str, carimbo: str) -> tuple[Path, Path]:
    """Devolve (arquivo de dados, arquivo de metadados) de uma coleta."""
    pasta = pasta_raw / cod_serie
    return pasta / f"{carimbo}{SUFIXO_DADOS}", pasta / f"{carimbo}{SUFIXO_META}"


def gravar_exclusivo(destino: Path, conteudo: bytes) -> None:
    """Grava via temporário + os.link; falha se o destino existir ou se não houver hard link."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(f".{destino.name}.{uuid.uuid4().hex}.tmp")
    try:
        try:
            with open(temporario, "xb") as arquivo:
                arquivo.write(conteudo)
                arquivo.flush()
                os.fsync(arquivo.fileno())
        except OSError as exc:
            raise ErroGravacao(f"Falha ao gravar o arquivo temporário de {destino}: {exc}") from exc
        try:
            os.link(temporario, destino)
        except FileExistsError as exc:
            raise ErroGravacao(f"Destino já existe; a RAW nunca é sobrescrita: {destino}") from exc
        except (OSError, NotImplementedError, AttributeError) as exc:
            raise ErroGravacao(
                f"Não foi possível criar {destino} com os.link (o sistema de arquivos pode não "
                f"suportar hard links). A coleta foi interrompida para não arriscar sobrescrever "
                f"a RAW: {exc}"
            ) from exc
    finally:
        temporario.unlink(missing_ok=True)


def _ler_meta(arquivo_meta: Path) -> dict[str, Any] | None:
    try:
        meta = json.loads(arquivo_meta.read_bytes())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return meta if isinstance(meta, dict) else None


def _arquivo_dados_de(arquivo_meta: Path) -> Path:
    return arquivo_meta.with_name(arquivo_meta.name[: -len(SUFIXO_META)] + SUFIXO_DADOS)


def coletas_incompletas(pasta_serie: Path) -> list[Path]:
    """Arquivos de dados sem .meta.json correspondente (ignorados pela carga)."""
    if not pasta_serie.is_dir():
        return []
    incompletas = []
    for dados in sorted(pasta_serie.glob(f"*{SUFIXO_DADOS}")):
        if dados.name.startswith(".") or dados.name.endswith(SUFIXO_META):
            continue
        meta = dados.with_name(dados.name[: -len(SUFIXO_DADOS)] + SUFIXO_META)
        if not meta.exists():
            incompletas.append(dados)
    return incompletas


def ultima_coleta_valida(pasta_raw: Path, cod_serie: str) -> tuple[Path, dict[str, Any]] | None:
    """Última coleta com par completo (dados + .meta.json legível); incompletas geram aviso."""
    pasta_serie = pasta_raw / cod_serie
    for incompleta in coletas_incompletas(pasta_serie):
        logger.warning("Coleta incompleta ignorada (sem %s): %s", SUFIXO_META, incompleta)
    if not pasta_serie.is_dir():
        return None
    metas = sorted(
        (m for m in pasta_serie.glob(f"*{SUFIXO_META}") if not m.name.startswith(".")),
        reverse=True,
    )
    for arquivo_meta in metas:
        dados = _arquivo_dados_de(arquivo_meta)
        meta = _ler_meta(arquivo_meta)
        if meta is not None and dados.exists():
            return dados, meta
        logger.warning("Metadados ilegíveis ou sem arquivo de dados, ignorados: %s", arquivo_meta)
    return None


def versao_extrator(raiz: Path = RAIZ_PROJETO) -> str:
    """Hash curto do commit, com '-dirty' se houver mudanças locais; 'desconhecido' sem git."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=raiz, capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
        mudancas = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=raiz, capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "desconhecido"
    if not commit:
        return "desconhecido"
    return f"{commit}-dirty" if mudancas else commit


def gravar_coleta(
    fonte: FonteColeta,
    resposta: RespostaHTTP,
    n_registros: int,
    *,
    pasta_raw: Path,
    coletado_em: datetime,
    versao: str,
) -> dict[str, Any]:
    """Grava os bytes originais e depois o .meta.json; devolve os metadados."""
    anterior = ultima_coleta_valida(pasta_raw, fonte.cod_serie)
    arquivo_dados, arquivo_meta = caminhos_coleta(pasta_raw, fonte.cod_serie,
                                                  carimbo_utc(coletado_em))
    sha256 = calcular_sha256(resposta.conteudo)
    meta: dict[str, Any] = {
        "cod_serie": fonte.cod_serie,
        "url": resposta.url,
        "parametros": copy.deepcopy(fonte.parametros),
        "status_http": resposta.status_http,
        "coletado_em": iso_utc(coletado_em),
        "duracao_ms": resposta.duracao_ms,
        "tentativas": resposta.tentativas,
        "n_registros": n_registros,
        "tamanho_bytes": len(resposta.conteudo),
        "sha256": sha256,
        "versao_extrator": versao,
        "igual_a_anterior": anterior is not None and anterior[1].get("sha256") == sha256,
        "arquivo_dados": arquivo_dados.name,
    }
    gravar_exclusivo(arquivo_dados, resposta.conteudo)
    try:
        gravar_exclusivo(arquivo_meta,
                         json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
    except ErroGravacao:
        logger.warning("Metadados não gravados; coleta incompleta será ignorada: %s",
                       arquivo_dados)
        raise
    logger.info("Coleta gravada: %s (%d registros, igual_a_anterior=%s)",
                arquivo_dados, n_registros, meta["igual_a_anterior"])
    return meta
