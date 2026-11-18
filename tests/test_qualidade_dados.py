"""Testes de qualidade de dados da SILVER (D22 + D26), a partir de reports/qualidade_20261118.md.

Implementa os testes ERRO aprovados (T1–T8, T10, T11, T13, T14, T15). Só leitura: conecta como
bed_readonly numa transação READ ONLY que é sempre desfeita. Os valores esperados saem do
catálogo (extract.catalogo) e das regras de conteúdo (extract.conteudo), não de números soltos.
"""

from collections.abc import Iterable, Iterator
from decimal import Decimal

import pytest
from sqlalchemy import Connection, text

from brasil_em_dados.extract import catalogo
from brasil_em_dados.extract.conteudo import (
    ANOS_PESQUISAS,
    CODIGOS_NOVOS,
    COD_PESQUISAS,
    N_MUNICIPIOS,
    REGRAS_SIDRA,
    SINAL_AUSENTE,
    TRACO,
    TRACOS_PERMITIDOS_PESQUISAS,
)

pytestmark = pytest.mark.integracao

MAX_EXEMPLOS = 10

# Regra 10: 4212650 e 4220000 foram instalados em 2013; antes disso a ausência é esperada.
ANO_INSTALACAO_NOVOS = 2013

IND_POP_ESTIMADA = "pop_estimada"
IND_POP_CENSO = "pop_censo"
IND_PIB = "pib_corrente"
IND_PIB_PER_CAPITA = "pib_per_capita"

# T11 (D09/D10, dicionário seção pib_per_capita): o Censo 2022 (4709) é o denominador de 2023.
ANO_CENSO_2022 = 2022
ANO_DENOMINADOR_CENSO_2022 = 2023
# Içara (4207007) e Laguna (4209409) em 2012: exceção documentada do teste D10 (dicionário,
# decisoes.md D10; códigos conferidos no relatório de qualidade, observação O3).
EXCLUIDOS_COERENCIA = frozenset({("4207007", 2012), ("4209409", 2012)})
# Margem além do arredondamento do PIB: 1 centavo do arredondamento do per capita publicado.
MARGEM_PER_CAPITA = Decimal("0.01")

# T15: ordem de grandeza da soma anual do PIB de SC em R$. Hoje fica entre 153 bi e 514 bi
# (relatório, 4.2); um erro de fator 1000 cairia fora desta faixa nos dois sentidos.
SOMA_PIB_MIN = Decimal("10e9")
SOMA_PIB_MAX = Decimal("10e12")


# Expectativas derivadas do catálogo e das regras de conteúdo -------------------------------------

def _serie_unica(codigo_indicador: str, anos: frozenset[int] | None = None) -> str:
    """cod_serie do indicador no catálogo (filtrando pelos anos publicados, se dados)."""
    candidatas = [s.cod_serie for s in catalogo.series() if s.codigo_indicador == codigo_indicador
                  and (anos is None or _anos_publicados()[s.cod_serie] == anos)]
    assert len(candidatas) == 1, f"{codigo_indicador}: esperada 1 série, achadas {candidatas}"
    return candidatas[0]


def _anos_publicados() -> dict[str, frozenset[int]]:
    """Anos que cada série publica: REGRAS_SIDRA e ANOS_PESQUISAS."""
    anos = {cod: regra.anos for cod, regra in REGRAS_SIDRA.items()}
    anos[COD_PESQUISAS] = frozenset(ANOS_PESQUISAS)
    series_catalogo = {s.cod_serie for s in catalogo.series()}
    assert set(anos) == series_catalogo, "regras de conteúdo e catálogo cobrem séries diferentes"
    return anos


def _linhas_por_ano() -> dict[str, int]:
    """Linhas esperadas por ano em cada série (n_linhas / anos; 295 localidades na Pesquisas)."""
    esperado = {}
    for cod, regra in REGRAS_SIDRA.items():
        assert regra.n_linhas % len(regra.anos) == 0, f"{cod}: n_linhas não divide pelos anos"
        por_ano = regra.n_linhas // len(regra.anos)
        assert por_ano == N_MUNICIPIOS - len(regra.ausentes), f"{cod}: regra incoerente"
        esperado[cod] = por_ano
    esperado[COD_PESQUISAS] = N_MUNICIPIOS
    return esperado


