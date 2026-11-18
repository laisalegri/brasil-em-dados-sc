"""Transformação da fato (D21): respostas da RAW → linhas de silver.fato_indicador_municipio.

Lógica pura, sem I/O. Regras:
- SIDRA (regra 9): '-' → 0 com sinal; número (inclusive '0') → valor sem sinal;
  '...', '..', 'X' e letras de faixa → NULL com o sinal.
- API de Pesquisas: '-' → NULL com sinal '-'; código de 6 dígitos → 7 pelo cadastro (1:1);
  só os anos de 2010 a 2023.
- Conversão de unidade (regra 11): valor × fator_conversao da dim_serie, sempre Decimal,
  com 2 casas. Resultado com mais de 2 casas é erro (arredondar mudaria o valor publicado).
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from brasil_em_dados.extract.conteudo import linhas_sidra as ler_linhas_sidra
from brasil_em_dados.transform.codigos import mapear_codigos_6_para_7
from brasil_em_dados.transform.dimensoes import ErroTransformacao

ANO_INICIAL, ANO_FINAL = 2010, 2023
DUAS_CASAS = Decimal("0.01")
FONTE_SIDRA = "sidra"
FONTE_PESQUISAS = "api_pesquisas"

COLUNAS_FATO = ("cod_municipio", "codigo_indicador", "ano", "cod_serie", "valor",
                "sinal_origem", "data_coleta")

_NUMERO = re.compile(r"-?\d+(?:\.\d+)?")
_SINAIS_NULOS_SIDRA = re.compile(r"\.\.\.|\.\.|[A-Z]")  # inclui X e as letras de faixa
TRACO = "-"


@dataclass(frozen=True)
class SerieFato:
    """Atributos da dim_serie usados na transformação."""

    cod_serie: str
    codigo_indicador: str
    fonte: str
    variavel_ou_indicador: str
    fator_conversao: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.fator_conversao, Decimal):
            # Nunca float: Decimal(1.1) carregaria o erro binário para o valor.
            raise TypeError(f"{self.cod_serie}: fator_conversao deve ser Decimal")
        if self.fator_conversao <= 0:
            raise ErroTransformacao(f"{self.cod_serie}: fator_conversao deve ser positivo")


def converter(valor: Decimal | None, fator: Decimal) -> Decimal | None:
    """valor × fator com 2 casas; ausência continua None.

    Se o resultado exato tiver mais de 2 casas, é erro: arredondar mudaria o valor publicado
    (regra 4) em silêncio. O quantize (ROUND_HALF_UP) só fixa a escala em 2 casas.
    """
    if valor is None:
        return None
    if not isinstance(valor, Decimal) or not isinstance(fator, Decimal):
        raise TypeError("converter usa só Decimal (nunca float)")
    exato = valor * fator
    convertido = exato.quantize(DUAS_CASAS, rounding=ROUND_HALF_UP)
    if convertido != exato:
        raise ErroTransformacao(
            f"valor {valor} × {fator} = {exato} tem mais de 2 casas; arredondar alteraria o "
            "valor publicado")
    return convertido


def _numero(texto: str) -> Decimal:
    try:
        return Decimal(texto)
    except InvalidOperation as exc:
        raise ErroTransformacao(f"valor não numérico: {texto!r}") from exc


def interpretar_sidra(texto: str) -> tuple[Decimal | None, str | None]:
    """Valor de origem e sinal de uma célula SIDRA (regra 9)."""
    if texto == TRACO:
        return Decimal(0), TRACO  # zero absoluto: valor 0, sinal preservado
    if _NUMERO.fullmatch(texto):
        return _numero(texto), None  # inclusive "0" (zero por arredondamento): sem sinal
    if _SINAIS_NULOS_SIDRA.fullmatch(texto):
        return None, texto
    raise ErroTransformacao(f"valor SIDRA fora da legenda: {texto!r}")


def interpretar_pesquisas(texto: Any) -> tuple[Decimal | None, str | None]:
    """Valor de origem e sinal de um resultado da API de Pesquisas."""
    if texto == TRACO:
        return None, TRACO  # na API de Pesquisas, '-' é ausência
    if isinstance(texto, str) and _NUMERO.fullmatch(texto):
        return _numero(texto), None
    raise ErroTransformacao(f"valor da API de Pesquisas fora do esperado: {texto!r}")


def _linha(serie: SerieFato, municipio: str, ano: int, valor: Decimal | None,
           sinal: str | None, data_coleta: datetime) -> dict[str, Any]:
    try:
        convertido = converter(valor, serie.fator_conversao)
    except ErroTransformacao as exc:
        raise ErroTransformacao(f"{serie.cod_serie} {municipio}/{ano}: {exc}") from exc
    return {"cod_municipio": municipio, "codigo_indicador": serie.codigo_indicador, "ano": ano,
            "cod_serie": serie.cod_serie, "valor": convertido,
            "sinal_origem": sinal, "data_coleta": data_coleta}


def _conferir_municipio_e_ano(serie: SerieFato, municipio: str, ano: int,
                              cadastro: set[str]) -> None:
    if municipio not in cadastro:
        raise ErroTransformacao(f"{serie.cod_serie}: município {municipio} fora da dim_municipio")
    if not ANO_INICIAL <= ano <= ANO_FINAL:
        raise ErroTransformacao(f"{serie.cod_serie}: ano {ano} fora de {ANO_INICIAL}–{ANO_FINAL}")


def linhas_sidra(dados: Any, serie: SerieFato, cadastro: Iterable[str],
                 data_coleta: datetime) -> list[dict[str, Any]]:
    """Linhas da fato a partir de uma resposta SIDRA (campos pelo cabeçalho)."""
    codigos = set(cadastro)
    linhas = []
    for bruta in ler_linhas_sidra(dados):
        if bruta.variavel != serie.variavel_ou_indicador:
            raise ErroTransformacao(f"{serie.cod_serie}: variável {bruta.variavel}, esperada "
                                    f"{serie.variavel_ou_indicador}")
        _conferir_municipio_e_ano(serie, bruta.municipio, bruta.ano, codigos)
        try:
            valor, sinal = interpretar_sidra(bruta.valor)
        except ErroTransformacao as exc:
            raise ErroTransformacao(f"{serie.cod_serie} {bruta.municipio}/{bruta.ano}: {exc}") \
                from exc
        linhas.append(_linha(serie, bruta.municipio, bruta.ano, valor, sinal, data_coleta))
    return linhas


def linhas_pesquisas(dados: Any, serie: SerieFato, cadastro: Iterable[str],
                     data_coleta: datetime) -> list[dict[str, Any]]:
    """Linhas da fato a partir da API de Pesquisas (6 → 7 dígitos, recorte 2010–2023)."""
    codigos = list(cadastro)
    conjunto = set(codigos)
    try:
        resultados = [r for item in dados for r in item["res"]]
        localidades = [str(r["localidade"]) for r in resultados]
    except (KeyError, TypeError) as exc:
        raise ErroTransformacao(f"{serie.cod_serie}: resposta fora do formato: {exc}") from exc
    try:
        mapa = mapear_codigos_6_para_7(localidades, codigos)
    except ValueError as exc:
        raise ErroTransformacao(f"{serie.cod_serie}: {exc}") from exc
    linhas = []
    for resultado, codigo6 in zip(resultados, localidades):
        municipio = mapa[codigo6]
        valores = resultado["res"]
        if not isinstance(valores, dict):
            raise ErroTransformacao(f"{serie.cod_serie} {municipio}: 'res' deveria ser um objeto")
        for ano_texto, texto in valores.items():
            try:
                ano = int(ano_texto)
            except ValueError as exc:
                raise ErroTransformacao(f"{serie.cod_serie} {municipio}: ano {ano_texto!r}") \
                    from exc
            if not ANO_INICIAL <= ano <= ANO_FINAL:
                continue  # a RAW guarda a série inteira (1999–2023); o recorte é na carga
            _conferir_municipio_e_ano(serie, municipio, ano, conjunto)
            try:
                valor, sinal = interpretar_pesquisas(texto)
            except ErroTransformacao as exc:
                raise ErroTransformacao(f"{serie.cod_serie} {municipio}/{ano}: {exc}") from exc
            linhas.append(_linha(serie, municipio, ano, valor, sinal, data_coleta))
    return linhas


def linhas_da_serie(dados: Any, serie: SerieFato, cadastro: Iterable[str],
                    data_coleta: datetime) -> list[dict[str, Any]]:
    """Escolhe o parser pela fonte da série."""
    if serie.fonte == FONTE_SIDRA:
        return linhas_sidra(dados, serie, cadastro, data_coleta)
    if serie.fonte == FONTE_PESQUISAS:
        return linhas_pesquisas(dados, serie, cadastro, data_coleta)
    raise ErroTransformacao(f"{serie.cod_serie}: fonte sem parser: {serie.fonte}")
