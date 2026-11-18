"""Testes da transformação da fato (sem banco): sinais, conversão Decimal e parsers."""

import copy
import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from brasil_em_dados.config import RAIZ_PROJETO
from brasil_em_dados.extract.erros import ErroValidacao
from brasil_em_dados.transform.dimensoes import ErroTransformacao
from brasil_em_dados.transform.fato import (
    COLUNAS_FATO,
    SerieFato,
    converter,
    interpretar_pesquisas,
    interpretar_sidra,
    linhas_da_serie,
    linhas_pesquisas,
    linhas_sidra,
)

FIXTURES = RAIZ_PROJETO / "tests" / "fixtures"
SIDRA_6579 = json.loads((FIXTURES / "sidra_6579_amostra.json").read_text(encoding="utf-8"))
PESQUISAS = json.loads((FIXTURES / "pesquisas_47001_amostra.json").read_text(encoding="utf-8"))
COLETADO_EM = datetime(2026, 11, 14, 23, 37, 59, 272000, tzinfo=timezone.utc)

POP_ESTIMADA = SerieFato("sidra_6579_v9324", "pop_estimada", "sidra", "9324", Decimal("1"))
PIB = SerieFato("sidra_5938_v37", "pib_corrente", "sidra", "37", Decimal("1000"))
PER_CAPITA = SerieFato("pesquisas_38_i47001", "pib_per_capita", "api_pesquisas", "47001",
                       Decimal("1"))
CADASTRO = ["4205407", "4212650", "4220000"]
# A amostra da API de Pesquisas tem 2 municípios; o 1:1 exige o cadastro correspondente.
CADASTRO_PESQUISAS = ["4205407", "4212650"]


def _sidra(valores: list[tuple[str, str, str]], variavel: str = "37") -> list[dict]:
    """Resposta SIDRA no formato real: [(município, ano, valor), ...]."""
    cabecalho = {"V": "Valor", "D1C": "Município (Código)", "D2C": "Variável (Código)",
                 "D3C": "Ano (Código)"}
    return [cabecalho] + [{"V": v, "D1C": m, "D2C": variavel, "D3C": a} for m, a, v in valores]


# --- sinais do SIDRA (regra 9) ----------------------------------------------------------------

@pytest.mark.parametrize("texto, esperado", [
    ("-", (Decimal(0), "-")),          # zero absoluto: 0 com sinal
    ("0", (Decimal(0), None)),         # zero por arredondamento: numérico, sem sinal
    ("427298", (Decimal(427298), None)),
    ("12.5", (Decimal("12.5"), None)),
    ("...", (None, "...")),            # não disponível
    ("..", (None, "..")),              # não se aplica
    ("X", (None, "X")),                # inibido
    ("B", (None, "B")),                # letra de faixa
])
def test_interpretar_sidra(texto, esperado):
    assert interpretar_sidra(texto) == esperado


@pytest.mark.parametrize("texto", ["", "abc", "x", "1,5", "--", "...."])
def test_valor_sidra_fora_da_legenda_falha(texto):
    with pytest.raises(ErroTransformacao, match="fora da legenda"):
        interpretar_sidra(texto)


# --- API de Pesquisas -------------------------------------------------------------------------

@pytest.mark.parametrize("texto, esperado", [
    ("-", (None, "-")),                # na API de Pesquisas, '-' é ausência (NULL)
    ("26772.55", (Decimal("26772.55"), None)),
])
def test_interpretar_pesquisas(texto, esperado):
    assert interpretar_pesquisas(texto) == esperado


@pytest.mark.parametrize("texto", [None, "", "abc", 123.4])
def test_valor_pesquisas_fora_do_esperado_falha(texto):
    with pytest.raises(ErroTransformacao, match="fora do esperado"):
        interpretar_pesquisas(texto)


# --- conversão de unidade (regra 11) ----------------------------------------------------------

def test_conversao_de_mil_reais_para_reais_com_decimal():
    resultado = converter(Decimal("29343413"), Decimal("1000"))
    assert resultado == Decimal("29343413000.00")
    assert isinstance(resultado, Decimal)
    assert resultado.as_tuple().exponent == -2