def _nulos_previstos() -> set[tuple[str, str, int, str]]:
    """(série, município, ano, sinal) com valor NULL previstos pelas regras (dicionário, seção 5)."""
    previstos = {(cod, municipio, ano, SINAL_AUSENTE)
                 for cod, regra in REGRAS_SIDRA.items()
                 for municipio, ano in regra.sinais_permitidos}
    codigo_7 = {codigo[:6]: codigo for codigo in CODIGOS_NOVOS}
    previstos |= {(COD_PESQUISAS, codigo_7[localidade], ano, TRACO)
                  for localidade, ano in TRACOS_PERMITIDOS_PESQUISAS}
    return previstos


def _sem_valor_previsto() -> set[tuple[str, str, int]]:
    """(série, município, ano) sem valor: NULL com sinal ou sem linha (ausentes da 1378, D08)."""
    sem_valor = {(cod, municipio, ano) for cod, municipio, ano, _ in _nulos_previstos()}
    sem_valor |= {(cod, municipio, ano) for cod, regra in REGRAS_SIDRA.items()
                  for municipio in regra.ausentes for ano in regra.anos}
    return sem_valor


def _exemplos(itens: Iterable) -> list:
    """Até MAX_EXEMPLOS itens, ordenados, para as mensagens de falha."""
    return sorted(itens)[:MAX_EXEMPLOS]


# Conexão somente leitura ----------------------------------------------------------------------

@pytest.fixture
def conexao(engine_readonly) -> Iterator[Connection]:
    """Conexão bed_readonly numa transação READ ONLY sempre desfeita; pula se a fato está vazia."""
    with engine_readonly.connect() as conexao:
        transacao = conexao.begin()
        try:
            conexao.execute(text("SET TRANSACTION READ ONLY"))
            carregada = conexao.execute(text(
                "SELECT EXISTS (SELECT 1 FROM silver.fato_indicador_municipio)")).scalar()
            if not carregada:
                pytest.skip("silver.fato_indicador_municipio vazia; "
                            "rode python -m brasil_em_dados.load tudo")
            yield conexao
        finally:
            transacao.rollback()


# T1 ------------------------------------------------------------------------------------------

def test_t1_contagem_por_serie_e_ano_igual_a_publicada(conexao):
    por_ano = _linhas_por_ano()
    esperado = {(cod, ano): por_ano[cod]
                for cod, anos in _anos_publicados().items() for ano in anos}
    obtido = {(cod, ano): n for cod, ano, n in conexao.execute(text(
        "SELECT cod_serie, ano, count(*) FROM silver.fato_indicador_municipio GROUP BY 1, 2"))}
    diferencas = [(chave, esperado.get(chave), obtido.get(chave))
                  for chave in set(esperado) | set(obtido) if esperado.get(chave) != obtido.get(chave)]
    assert not diferencas, (f"{len(diferencas)} (série, ano) com contagem diferente "
                            f"[(chave, esperado, obtido)]: {_exemplos(diferencas)}")


# T2 ------------------------------------------------------------------------------------------

def test_t2_nenhuma_linha_em_ano_que_a_serie_nao_publica(conexao):
    publicados = [(cod, ano) for cod, anos in _anos_publicados().items() for ano in anos]
    fora = conexao.execute(text(
        "WITH pub AS (SELECT * FROM unnest(CAST(:series AS text[]), CAST(:anos AS int[]))"
        "             AS p(cod_serie, ano)) "
        "SELECT f.cod_serie, f.ano, count(*) FROM silver.fato_indicador_municipio f "
        "WHERE NOT EXISTS (SELECT 1 FROM pub p WHERE p.cod_serie = f.cod_serie AND p.ano = f.ano) "
        "GROUP BY 1, 2 ORDER BY 1, 2"),
        {"series": [c for c, _ in publicados], "anos": [a for _, a in publicados]}).all()
    assert not fora, f"linhas em anos não publicados [(série, ano, linhas)]: {fora[:MAX_EXEMPLOS]}"


# T3 ------------------------------------------------------------------------------------------

def test_t3_cada_indicador_e_ano_vem_de_uma_unica_serie(conexao):
    misturados = conexao.execute(text(
        "SELECT codigo_indicador, ano, array_agg(DISTINCT cod_serie ORDER BY cod_serie) "
        "FROM silver.fato_indicador_municipio GROUP BY 1, 2 "
        "HAVING count(DISTINCT cod_serie) > 1 ORDER BY 1, 2")).all()
    assert not misturados, f"(indicador, ano) com mais de uma série: {misturados[:MAX_EXEMPLOS]}"


# T4 ------------------------------------------------------------------------------------------

