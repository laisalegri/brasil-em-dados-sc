"""Textos do app: avisos das regras (docs/dashboards.md), formatadores pt-BR e títulos.

Os formatadores só produzem texto (regra 11): o valor exibido é o da GOLD. Valor ausente aparece
como "sem dado", nunca como zero (regra 5).
"""

from collections.abc import Callable

import pandas as pd

from brasil_em_dados.analise.graficos import (
    FONTE_CENSOS,
    FONTE_ESTIMATIVA,
    FONTE_PER_CAPITA,
    FONTE_PIB,
    formatar_habitantes,
    formatar_reais,
)

__all__ = [
    "FONTE_CENSOS", "FONTE_ESTIMATIVA", "FONTE_PER_CAPITA", "FONTE_PIB",
    "formatar_habitantes", "formatar_reais",
]

SEM_DADO = "sem dado"
SANTA_CATARINA = "Santa Catarina"
ROTULO_MEDIANA = "mediana entre os municípios"  # decisão D34: nunca "per capita de SC/da região"
RODAPE = "Fonte: IBGE (SIDRA e API de Pesquisas), elaboração própria."  # C9
FONTE_PARTICIPACAO = "IBGE (PIB dos Municípios, SIDRA 5938; Censos, SIDRA 1378 e 4709)"
ANOS_CENSO = (2010, 2022)

# -- avisos (seção 4 de docs/dashboards.md) ------------------------------------------------------

AVISO_PIB_NOMINAL = ("PIB nominal, a preços correntes: a variação entre anos inclui inflação e não "
                     "é crescimento real (regra 3).")
AVISO_REVISAO_PIB = ("2021–2023 foram revisados pelo IBGE em 19/12/2025; 2022–2023 ainda estão "
                     "sujeitos a revisão (limitações, seção 5).")
AVISO_DISTRIBUICAO = ("O PIB municipal é uma distribuição do PIB estadual feita pelo IBGE por "
                      "indicadores de atividade, e não uma medição direta (limitações, seção 6).")
AVISO_PER_CAPITA = "PIB per capita publicado pelo IBGE; não é renda (regra 4)."
AVISO_DENOMINADOR = ("O denominador do per capita muda conforme o ano: estimativa até 2021, "
                     "1ª apuração do Censo em 2022 (limitações, seção 9).")
AVISO_A1 = ("Alerta A1: em municípios pequenos, a entrada ou a saída de um estabelecimento pode "
            "multiplicar o PIB de um ano para outro; a causa de cada caso é NÃO CONFIRMADA "
            "(limitações, seção 6).")
AVISO_PARTICIPACAO = ("A participação é uma razão entre valores do mesmo ano e não depende da "
                      "inflação geral, mas reflete diferenças de preços entre atividades.")
AVISO_SEM_PER_CAPITA_REGIONAL = ("Comparação entre participações; não é PIB per capita regional "
                                 "(regra 4).")
AVISO_QUEBRAS = ("Estimativa com três bases (regra 12): de 2012 para 2013 há quebra de série "
                 "(nova projeção por UF) e a variação não é calculada; de 2017 para 2018 há "
                 "revisão da projeção, e o IBGE declara comparáveis só 2013–2017. Linhas de bases "
                 "diferentes não se ligam.")
AVISO_DUPLA_CONTAGEM = ("Em 2012, o total exclui Pescaria Brava (4212650) e Balneário Rincão "
                        "(4220000), em dupla contagem com o município de origem (regra 13).")
AVISO_CENSO_OFICIAL = ("A variação oficial de população é Censo 2010 × Censo 2022; a estimativa "
                       "não substitui os Censos (regra 2).")
AVISO_APURACOES = ("O Censo 2022 tem duas apurações; a diferença entre elas não foi confirmada "
                   "(limitações, seção 8).")
AVISO_LAGUNA = ("Laguna: a queda pode vir do desmembramento de Pescaria Brava (NÃO CONFIRMADO; "
                "limitações, seção 10).")
AVISO_CRICIUMA = ("Região de Criciúma: inclui os 2 municípios instalados em 2013; o território é "
                  "o mesmo em 2010 e 2022 só se a população deles estava em Laguna e Içara em "
                  "2010 (NÃO CONFIRMADO; limitações, seção 10).")