@pytest.mark.parametrize("valor, fator, esperado", [
    ("26772.55", "1", "26772.55"),     # per capita publicado com 2 casas: intacto
    ("12.5", "1", "12.50"),            # só fixa a escala
    ("0.001", "1000", "1.00"),         # 3 casas × 1000: exato
])
def test_conversao_exata_fica_com_2_casas(valor, fator, esperado):
    assert converter(Decimal(valor), Decimal(fator)) == Decimal(esperado)


@pytest.mark.parametrize("valor", ["0.005", "1.2345", "-0.005"])
def test_conversao_que_exigiria_arredondamento_e_recusada(valor):
    # Arredondar mudaria o valor publicado (regra 4) sem ninguém perceber.
    with pytest.raises(ErroTransformacao, match="mais de 2 casas"):
        converter(Decimal(valor), Decimal("1"))


def test_valor_com_3_casas_na_fonte_cita_serie_municipio_e_ano():
    # Fator 1: 0.001 continuaria com 3 casas (com fator 1000 viraria 1.00, exato).
    with pytest.raises(ErroTransformacao, match="sidra_6579_v9324 4205407/2020: .*mais de 2 casas"):
        linhas_sidra(_sidra([("4205407", "2020", "0.001")], variavel="9324"), POP_ESTIMADA,
                     CADASTRO, COLETADO_EM)


def test_ausencia_continua_nula_na_conversao():
    assert converter(None, Decimal("1000")) is None


def test_conversao_recusa_float():
    with pytest.raises(TypeError, match="nunca float"):
        converter(1.1, Decimal("1"))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Decimal"):
        SerieFato("x", "pib_corrente", "sidra", "37", 1000.0)  # type: ignore[arg-type]


def test_fator_nao_positivo_falha():
    with pytest.raises(ErroTransformacao, match="positivo"):
        SerieFato("x", "pib_corrente", "sidra", "37", Decimal("0"))


# --- parser SIDRA -----------------------------------------------------------------------------

def test_amostra_real_da_6579():
    linhas = linhas_sidra(SIDRA_6579, POP_ESTIMADA, CADASTRO, COLETADO_EM)
    assert linhas == [
        {"cod_municipio": "4205407", "codigo_indicador": "pop_estimada", "ano": 2011,
         "cod_serie": "sidra_6579_v9324", "valor": Decimal("427298.00"), "sinal_origem": None,
         "data_coleta": COLETADO_EM},
        {"cod_municipio": "4212650", "codigo_indicador": "pop_estimada", "ano": 2011,
         "cod_serie": "sidra_6579_v9324", "valor": None, "sinal_origem": "...",
         "data_coleta": COLETADO_EM},
    ]
    assert all(tuple(l) == COLUNAS_FATO for l in linhas)


def test_pib_e_convertido_pelo_fator_da_serie():
    [linha] = linhas_sidra(_sidra([("4205407", "2021", "29343413")]), PIB, CADASTRO, COLETADO_EM)
    assert linha["valor"] == Decimal("29343413000.00")


def test_traco_do_sidra_carrega_zero_com_sinal_e_zero_sem_sinal():
    linhas = linhas_sidra(_sidra([("4205407", "2020", "-"), ("4212650", "2020", "0")]), PIB,
                          CADASTRO, COLETADO_EM)
    assert [(l["valor"], l["sinal_origem"]) for l in linhas] == [
        (Decimal("0.00"), "-"), (Decimal("0.00"), None)]


def test_codigo_continua_texto_com_zero_a_esquerda():
    # O código nunca vira número (regra 1): um zero à esquerda não se perde.
    [linha] = linhas_sidra(_sidra([("0420540", "2020", "1")]), PIB, ["0420540"], COLETADO_EM)
    assert linha["cod_municipio"] == "0420540"