def test_t4_sem_orfaos_e_toda_dimensao_usada_na_fato(conexao):
    contagens = conexao.execute(text("""
        SELECT
         (SELECT count(*) FROM silver.fato_indicador_municipio f
           LEFT JOIN silver.dim_municipio m USING (cod_municipio)
           WHERE m.cod_municipio IS NULL) AS fato_sem_municipio,
         (SELECT count(*) FROM silver.fato_indicador_municipio f
           LEFT JOIN silver.dim_indicador i USING (codigo_indicador)
           WHERE i.codigo_indicador IS NULL) AS fato_sem_indicador,
         (SELECT count(*) FROM silver.fato_indicador_municipio f
           LEFT JOIN silver.dim_serie s
             ON s.cod_serie = f.cod_serie AND s.codigo_indicador = f.codigo_indicador
           WHERE s.cod_serie IS NULL) AS fato_sem_serie_do_indicador,
         (SELECT count(*) FROM silver.dim_serie s
           LEFT JOIN silver.dim_indicador i USING (codigo_indicador)
           WHERE i.codigo_indicador IS NULL) AS serie_sem_indicador,
         (SELECT count(*) FROM silver.dim_municipio m WHERE NOT EXISTS (
           SELECT 1 FROM silver.fato_indicador_municipio f
           WHERE f.cod_municipio = m.cod_municipio)) AS municipio_sem_fato,
         (SELECT count(*) FROM silver.dim_indicador i WHERE NOT EXISTS (
           SELECT 1 FROM silver.fato_indicador_municipio f
           WHERE f.codigo_indicador = i.codigo_indicador)) AS indicador_sem_fato,
         (SELECT count(*) FROM silver.dim_serie s WHERE NOT EXISTS (
           SELECT 1 FROM silver.fato_indicador_municipio f
           WHERE f.cod_serie = s.cod_serie)) AS serie_sem_fato
    """)).one()._asdict()
    problemas = {nome: n for nome, n in contagens.items() if n}
    assert not problemas, f"órfãos ou dimensões sem uso na fato: {problemas}"


# T5 ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("cod_serie", sorted(_anos_publicados()))
def test_t5_cobertura_da_regra_10_por_serie(conexao, cod_serie):
    assert conexao.execute(text("SELECT count(*) FROM silver.dim_municipio")).scalar() \
        == N_MUNICIPIOS, "dim_municipio incompleta: a grade município × ano não vale"
    sem_valor = conexao.execute(text(
        "SELECT m.cod_municipio, p.ano, f.cod_municipio IS NOT NULL AS tem_linha "
        "FROM unnest(CAST(:anos AS int[])) AS p(ano) CROSS JOIN silver.dim_municipio m "
        "LEFT JOIN silver.fato_indicador_municipio f "
        "  ON f.cod_serie = :serie AND f.ano = p.ano AND f.cod_municipio = m.cod_municipio "
        "WHERE f.valor IS NULL"),
        {"serie": cod_serie, "anos": sorted(_anos_publicados()[cod_serie])}).all()

    violacoes = [(m, ano, "NULL" if tem_linha else "sem linha") for m, ano, tem_linha in sem_valor
                 if not (m in CODIGOS_NOVOS and ano < ANO_INSTALACAO_NOVOS)]
    assert not violacoes, (f"{cod_serie}: {len(violacoes)} município × ano sem valor fora da "
                           f"regra 10: {_exemplos(violacoes)}")
    # Linhas inexistentes só onde a regra da série prevê (1378 sem os municípios novos, D08).
    sem_linha = {(cod_serie, m, ano) for m, ano, tem_linha in sem_valor if not tem_linha}
    previstas = {chave for chave in _sem_valor_previsto()
                 if chave[0] == cod_serie} - {(s, m, a) for s, m, a, _ in _nulos_previstos()}
    assert sem_linha == previstas, (f"{cod_serie}: sem linha inesperada {_exemplos(sem_linha - previstas)}, "
                                    f"prevista e presente {_exemplos(previstas - sem_linha)}")


# T6 ------------------------------------------------------------------------------------------

