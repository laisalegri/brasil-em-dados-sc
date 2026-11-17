"""Transformação das dimensões da SILVER (D20): JSON de municípios e catálogo → linhas.

Lógica pura, sem I/O. A leitura da RAW e a gravação no banco ficam em brasil_em_dados.load.
"""

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from brasil_em_dados.extract import catalogo

_CODIGO_SC = re.compile(r"42\d{5}")
UF_SC = "42"
SIGLA_SC = "SC"

COLUNAS_DIM_MUNICIPIO = (
    "cod_municipio", "nome_municipio",
    "cod_regiao_imediata", "nome_regiao_imediata",
    "cod_regiao_intermediaria", "nome_regiao_intermediaria",
    "cod_microrregiao", "nome_microrregiao",
    "cod_mesorregiao", "nome_mesorregiao",
    "cod_uf", "sigla_uf",
)
COLUNAS_DIM_INDICADOR = ("codigo_indicador", "nome", "unidade_armazenada", "tipo_medida",
                         "descricao")
COLUNAS_DIM_SERIE = ("cod_serie", "codigo_indicador", "fonte", "tabela_ou_pesquisa",
                     "variavel_ou_indicador", "unidade_origem", "fator_conversao",
                     "data_referencia", "url_extrator")


class ErroTransformacao(ValueError):
    """Dado de origem fora do formato esperado para a dimensão."""


def codigo_municipio(id_municipio: Any) -> str:
    """Código IBGE como texto de 7 dígitos (regra 1); a API devolve o id como número."""
    return str(id_municipio).zfill(7)


def _identificar(municipio: Any) -> str:
    return repr(municipio.get("id")) if isinstance(municipio, Mapping) else repr(municipio)


def linha_dim_municipio(municipio: Mapping[str, Any]) -> dict[str, str]:
    """Achata um município da API de Localidades nas duas hierarquias (D06)."""
    try:
        micro = municipio["microrregiao"]
        meso = micro["mesorregiao"]
        imediata = municipio["regiao-imediata"]
        intermediaria = imediata["regiao-intermediaria"]
        uf_antiga, uf_nova = meso["UF"], intermediaria["UF"]
        linha = {
            "cod_municipio": codigo_municipio(municipio["id"]),
            "nome_municipio": municipio["nome"],
            "cod_regiao_imediata": str(imediata["id"]),
            "nome_regiao_imediata": imediata["nome"],
            "cod_regiao_intermediaria": str(intermediaria["id"]),
            "nome_regiao_intermediaria": intermediaria["nome"],
            "cod_microrregiao": str(micro["id"]),
            "nome_microrregiao": micro["nome"],
            "cod_mesorregiao": str(meso["id"]),
            "nome_mesorregiao": meso["nome"],
            "cod_uf": str(uf_antiga["id"]),
            "sigla_uf": uf_antiga["sigla"],
        }
        ufs = {(str(uf_antiga["id"]), uf_antiga["sigla"]), (str(uf_nova["id"]), uf_nova["sigla"])}
    except KeyError as exc:
        raise ErroTransformacao(
            f"Município {_identificar(municipio)} fora do formato da API: falta o campo {exc}"
        ) from exc
    except TypeError as exc:
        raise ErroTransformacao(
            f"Município {_identificar(municipio)} fora do formato da API: um nível da "
            f"hierarquia não é um objeto ({exc})") from exc

    if not _CODIGO_SC.fullmatch(linha["cod_municipio"]):
        raise ErroTransformacao(f"Código fora do padrão 42xxxxx: {linha['cod_municipio']}")
    if ufs != {(UF_SC, SIGLA_SC)}:
        raise ErroTransformacao(
            f"Município {linha['cod_municipio']}: UF diferente de 42/SC nas hierarquias: {ufs}")
    return linha


def linhas_dim_municipio(municipios: Any) -> list[dict[str, str]]:
    """Converte a resposta da API em linhas; códigos repetidos são erro."""
    if not isinstance(municipios, list):
        raise ErroTransformacao("Resposta de municípios deveria ser uma lista")
    linhas = [linha_dim_municipio(m) for m in municipios]
    repetidos = sorted(c for c, n in Counter(l["cod_municipio"] for l in linhas).items() if n > 1)
    if repetidos:
        raise ErroTransformacao(f"Códigos de município repetidos: {repetidos[:5]}")
    return linhas


def linhas_dim_indicador(
    indicadores: Iterable[catalogo.Indicador] | None = None,
) -> list[dict[str, str]]:
    """Linhas da dim_indicador a partir do catálogo (fonte única)."""
    fonte = catalogo.indicadores() if indicadores is None else indicadores
    return [{coluna: getattr(i, coluna) for coluna in COLUNAS_DIM_INDICADOR} for i in fonte]


def linhas_dim_serie(series: Iterable[catalogo.FonteColeta] | None = None) -> list[dict[str, Any]]:
    """Linhas da dim_serie a partir do catálogo; só séries, sem fontes de dimensão."""
    fonte = catalogo.series() if series is None else series
    linhas = []
    for serie in fonte:
        linha = {coluna: getattr(serie, coluna) for coluna in COLUNAS_DIM_SERIE}
        faltando = [coluna for coluna, valor in linha.items() if valor is None]
        if faltando:
            raise ErroTransformacao(f"Série {serie.cod_serie} sem {faltando} no catálogo")
        linhas.append(linha)
    return linhas
