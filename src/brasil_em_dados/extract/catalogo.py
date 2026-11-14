"""Catálogo de séries coletadas: fonte única para extratores e para a carga da dim_serie (D11).

Os valores espelham a tabela 1.2 de docs/dicionario_dados.md; um teste confere os dois.
"""

from dataclasses import dataclass, field
from typing import Any

TIPO_SERIE = "serie"
TIPO_DIMENSAO = "dimensao"


@dataclass(frozen=True)
class FonteColeta:
    """Uma origem coletável: série da dim_serie ou fonte de dimensão."""

    cod_serie: str
    tipo: str
    fonte: str
    url_extrator: str
    parametros: dict[str, Any] = field(default_factory=dict)
    codigo_indicador: str | None = None
    tabela_ou_pesquisa: str | None = None
    variavel_ou_indicador: str | None = None
    unidade_origem: str | None = None
    fator_conversao: int | None = None
    data_referencia: str | None = None


_FONTES: tuple[FonteColeta, ...] = (
    FonteColeta(
        cod_serie="sidra_6579_v9324",
        tipo=TIPO_SERIE,
        fonte="sidra",
        url_extrator="https://apisidra.ibge.gov.br/values/t/6579/n6/in%20n3%2042/v/9324/p/2011-2021",
        parametros={"tabela": "6579", "variaveis": ["9324"], "periodo": "2011-2021",
                    "nivel": "n6 in n3 42"},
        codigo_indicador="pop_estimada",
        tabela_ou_pesquisa="6579",
        variavel_ou_indicador="9324",
        unidade_origem="Pessoas",
        fator_conversao=1,
        data_referencia="1º de julho de cada ano",
    ),
    FonteColeta(
        cod_serie="sidra_1378_v93",
        tipo=TIPO_SERIE,
        fonte="sidra",
        url_extrator=("https://apisidra.ibge.gov.br/values/t/1378/n6/in%20n3%2042/v/93/p/2010"
             "/c1/0/c2/0/c287/0/c455/0"),
        parametros={"tabela": "1378", "variaveis": ["93"], "periodo": "2010",
                    "nivel": "n6 in n3 42",
                    "classificacoes": {"c1": "0", "c2": "0", "c287": "0", "c455": "0"}},
        codigo_indicador="pop_censo",
        tabela_ou_pesquisa="1378",
        variavel_ou_indicador="93",
        unidade_origem="Pessoas",
        fator_conversao=1,
        data_referencia="noite de 31 de julho para 1º de agosto de 2010",
    ),
    FonteColeta(
        cod_serie="sidra_4709_v93",
        tipo=TIPO_SERIE,
        fonte="sidra",
        url_extrator="https://apisidra.ibge.gov.br/values/t/4709/n6/in%20n3%2042/v/93/p/2022",
        parametros={"tabela": "4709", "variaveis": ["93"], "periodo": "2022",
                    "nivel": "n6 in n3 42"},
        codigo_indicador="pop_censo",
        tabela_ou_pesquisa="4709",
        variavel_ou_indicador="93",
        unidade_origem="Pessoas",
        fator_conversao=1,
        data_referencia="meia-noite de 31 de julho para 1º de agosto de 2022",
    ),
    FonteColeta(
        cod_serie="sidra_5938_v37",
        tipo=TIPO_SERIE,
        fonte="sidra",
        url_extrator="https://apisidra.ibge.gov.br/values/t/5938/n6/in%20n3%2042/v/37/p/2010-2023",
        parametros={"tabela": "5938", "variaveis": ["37"], "periodo": "2010-2023",
                    "nivel": "n6 in n3 42"},
        codigo_indicador="pib_corrente",
        tabela_ou_pesquisa="5938",
        variavel_ou_indicador="37",
        unidade_origem="Mil Reais",
        fator_conversao=1000,
        data_referencia="ano civil",
    ),
    FonteColeta(
        cod_serie="pesquisas_38_i47001",
        tipo=TIPO_SERIE,
        fonte="api_pesquisas",
        url_extrator=("https://servicodados.ibge.gov.br/api/v1/pesquisas/38/indicadores/47001"
             "/resultados/N6%5BN3%5B42%5D%5D"),
        parametros={"pesquisa": "38", "indicador": "47001", "localidades": "N6[N3[42]]"},
        codigo_indicador="pib_per_capita",
        tabela_ou_pesquisa="38",
        variavel_ou_indicador="47001",
        unidade_origem="R$",
        fator_conversao=1,
        data_referencia="ano civil",
    ),
    FonteColeta(
        cod_serie="ibge_localidades_sc",
        tipo=TIPO_DIMENSAO,
        fonte="api_localidades",
        url_extrator="https://servicodados.ibge.gov.br/api/v1/localidades/estados/42/municipios",
        parametros={"uf": "42"},
    ),
)

FONTES: dict[str, FonteColeta] = {f.cod_serie: f for f in _FONTES}


def obter(cod_serie: str) -> FonteColeta:
    """Devolve a fonte do catálogo ou falha com mensagem clara."""
    try:
        return FONTES[cod_serie]
    except KeyError:
        disponiveis = ", ".join(sorted(FONTES))
        raise KeyError(f"cod_serie desconhecido: {cod_serie!r}. Disponíveis: {disponiveis}") from None


def series() -> list[FonteColeta]:
    """Devolve só as séries da dim_serie (sem fontes de dimensão)."""
    return [f for f in _FONTES if f.tipo == TIPO_SERIE]