def test_t6_nulos_sao_exatamente_os_previstos_e_todos_tem_sinal(conexao):
    nulos = conexao.execute(text(
        "SELECT cod_serie, cod_municipio, ano, sinal_origem FROM silver.fato_indicador_municipio "
        "WHERE valor IS NULL")).all()
    sem_sinal = [tuple(linha) for linha in nulos if linha.sinal_origem is None]
    assert not sem_sinal, f"NULL sem sinal_origem (regra 9): {_exemplos(sem_sinal)}"

    obtidos = {tuple(linha) for linha in nulos}
    previstos = _nulos_previstos()
    # 14 = 6579: 2 novos × 2011 + 5938: 2 × 2010–2012 + Pesquisas: 2 × 2010–2012 (dicionário, seção 5).
    assert len(previstos) == 14, (
        f"a regra de NULLs previstos mudou: {len(previstos)} em vez de 14: {sorted(previstos)}")
    assert obtidos == previstos, (f"NULL inesperado: {_exemplos(obtidos - previstos)}; "
                                  f"NULL previsto ausente: {_exemplos(previstos - obtidos)}")


# T7 ------------------------------------------------------------------------------------------

def test_t7_unidade_e_conversao_por_indicador_iguais_ao_catalogo(conexao):
    esperado = {
        codigo: ({indicador.unidade_armazenada},
                 {(s.unidade_origem, s.fator_conversao) for s in catalogo.series()
                  if s.codigo_indicador == codigo})
        for codigo, indicador in catalogo.INDICADORES.items()
    }
    obtido: dict[str, tuple[set, set]] = {}
    for codigo, unidade, origem, fator in conexao.execute(text(
            "SELECT DISTINCT f.codigo_indicador, i.unidade_armazenada, s.unidade_origem, "
            "       s.fator_conversao "
            "FROM silver.fato_indicador_municipio f "
            "JOIN silver.dim_indicador i USING (codigo_indicador) "
            "JOIN silver.dim_serie s ON s.cod_serie = f.cod_serie")):
        unidades, pares = obtido.setdefault(codigo, (set(), set()))
        unidades.add(unidade)
        pares.add((origem, fator))  # Decimal('1000') == 1000 e tem o mesmo hash

    for codigo, (unidades, pares) in obtido.items():
        assert len(unidades) == 1, f"{codigo}: mais de uma unidade_armazenada {unidades}"
        assert len(pares) == 1, f"{codigo}: mais de um (unidade_origem, fator) {pares}"
    assert obtido == esperado, (f"unidade/fator por indicador difere do catálogo: "
                                f"banco {obtido}, catálogo {esperado}")

    # Regra 2: o tipo_medida que cada linha da fato herda é o do catálogo (censo ≠ estimativa).
    tipos = dict(conexao.execute(text(
        "SELECT codigo_indicador, tipo_medida FROM silver.dim_indicador")).all())
    tipos_catalogo = {codigo: i.tipo_medida for codigo, i in catalogo.INDICADORES.items()}
    assert tipos == tipos_catalogo, (f"tipo_medida difere do catálogo: banco {tipos}, "
                                     f"catálogo {tipos_catalogo}")


# T8 ------------------------------------------------------------------------------------------

def test_t8_nenhum_valor_negativo(conexao):
    negativos = conexao.execute(text(
        "SELECT cod_serie, cod_municipio, ano, valor FROM silver.fato_indicador_municipio "
        "WHERE valor < 0 ORDER BY 1, 2, 3 LIMIT :limite"), {"limite": MAX_EXEMPLOS}).all()
    assert not negativos, f"valores negativos (até {MAX_EXEMPLOS}): {negativos}"


# T10 -----------------------------------------------------------------------------------------

def _divisores_de_conversao() -> list[tuple[str, int]]:
    """(série, divisor exato do valor): o fator de conversão quando > 1 (fonte em inteiros,
    ex.: PIB em mil reais) e 1 para populações (Pessoas inteiras)."""
    divisores = []
    for serie in catalogo.series():
        unidade = catalogo.INDICADORES[serie.codigo_indicador].unidade_armazenada
        if serie.fator_conversao > 1:
            divisores.append((serie.cod_serie, serie.fator_conversao))
        elif unidade == "Pessoas":
            divisores.append((serie.cod_serie, 1))
    return divisores


@pytest.mark.parametrize(("cod_serie", "divisor"), _divisores_de_conversao())
def test_t10_conversao_coerente_pib_multiplo_de_mil_e_populacao_inteira(conexao, cod_serie,
                                                                         divisor):
    fora = conexao.execute(text(
        "SELECT cod_municipio, ano, valor FROM silver.fato_indicador_municipio "
        "WHERE cod_serie = :serie AND mod(valor, :divisor) <> 0 ORDER BY 1, 2 LIMIT :limite"),
        {"serie": cod_serie, "divisor": divisor, "limite": MAX_EXEMPLOS}).all()
    assert not fora, f"{cod_serie}: valores que não são múltiplos de {divisor}: {fora}"


