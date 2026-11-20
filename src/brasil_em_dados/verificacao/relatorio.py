"""Montagem e gravação do relatório reports/verificacao_<carimbo>.md.

A parte de execução (flags, passos, usuários do banco, consumo) é escrita pelo código; só a
seção de análise vem do agente. O caminho é montado a partir do carimbo validado, sempre dentro
de reports/, e um arquivo existente nunca é sobrescrito.
"""

import re
from collections.abc import Iterable
from pathlib import Path

from brasil_em_dados.verificacao.agente import ResultadoAgente
from brasil_em_dados.verificacao.executor import ResultadoPasso
from brasil_em_dados.verificacao.seguranca import limpar_texto

FORMATO_CARIMBO = "%Y%m%dT%H%M%S"
_CARIMBO = re.compile(r"^\d{8}T\d{6}$")
USUARIO_FERRAMENTAS = "bed_readonly, com SET TRANSACTION READ ONLY"


def caminho_relatorio(pasta_reports: Path, carimbo: str) -> Path:
    """reports/verificacao_<carimbo>.md; recusa carimbo fora do formato AAAAMMDDTHHMMSS."""
    if not _CARIMBO.match(carimbo):
        raise ValueError(f"Carimbo fora do formato AAAAMMDDTHHMMSS: {carimbo!r}")
    return pasta_reports / f"verificacao_{carimbo}.md"


def _flags(flags: Iterable[str]) -> str:
    lista = [f"--{f}" for f in flags]
    return " ".join(lista) if lista else "nenhuma (só pytest)"


def comando(flags: Iterable[str]) -> str:
    """Linha de comando equivalente à execução."""
    return " ".join(["python -m brasil_em_dados.verificacao", *(f"--{f}" for f in flags)])


def _duracao(segundos: float | None) -> str:
    return "—" if segundos is None else f"{segundos:.1f} s"


def _consumo(agente: ResultadoAgente) -> list[str]:
    linhas = [
        f"- Modelo: {agente.modelo or '—'}",
        f"- Origem da chave (apiKeySource): {agente.origem_chave or '—'}"
        + (" (login do plano Pro, sem chave de API)" if agente.origem_chave == "none" else ""),
        f"- Situação: {agente.situacao}" + (f" ({agente.erro})" if agente.erro else ""),
        f"- Turnos: {agente.turnos if agente.turnos is not None else '—'}",
        f"- Duração: {agente.duracao_ms / 1000:.1f} s" if agente.duracao_ms is not None
        else "- Duração: —",
    ]
    if agente.usage:
        u = agente.usage
        linhas.append(
            "- Tokens do laço principal: entrada {} | saída {} | criação de cache {} | leitura "
            "de cache {}".format(u.get("input_tokens"), u.get("output_tokens"),
                                 u.get("cache_creation_input_tokens"),
                                 u.get("cache_read_input_tokens")))
    for modelo, uso in sorted((agente.model_usage or {}).items()):
        custo_modelo = uso.get("costUSD")
        estimativa = f"{custo_modelo:.4f}" if isinstance(custo_modelo, (int, float)) else "—"
        linhas.append(
            f"- {modelo}: entrada {uso.get('inputTokens')} | saída {uso.get('outputTokens')} | "
            f"criação de cache {uso.get('cacheCreationInputTokens')} | leitura de cache "
            f"{uso.get('cacheReadInputTokens')} | estimativa US$ {estimativa}")
    custo = agente.custo_estimado_usd
    linhas.append(
        f"- Custo estimado total: US$ {custo:.4f}" if custo is not None
        else "- Custo estimado total: —")
    linhas.append("- A estimativa é calculada localmente pelo SDK a preço de API. No plano Pro "
                  "não há cobrança por uso: a execução consome o limite da assinatura.")
    return linhas


def montar(carimbo: str, flags: Iterable[str], resultados: list[ResultadoPasso],
           agente: ResultadoAgente, analise: str | None, pasta_execucao: str,
           segredos: Iterable[str] = ()) -> str:
    """Texto completo do relatório, já limpo de URL de conexão e senha."""
    flags = list(flags)
    partes = [
        f"# Verificação do pipeline — {carimbo} (UTC)",
        "",
        "## Execução",
        "",
        "Esta seção é escrita pelo executor, não pelo modelo.",
        "",
        f"- Flags recebidas: {_flags(flags)}",
        f"- Comando: `{comando(flags)}`",
        f"- Saídas completas: `{pasta_execucao}`",
        f"- Ferramentas do agente no banco: {USUARIO_FERRAMENTAS}",
        "",
        "| Passo | Comando | Usuário do banco | Situação | Código | Duração |",
        "|---|---|---|---|---|---|",
    ]
    for r in resultados:
        situacao = r.situacao + (f" ({r.motivo})" if r.motivo else "")
        codigo = "—" if r.codigo is None else str(r.codigo)
        partes.append(f"| {r.passo.nome} | `{r.passo.comando}` | {r.passo.usuario_banco} | "
                      f"{situacao} | {codigo} | {_duracao(r.duracao_s)} |")
    partes += ["", "## Análise do agente", ""]
    if analise:
        partes.append(analise.strip())
    else:
        motivo = agente.erro or "o agente não entregou a análise"
        partes.append(f"Análise não produzida: {motivo}.")
    partes += ["", "## Consumo do agente", "", *_consumo(agente), ""]
    return limpar_texto("\n".join(partes), segredos)


def gravar(caminho: Path, texto: str) -> Path:
    """Grava o relatório; falha se o arquivo já existir (modo 'x', nunca sobrescreve)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("x", encoding="utf-8") as arquivo:
        arquivo.write(texto)
    return caminho