AVISO_NAO_INSTALADO = "Município instalado em 2013: sem dado antes disso (regras 6 e 10)."
AVISO_REVISAO_2018 = ("2017→2018: revisão da projeção; a variação é calculada, mas o IBGE declara "
                      "comparáveis só 2013–2017 (regra 12).")
QUEBRAS_ESTIMATIVA = {2013: "quebra de série: nova projeção", 2018: "revisão da projeção"}  # C8


# -- formatadores (só texto) ---------------------------------------------------------------------

def ausente(valor: object) -> bool:
    """Valor ausente (None, NaN, NA)."""
    return valor is None or bool(pd.isna(valor))


def numero_br(valor: float, casas: int = 0) -> str:
    """Número no padrão brasileiro: 7610361 → '7.610.361'; 8.0984 → '8,0984'."""
    texto = f"{abs(float(valor)):,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"−{texto}" if float(valor) < 0 else texto


def ou_sem_dado(valor: object, formatar: Callable[[float], str]) -> str:
    """Formata o valor ou devolve 'sem dado' (regra 5)."""
    return SEM_DADO if ausente(valor) else formatar(float(valor))


def inteiro(valor: object) -> str:
    """Pessoas ou contagens: '7.610.361'."""
    return ou_sem_dado(valor, lambda v: numero_br(v, 0))


def reais(valor: object) -> str:
    """Reais com centavos: 'R$ 513.392.972.000,00'."""
    return ou_sem_dado(valor, lambda v: f"R$ {numero_br(v, 2)}")


def reais_abreviado(valor: object) -> str:
    """Reais abreviados para rótulos: 'R$ 513,4 bi'."""
    return ou_sem_dado(valor, formatar_reais)


def habitantes_abreviado(valor: object) -> str:
    """Pessoas abreviadas para rótulos: '7,61 mi'."""
    return ou_sem_dado(valor, formatar_habitantes)


def percentual(valor: object, casas: int = 1) -> str:
    """'8,1%'; com casas=4, '8,0984%' (precisão da GOLD)."""
    return ou_sem_dado(valor, lambda v: f"{numero_br(v, casas)}%")


def variacao(valor: object, casas: int = 1) -> str:
    """Variação com sinal: '+27,53%' e '−17,0%'."""
    return ou_sem_dado(valor, lambda v: f"{'+' if v > 0 else ''}{numero_br(v, casas)}%")


def pontos(valor: object, casas: int = 2) -> str:
    """Diferença em pontos percentuais: '+2,84 p.p.'."""
    return ou_sem_dado(valor, lambda v: f"{'+' if v > 0 else ''}{numero_br(v, casas)} p.p.")


def coluna(serie: pd.Series, formatar: Callable[[object], str]) -> pd.Series:
    """Aplica um formatador a uma coluna inteira (para as tabelas de dados)."""
    return serie.map(formatar)


def de_territorio(nome_regiao: str | None) -> str:
    """Complemento com preposição: 'de Santa Catarina' ou 'da região de X'."""
    return f"de {SANTA_CATARINA}" if nome_regiao is None else f"da região de {nome_regiao}"


def de_municipio(nome: str) -> str:
    """Complemento com preposição para um município: 'de Florianópolis'."""
    return f"de {nome}"


def rotulo_mediana(nome_regiao: str | None) -> str:
    """'mediana entre os municípios' (estado) ou '... da região de X' (decisão D34)."""
    return ROTULO_MEDIANA if nome_regiao is None else f"{ROTULO_MEDIANA} da região de {nome_regiao}"


# -- títulos que afirmam o achado ----------------------------------------------------------------

def titulo_serie_pib(de_quem: str, ano_inicial: int, valor_inicial: float, ano_final: int,
                     valor_final: float) -> str:
    """VG2 e PER2: 'PIB nominal de Santa Catarina: de R$ 153,7 bi (2010) para R$ 513,4 bi (2023)'.

    `de_quem` já traz a preposição (de_territorio ou de_municipio).
    """
    return (f"PIB nominal {de_quem}: de {reais_abreviado(valor_inicial)} ({ano_inicial}) "
            f"para {reais_abreviado(valor_final)} ({ano_final}), em valores correntes")