# T11 -----------------------------------------------------------------------------------------

def _pares_coerencia_esperados() -> int:
    """Pares PIB × per capita × população esperados no T11 (hoje 3.534).

    12 anos (6579 em 2011–2021 + 4709 aplicada a 2023) × 295 municípios, menos os pares em que
    PIB, per capita ou população não têm valor previsto (municípios novos) e as exclusões D10.
    """
    serie_pib = _serie_unica(IND_PIB)
    serie_pc = _serie_unica(IND_PIB_PER_CAPITA)
    serie_est = _serie_unica(IND_POP_ESTIMADA)
    serie_censo = _serie_unica(IND_POP_CENSO, frozenset({ANO_CENSO_2022}))
    sem_valor = _sem_valor_previsto()
    pop_do_ano = {ano: (serie_est, ano) for ano in _anos_publicados()[serie_est]}
    pop_do_ano[ANO_DENOMINADOR_CENSO_2022] = (serie_censo, ANO_CENSO_2022)
    total = 0
    for ano, (serie_pop, ano_pop) in pop_do_ano.items():
        fora = {m for m in CODIGOS_NOVOS
                if (serie_pib, m, ano) in sem_valor or (serie_pc, m, ano) in sem_valor
                or (serie_pop, m, ano_pop) in sem_valor}
        fora |= {m for m, ano_excluido in EXCLUIDOS_COERENCIA if ano_excluido == ano}
        total += N_MUNICIPIOS - len(fora)
    return total


def test_t11_pib_sobre_populacao_bate_com_per_capita_publicado(conexao):
    serie_pib = _serie_unica(IND_PIB)
    # Tolerância 500/pop: o SIDRA arredonda o PIB para inteiro em mil reais (fator 1000), então
    # o PIB em R$ carrega erro de até meio fator; dividido pela população, 500/pop reais.
    meio_fator = Decimal(catalogo.FONTES[serie_pib].fator_conversao) / 2
    parametros = {
        "serie_pib": serie_pib,
        "serie_pc": _serie_unica(IND_PIB_PER_CAPITA),
        "serie_est": _serie_unica(IND_POP_ESTIMADA),
        "serie_censo": _serie_unica(IND_POP_CENSO, frozenset({ANO_CENSO_2022})),
        "ano_censo": ANO_CENSO_2022,
        "ano_denominador": ANO_DENOMINADOR_CENSO_2022,
        "excl_mun": [m for m, _ in sorted(EXCLUIDOS_COERENCIA)],
        "excl_ano": [a for _, a in sorted(EXCLUIDOS_COERENCIA)],
        "meio_fator": meio_fator,
        "margem": MARGEM_PER_CAPITA,
    }
    base = """
        WITH pop AS (
          SELECT cod_municipio, ano, valor FROM silver.fato_indicador_municipio
           WHERE cod_serie = :serie_est
          UNION ALL
          SELECT cod_municipio, CAST(:ano_denominador AS smallint), valor
            FROM silver.fato_indicador_municipio
           WHERE cod_serie = :serie_censo AND ano = :ano_censo),
        excl AS (SELECT * FROM unnest(CAST(:excl_mun AS text[]), CAST(:excl_ano AS int[]))
                 AS e(cod_municipio, ano)),
        pares AS (
          SELECT p.cod_municipio, p.ano,
                 abs(p.valor / pp.valor - pc.valor) AS dif,
                 CAST(:meio_fator AS numeric) / pp.valor + CAST(:margem AS numeric) AS tol
            FROM silver.fato_indicador_municipio p
            JOIN pop pp ON pp.cod_municipio = p.cod_municipio AND pp.ano = p.ano
            JOIN silver.fato_indicador_municipio pc
              ON pc.cod_municipio = p.cod_municipio AND pc.ano = p.ano
             AND pc.cod_serie = :serie_pc
           WHERE p.cod_serie = :serie_pib
             AND p.valor IS NOT NULL AND pc.valor IS NOT NULL AND pp.valor IS NOT NULL
             AND NOT EXISTS (SELECT 1 FROM excl e
                             WHERE e.cod_municipio = p.cod_municipio AND e.ano = p.ano))
    """
    n_pares, n_fora = conexao.execute(text(
        base + "SELECT count(*), count(*) FILTER (WHERE dif > tol) FROM pares"), parametros).one()
    exemplos = conexao.execute(text(
        base + "SELECT cod_municipio, ano, round(dif, 4), round(tol, 4) FROM pares "
               "WHERE dif > tol ORDER BY dif / tol DESC LIMIT :limite"),
        {**parametros, "limite": MAX_EXEMPLOS}).all()

    assert n_pares == _pares_coerencia_esperados(), "número de pares comparados mudou"
    assert n_fora == 0, (f"{n_fora} de {n_pares} pares com |PIB/pop − per capita| acima da "
                         f"tolerância [(município, ano, diferença, tolerância)]: {exemplos}")