def test_campos_em_outra_ordem_sao_achados_pelo_cabecalho():
    dados = [{"V": "Valor", "D1C": "Ano (Código)", "D2C": "Município (Código)",
              "D3C": "Variável (Código)"},
             {"V": "5", "D1C": "2020", "D2C": "4205407", "D3C": "37"}]
    [linha] = linhas_sidra(dados, PIB, CADASTRO, COLETADO_EM)
    assert (linha["cod_municipio"], linha["ano"]) == ("4205407", 2020)


def test_sidra_municipio_fora_da_dimensao_falha():
    with pytest.raises(ErroTransformacao, match="4299999 fora da dim_municipio"):
        linhas_sidra(_sidra([("4299999", "2020", "1")]), PIB, CADASTRO, COLETADO_EM)


def test_sidra_ano_fora_do_recorte_falha():
    with pytest.raises(ErroTransformacao, match="ano 2009 fora"):
        linhas_sidra(_sidra([("4205407", "2009", "1")]), PIB, CADASTRO, COLETADO_EM)


def test_sidra_variavel_de_outra_serie_falha():
    with pytest.raises(ErroTransformacao, match="variável 9324, esperada 37"):
        linhas_sidra(_sidra([("4205407", "2020", "1")], variavel="9324"), PIB, CADASTRO,
                     COLETADO_EM)


def test_sidra_valor_fora_da_legenda_cita_municipio_e_ano():
    with pytest.raises(ErroTransformacao, match="sidra_5938_v37 4205407/2020: .*'abc'"):
        linhas_sidra(_sidra([("4205407", "2020", "abc")]), PIB, CADASTRO, COLETADO_EM)


def test_sidra_que_nao_e_lista_falha():
    with pytest.raises(ErroValidacao, match="esperada lista"):
        linhas_sidra({"erro": "x"}, PIB, CADASTRO, COLETADO_EM)


# --- parser da API de Pesquisas ---------------------------------------------------------------

def test_amostra_real_da_api_de_pesquisas():
    linhas = linhas_pesquisas(PESQUISAS, PER_CAPITA, CADASTRO_PESQUISAS, COLETADO_EM)
    por_chave = {(l["cod_municipio"], l["ano"]): (l["valor"], l["sinal_origem"]) for l in linhas}
    # 6 dígitos → 7 pelo cadastro; 2009 (null) fica fora do recorte.
    assert por_chave[("4205407", 2010)] == (Decimal("26772.55"), None)
    assert por_chave[("4212650", 2012)] == (None, "-")
    assert por_chave[("4212650", 2013)][1] is None
    assert {ano for _, ano in por_chave} == set(range(2010, 2015))
    assert len(linhas) == 2 * 5


def test_pesquisas_codigo_6_sem_par_no_cadastro_falha():
    dados = copy.deepcopy(PESQUISAS)
    dados[0]["res"][0]["localidade"] = "429999"
    with pytest.raises(ErroTransformacao, match="não é 1:1"):
        linhas_pesquisas(dados, PER_CAPITA, CADASTRO_PESQUISAS, COLETADO_EM)


def test_pesquisas_null_dentro_do_recorte_falha():
    dados = copy.deepcopy(PESQUISAS)
    dados[0]["res"][0]["res"]["2011"] = None
    with pytest.raises(ErroTransformacao, match="4205407/2011: .*None"):
        linhas_pesquisas(dados, PER_CAPITA, CADASTRO_PESQUISAS, COLETADO_EM)


def test_pesquisas_resposta_fora_do_formato_falha():
    with pytest.raises(ErroTransformacao, match="fora do formato"):
        linhas_pesquisas([{"id": 47001}], PER_CAPITA, CADASTRO_PESQUISAS, COLETADO_EM)


def test_parser_escolhido_pela_fonte():
    assert len(linhas_da_serie(PESQUISAS, PER_CAPITA, CADASTRO_PESQUISAS, COLETADO_EM)) == 10
    assert len(linhas_da_serie(SIDRA_6579, POP_ESTIMADA, CADASTRO, COLETADO_EM)) == 2
    with pytest.raises(ErroTransformacao, match="sem parser"):
        linhas_da_serie([], SerieFato("x", "i", "outra", "1", Decimal(1)), CADASTRO, COLETADO_EM)
