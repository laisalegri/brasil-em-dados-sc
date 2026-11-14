"""Conteúdo esperado de cada fonte, verificado antes de gravar na RAW (D12–D14).

Resposta fora do esperado = ErroValidacao: nada é gravado e o erro vai para o controle.
Sem I/O de arquivos ou rede: o cadastro de municípios, quando necessário, é lido pelo
chamador. A única saída lateral é o aviso de valor zero no log.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from brasil_em_dados.extract.erros import ErroValidacao
from brasil_em_dados.transform.codigos import mapear_codigos_6_para_7

logger = logging.getLogger(__name__)

N_MUNICIPIOS = 295
CODIGOS_NOVOS = frozenset({"4212650", "4220000"})  # Pescaria Brava e Balneário Rincão
COD_LOCALIDADES = "ibge_localidades_sc"
COD_PESQUISAS = "pesquisas_38_i47001"
MAX_EXEMPLOS = 5
SINAL_AUSENTE = "..."  # único sinal que as fontes reais devolvem para os municípios novos

ROTULO_MUNICIPIO = "Município (Código)"
ROTULO_ANO = "Ano (Código)"
ROTULO_VARIAVEL = "Variável (Código)"
ROTULO_VALOR = "Valor"

_CODIGO_SC = re.compile(r"42\d{5}")
_CODIGO_6 = re.compile(r"42\d{4}")
_NUMERO = re.compile(r"-?\d+(?:\.\d+)?")


@dataclass(frozen=True)
class RegraSidra:
    """Conteúdo esperado de uma série SIDRA."""

    variavel: str
    anos: frozenset[int]
    n_linhas: int
    ausentes: frozenset[str] = frozenset()
    sinais_permitidos: frozenset[tuple[str, int]] = frozenset()  # (município, ano) com "..."
    zero_suspeito: bool = True  # "0" pode ser zero por arredondamento (regra 9): avisa no log


@dataclass(frozen=True)
class LinhaSidra:
    """Campos de uma linha SIDRA usados na validação."""

    municipio: str
    ano: int
    variavel: str
    valor: str


def _sinais(codigos: frozenset[str], anos: range) -> frozenset[tuple[str, int]]:
    return frozenset((codigo, ano) for codigo in codigos for ano in anos)


REGRAS_SIDRA: dict[str, RegraSidra] = {
    "sidra_6579_v9324": RegraSidra("9324", frozenset(range(2011, 2022)), 3245,
                                   sinais_permitidos=_sinais(CODIGOS_NOVOS, range(2011, 2012))),
    "sidra_1378_v93": RegraSidra("93", frozenset({2010}), 293, ausentes=CODIGOS_NOVOS),
    "sidra_4709_v93": RegraSidra("93", frozenset({2022}), 295),
    "sidra_5938_v37": RegraSidra("37", frozenset(range(2010, 2024)), 4130,
                                 sinais_permitidos=_sinais(CODIGOS_NOVOS, range(2010, 2013))),
}

# Fontes cujos códigos de município são conferidos contra o cadastro (ibge_localidades_sc).
PRECISAM_DE_CADASTRO = frozenset(REGRAS_SIDRA) | {COD_PESQUISAS}


def _exemplos(itens: list) -> list:
    return sorted(itens)[:MAX_EXEMPLOS]


def _falhar_se(problemas: list[str], fonte: str) -> None:
    if problemas:
        raise ErroValidacao(f"{fonte}: " + "; ".join(problemas))


def eh_numerico(valor: str) -> bool:
    """Indica se o valor SIDRA é número (e não um sinal como '...', '-' ou 'X')."""
    return bool(_NUMERO.fullmatch(valor))


def localizar_campos(cabecalho: Any) -> dict[str, str]:
    """Acha as chaves de município, ano, variável e valor pelos rótulos do cabeçalho (D10)."""
    if not isinstance(cabecalho, dict):
        raise ErroValidacao("SIDRA: a primeira linha deveria ser o cabeçalho")
    chave_por_rotulo = {rotulo: chave for chave, rotulo in cabecalho.items()}
    rotulos = {"municipio": ROTULO_MUNICIPIO, "ano": ROTULO_ANO,
               "variavel": ROTULO_VARIAVEL, "valor": ROTULO_VALOR}
    faltando = [r for r in rotulos.values() if r not in chave_por_rotulo]
    if faltando:
        raise ErroValidacao(f"SIDRA: rótulos ausentes no cabeçalho: {faltando}")
    return {campo: chave_por_rotulo[rotulo] for campo, rotulo in rotulos.items()}


def linhas_sidra(dados: Any) -> list[LinhaSidra]:
    """Converte a resposta SIDRA em linhas, usando o cabeçalho para achar os campos."""
    if not isinstance(dados, list) or not dados:
        raise ErroValidacao("SIDRA: esperada lista com cabeçalho")
    campos = localizar_campos(dados[0])
    linhas = []
    for bruta in dados[1:]:
        try:
            linhas.append(LinhaSidra(
                municipio=str(bruta[campos["municipio"]]),
                ano=int(bruta[campos["ano"]]),
                variavel=str(bruta[campos["variavel"]]),
                valor=str(bruta[campos["valor"]]),
            ))
        except (KeyError, TypeError, ValueError) as exc:
            raise ErroValidacao(f"SIDRA: linha fora do formato do cabeçalho: {bruta!r}") from exc
    return linhas


def eh_zero(valor: str) -> bool:
    """Indica se o valor SIDRA é numérico e igual a zero ("0", "0.00")."""
    return eh_numerico(valor) and float(valor) == 0


def validar_sidra(dados: Any, regra: RegraSidra, cadastro: list[str],
                  fonte: str = "SIDRA") -> None:
    """Confere contagem, anos, variável, códigos, cadastro, duplicidades, ausências e sinais.

    Valor zero não reprova a resposta: gera aviso no log quando `regra.zero_suspeito`.
    """
    linhas = linhas_sidra(dados)
    problemas: list[str] = []

    if len(linhas) != regra.n_linhas:
        problemas.append(f"esperadas {regra.n_linhas} linhas, vieram {len(linhas)}")
    variaveis = {linha.variavel for linha in linhas}
    if variaveis != {regra.variavel}:
        problemas.append(f"variáveis {sorted(variaveis)}, esperada {regra.variavel}")
    anos = {linha.ano for linha in linhas}
    if anos != regra.anos:
        problemas.append(f"anos {sorted(anos)}, esperados {sorted(regra.anos)}")

    invalidos = [l.municipio for l in linhas if not _CODIGO_SC.fullmatch(l.municipio)]
    if invalidos:
        problemas.append(f"códigos fora do padrão 42xxxxx: {_exemplos(invalidos)}")
    validos = {l.municipio for l in linhas if _CODIGO_SC.fullmatch(l.municipio)}
    desconhecidos = sorted(validos - set(cadastro))
    if desconhecidos:
        problemas.append(f"municípios fora do cadastro: {_exemplos(desconhecidos)}")
    repetidos = [k for k, n in Counter((l.municipio, l.ano) for l in linhas).items() if n > 1]
    if repetidos:
        problemas.append(f"município × ano repetidos: {_exemplos(repetidos)}")
    por_ano = Counter(linha.ano for linha in linhas)
    esperado_por_ano = regra.n_linhas // len(regra.anos)
    anos_incompletos = [(a, n) for a, n in por_ano.items() if n != esperado_por_ano]
    if anos_incompletos:
        problemas.append(f"anos sem {esperado_por_ano} municípios: {_exemplos(anos_incompletos)}")
    presentes = sorted({l.municipio for l in linhas} & regra.ausentes)
    if presentes:
        problemas.append(f"municípios que deveriam estar ausentes: {presentes}")
    sinais = [(l.municipio, l.ano, l.valor) for l in linhas
              if not eh_numerico(l.valor) and not _sinal_permitido(l, regra)]
    if sinais:
        problemas.append(f"sinais não permitidos: {_exemplos(sinais)}")

    _falhar_se(problemas, fonte)
    if regra.zero_suspeito:
        _avisar_zeros(linhas, fonte)


def _sinal_permitido(linha: LinhaSidra, regra: RegraSidra) -> bool:
    """Só "..." nos (município, ano) previstos; "-" seria zero na carga (regra 9)."""
    return linha.valor == SINAL_AUSENTE and (linha.municipio, linha.ano) in regra.sinais_permitidos


def _avisar_zeros(linhas: list[LinhaSidra], fonte: str) -> None:
    zeros = [(l.municipio, l.ano) for l in linhas if eh_zero(l.valor)]
    if zeros:
        logger.warning("%s: %d valor(es) zero, suspeitos para este indicador (regra 9): %s",
                       fonte, len(zeros), _exemplos(zeros))


def validar_localidades(dados: Any) -> None:
    """295 municípios; ids únicos, com 7 dígitos e começando com 42."""
    if not isinstance(dados, list):
        raise ErroValidacao(f"{COD_LOCALIDADES}: esperada lista de municípios")
    ids = [str(m.get("id")) if isinstance(m, dict) else repr(m) for m in dados]
    problemas: list[str] = []
    if len(ids) != N_MUNICIPIOS:
        problemas.append(f"esperados {N_MUNICIPIOS} municípios, vieram {len(ids)}")
    invalidos = [i for i in ids if not _CODIGO_SC.fullmatch(i)]
    if invalidos:
        problemas.append(f"ids fora do padrão 42xxxxx: {_exemplos(invalidos)}")
    repetidos = [i for i, n in Counter(ids).items() if n > 1]
    if repetidos:
        problemas.append(f"ids repetidos: {_exemplos(repetidos)}")
    _falhar_se(problemas, COD_LOCALIDADES)


def codigos_do_cadastro(municipios: Any) -> list[str]:
    """Valida o cadastro de municípios e devolve os códigos de 7 dígitos."""
    validar_localidades(municipios)
    return [str(m["id"]) for m in municipios]


def _localidades_pesquisas(dados: Any) -> list[str]:
    if not isinstance(dados, list) or not dados:
        raise ErroValidacao(f"{COD_PESQUISAS}: esperada lista não vazia")
    localidades = []
    for item in dados:
        resultados = item.get("res") if isinstance(item, dict) else None
        if not isinstance(resultados, list):
            raise ErroValidacao(f"{COD_PESQUISAS}: indicador sem lista 'res'")
        for resultado in resultados:
            if not isinstance(resultado, dict) or "localidade" not in resultado:
                raise ErroValidacao(f"{COD_PESQUISAS}: resultado sem 'localidade': {resultado!r}")
            localidades.append(str(resultado["localidade"]))
    return localidades


def validar_pesquisas(dados: Any, cadastro: list[str]) -> None:
    """295 localidades com 6 dígitos, em correspondência 1:1 com o cadastro (D09)."""
    localidades = _localidades_pesquisas(dados)
    problemas: list[str] = []
    if len(localidades) != N_MUNICIPIOS:
        problemas.append(f"esperadas {N_MUNICIPIOS} localidades, vieram {len(localidades)}")
    invalidos = [c for c in localidades if not _CODIGO_6.fullmatch(c)]
    if invalidos:
        problemas.append(f"localidades fora do padrão 42xxxx: {_exemplos(invalidos)}")
    try:
        mapear_codigos_6_para_7(localidades, cadastro)
    except ValueError as exc:
        problemas.append(str(exc))
    _falhar_se(problemas, COD_PESQUISAS)


def _exigir_cadastro(cod_serie: str, cadastro: list[str] | None) -> list[str]:
    if cadastro is None:
        raise ErroValidacao(f"{cod_serie}: cadastro de municípios é obrigatório")
    return cadastro


def validar_conteudo(cod_serie: str, dados: Any, *, cadastro: list[str] | None = None) -> None:
    """Aplica a regra de conteúdo esperado da fonte; sem regra também é falha.

    `cadastro` (códigos de 7 dígitos) é obrigatório para as fontes em PRECISAM_DE_CADASTRO.
    """
    if cod_serie == COD_LOCALIDADES:
        validar_localidades(dados)
    elif cod_serie in REGRAS_SIDRA:
        validar_sidra(dados, REGRAS_SIDRA[cod_serie], _exigir_cadastro(cod_serie, cadastro),
                      cod_serie)
    elif cod_serie == COD_PESQUISAS:
        validar_pesquisas(dados, _exigir_cadastro(cod_serie, cadastro))
    else:
        raise ErroValidacao(f"Sem regra de conteúdo esperado para {cod_serie}")