# T13 -----------------------------------------------------------------------------------------

def test_t13_data_coleta_casa_com_arquivo_raw_de_coleta_com_sucesso(conexao):
    # O nome do arquivo RAW é {cod_serie}/{AAAAMMDDTHHMMSSfffZ}.json, com o coletado_em em UTC
    # (extract.raw.carimbo_utc); data_coleta é esse mesmo instante.
    resultado = conexao.execute(text("""
        SELECT f.cod_serie, count(*) AS linhas,
          count(*) FILTER (WHERE EXISTS (
            SELECT 1 FROM silver.controle_execucao c
             WHERE c.cod_serie = f.cod_serie AND c.status = 'sucesso'
               AND split_part(c.arquivo, '/', 1) = f.cod_serie
               AND to_char(f.data_coleta AT TIME ZONE 'UTC', 'YYYYMMDD"T"HH24MISSMS"Z"')
                   = split_part(split_part(c.arquivo, '/', 2), '.', 1)
               AND f.data_coleta BETWEEN c.inicio AND c.fim)) AS casadas,
          count(*) FILTER (WHERE f.data_coleta > (
            SELECT max(c.fim) FROM silver.controle_execucao c
             WHERE c.cod_serie = f.cod_serie AND c.status = 'sucesso')) AS apos_ultima,
          count(*) FILTER (WHERE NOT EXISTS (
            SELECT 1 FROM silver.controle_execucao c
             WHERE c.cod_serie = f.cod_serie AND c.status = 'sucesso')) AS sem_sucesso
        FROM silver.fato_indicador_municipio f GROUP BY 1 ORDER BY 1
    """)).all()
    problemas = [tuple(linha) for linha in resultado
                 if linha.casadas != linha.linhas or linha.apos_ultima or linha.sem_sucesso]
    assert not problemas, ("séries com data_coleta sem coleta de sucesso correspondente "
                           f"[(série, linhas, casadas, após a última, sem sucesso)]: {problemas}")


# T14 -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("cod_serie", sorted(_anos_publicados()))
def test_t14_n_registros_da_ultima_coleta_bate_com_a_fato(conexao, cod_serie):
    n_registros = conexao.execute(text(
        "SELECT n_registros FROM silver.controle_execucao "
        "WHERE cod_serie = :serie AND status = 'sucesso' ORDER BY inicio DESC LIMIT 1"),
        {"serie": cod_serie}).scalar()
    assert n_registros is not None, f"{cod_serie}: nenhuma coleta com sucesso no controle"
    linhas = conexao.execute(text(
        "SELECT count(*) FROM silver.fato_indicador_municipio WHERE cod_serie = :serie"),
        {"serie": cod_serie}).scalar()
    # API de Pesquisas: n_registros = localidades (padrao_coleta.md, seção 6); 1 linha por ano.
    por_registro = len(ANOS_PESQUISAS) if cod_serie == COD_PESQUISAS else 1
    assert linhas == n_registros * por_registro, (
        f"{cod_serie}: fato com {linhas} linhas, última coleta com n_registros={n_registros} "
        f"(× {por_registro})")


# T15 -----------------------------------------------------------------------------------------

def test_t15_soma_anual_do_pib_na_ordem_de_grandeza_esperada(conexao):
    serie_pib = _serie_unica(IND_PIB)
    somas = dict(conexao.execute(text(
        "SELECT ano, sum(valor) FROM silver.fato_indicador_municipio "
        "WHERE cod_serie = :serie GROUP BY 1"), {"serie": serie_pib}).all())
    assert set(somas) == _anos_publicados()[serie_pib], f"anos com PIB: {sorted(somas)}"
    fora = {ano: soma for ano, soma in sorted(somas.items())
            if soma is None or not SOMA_PIB_MIN <= soma <= SOMA_PIB_MAX}
    assert not fora, (f"soma anual do PIB (R$) fora de [{SOMA_PIB_MIN:,.0f}, "
                      f"{SOMA_PIB_MAX:,.0f}]: {fora}")