def titulo_concentracao(part_pop: float, part_pib: float, ano_pib: int) -> str:
    """VG3."""
    return (f"Os 10 maiores municípios somam {percentual(part_pop)} da população (Censo 2022) "
            f"e {percentual(part_pib)} do PIB nominal de {ano_pib}")


def titulo_lider(nome: str, participacao: float, o_que: str) -> str:
    """POP1 e ECO1: 'Joinville lidera a população no Censo 2022, com 8,1% do estado'."""
    return f"{nome} lidera {o_que}, com {percentual(participacao)} do estado"


def titulo_variacao_censo(perderam: int, comparaveis: int, de_quem: str) -> str:
    """POP2 (`de_quem` com a preposição)."""
    return (f"{perderam} de {comparaveis} municípios {de_quem} perderam população entre "
            f"os Censos 2010 e 2022")


def titulo_regioes_censo(maior: str, variacao_maior: float, menor: str,
                         variacao_menor: float) -> str:
    """POP3."""
    return (f"Entre os Censos, a região de {maior} cresceu mais ({variacao(variacao_maior)}) "
            f"e a de {menor}, menos ({variacao(variacao_menor)})")


def titulo_estimativa(de_quem: str, ano_inicial: int, valor_inicial: float, ano_final: int,
                      valor_final: float) -> str:
    """POP4 e PER3: sem variação, porque as bases não se comparam (regra 12)."""
    return (f"Estimativa de população {de_quem}: {habitantes_abreviado(valor_inicial)} em "
            f"{ano_inicial} e {habitantes_abreviado(valor_final)} em {ano_final}, em três bases")


def titulo_regioes_pib_pop(acima: int, total: int, ano: int) -> str:
    """VG4."""
    return (f"Em {acima} das {total} regiões intermediárias, a participação no PIB nominal supera "
            f"a participação na população ({ano})")


def titulo_participacao(nome: str, ano_inicial: int, inicio: float, ano_final: int,
                        fim: float) -> str:
    """PER5: 'Itajaí ganhou participação no PIB nominal do estado: 6,5% em 2010 e 9,4% em 2023'."""
    verbo = "ganhou" if fim > inicio else "perdeu" if fim < inicio else "manteve"
    return (f"{nome} {verbo} participação no PIB nominal do estado: {percentual(inicio)} em "
            f"{ano_inicial} e {percentual(fim)} em {ano_final}")


def titulo_per_capita_municipio(nome: str, ano_inicial: int, inicio: float, ano_final: int,
                                fim: float) -> str:
    """PER4: valores publicados nos dois anos, sem variação (o denominador muda; seção 9)."""
    return (f"PIB per capita de {nome}: {reais_abreviado(inicio)} em {ano_inicial} e "
            f"{reais_abreviado(fim)} em {ano_final} (valores publicados, correntes)")


def titulo_censos(nome: str, censo_2010: object, censo_2022: object) -> str:
    """PER3 (b) e CMP3."""
    return (f"Censo de {nome}: {inteiro(censo_2010)} pessoas em 2010 e {inteiro(censo_2022)} "
            f"em 2022")


def posicao_texto(posicao: int | None, total: int) -> str:
    """'3º de 295' ou 'sem dado'."""
    return SEM_DADO if posicao is None else f"{posicao}º de {total}"


def titulo_per_capita(maior: str, valor_maior: float, menor: str, valor_menor: float,
                      ano: int) -> str:
    """ECO3: a razão é entre dois valores municipais publicados, não um per capita novo."""
    razao = numero_br(valor_maior / valor_menor, 1)
    return (f"Em {ano}, o PIB per capita de {maior} ({reais_abreviado(valor_maior)}) é {razao} "
            f"vezes o de {menor} ({reais_abreviado(valor_menor)})")


def titulo_saltos(variacoes: int, municipios: int) -> str:
    """ECO4."""
    return (f"{variacoes} variações anuais do PIB nominal passaram de 50% em módulo, em "
            f"{municipios} municípios")


def titulo_ganhos_participacao(ganharam: int, total: int, nome: str, diferenca: float,
                               ano: int) -> str:
    """ECO2: quantos dos maiores ganharam participação e o maior ganho (ou a menor perda)."""
    return (f"Dos {total} maiores municípios em PIB nominal de {ano}, {ganharam} ganharam "
            f"participação no estado desde 2010; maior variação: {nome} ({pontos(diferenca)})")
