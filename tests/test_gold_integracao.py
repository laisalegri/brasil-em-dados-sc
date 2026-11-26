"""Testes de integração da GOLD (D30).

Os testes de conteúdo recriam as views a partir de sql/gold/ como bed_app, numa transação que é
SEMPRE desfeita: testam os arquivos atuais sem mudar o banco. Os testes de leitura como
bed_readonly usam as views já aplicadas (python -m brasil_em_dados.db.aplicar_gold).
"""

from collections.abc import Iterator
from decimal import Decimal

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import OperationalError

from brasil_em_dados.config import PASTA_GOLD
from brasil_em_dados.db import sqlstate
from brasil_em_dados.db.aplicar_ddl import ler_scripts
from brasil_em_dados.db.aplicar_gold import recriar_em_conexao, views_em_ordem
from brasil_em_dados.extract import catalogo
from brasil_em_dados.extract.conteudo import ANOS_PESQUISAS, CODIGOS_NOVOS, N_MUNICIPIOS, REGRAS_SIDRA
from tests.apoio_banco import total_sc_2012_documentado

pytestmark = pytest.mark.integracao

VIEWS = views_em_ordem(ler_scripts(PASTA_GOLD))
# Municípios novos e de origem (desmembramento): Pescaria Brava–Laguna, Balneário Rincão–Içara.
ORIGEM = {"4212650": "4209409", "4220000": "4207007"}


LOCK_TIMEOUT = "10s"
# lock_not_available (estourou o lock_timeout) e deadlock_detected.
BLOQUEIO_POR_OUTRA_SESSAO = {"55P03", "40P01"}
MENSAGEM_BLOQUEIO = ("Não foi possível recriar as views da GOLD: outra sessão está usando o banco "
                     "(Streamlit, refresh do Power BI, notebook ou auditoria). Feche-a e rode o "
                     "pytest com o banco livre (README, passo de testes).")


@pytest.fixture
def gold(engine_app) -> Iterator[Connection]:
    """Conexão bed_app com as views recriadas dos arquivos atuais, numa transação desfeita.

    DROP VIEW pede trava exclusiva: se outra sessão estiver lendo a GOLD, a espera para em
    LOCK_TIMEOUT e o teste falha com mensagem clara, em vez de travar ou dar deadlock obscuro.
    """
    with engine_app.connect() as conexao:
        transacao = conexao.begin()
        try:
            if not conexao.execute(text(
                    "SELECT count(*) FROM silver.fato_indicador_municipio")).scalar():
                pytest.skip("SILVER vazia; rode python -m brasil_em_dados.load tudo")
            conexao.execute(text(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'"))
            try:
                recriar_em_conexao(conexao, ler_scripts(PASTA_GOLD))
            except OperationalError as exc:
                if sqlstate(exc) in BLOQUEIO_POR_OUTRA_SESSAO:
                    pytest.fail(f"{MENSAGEM_BLOQUEIO} SQLSTATE {sqlstate(exc)}.", pytrace=False)
                raise
            yield conexao
        finally:
            transacao.rollback()


def _um(conexao: Connection, sql: str, **parametros):
    return conexao.execute(text(sql), parametros).one()


def _anos_publicados_por_indicador() -> dict[str, set[int]]:
    """Anos de cada indicador, derivados das regras de conteúdo de cada série."""
    anos: dict[str, set[int]] = {}
    for serie in catalogo.series():
        regra = REGRAS_SIDRA.get(serie.cod_serie)
        anos_serie = set(regra.anos) if regra else set(ANOS_PESQUISAS)
        anos.setdefault(serie.codigo_indicador, set()).update(anos_serie)
    return anos


# 1. Tamanho da grade --------------------------------------------------------------------------

def test_grade_tem_todos_os_municipios_em_todos_os_anos_publicados(gold):
    esperado = N_MUNICIPIOS * sum(len(a) for a in _anos_publicados_por_indicador().values())
    assert esperado == 12095  # 295 × (14 PIB + 14 per capita + 2 Censo + 11 estimativa)
    assert _um(gold, "SELECT count(*) FROM gold.grade_indicador_municipio_ano")[0] == esperado


# 2. Dupla contagem de 2012 (regra 13) ---------------------------------------------------------

def test_soma_estadual_de_pop_estimada_2012_e_o_total_de_sc(gold):
    valor, excluidos, aviso = _um(gold, """
        SELECT valor, municipios_excluidos, aviso FROM gold.agregado_regiao_ano
        WHERE nivel = 'estado' AND codigo_indicador = 'pop_estimada' AND ano = 2012""")
    assert valor == total_sc_2012_documentado()
    assert excluidos == len(CODIGOS_NOVOS)
    assert "regra 13" in aviso


def test_aviso_de_dupla_contagem_so_nas_duas_linhas_de_2012(gold):
    for view in ("gold.grade_indicador_municipio_ano", "gold.painel_municipio_ano"):
        linhas = gold.execute(text(
            f"SELECT cod_municipio, ano, aviso FROM {view} WHERE aviso IS NOT NULL")).all()
        assert {(m, a) for m, a, _ in linhas} == {(c, 2012) for c in CODIGOS_NOVOS}, view
        assert all(aviso == "dupla contagem 2012 (regra 13)" for _, _, aviso in linhas)


# 3. Quebras de série (regra 12) ---------------------------------------------------------------

def test_variacao_2012_2013_e_sempre_nula_e_nao_comparavel(gold):
    linhas, calculadas, comparaveis, sem_motivo = _um(gold, """
        SELECT count(*), count(variacao_absoluta) + count(variacao_percentual),
               count(*) FILTER (WHERE comparavel IS NOT FALSE),
               count(*) FILTER (WHERE motivo IS NULL)
        FROM gold.variacao_anual WHERE codigo_indicador = 'pop_estimada' AND ano = 2013""")
    # 295 linhas: sem isso o teste passaria vazio se o par 2012→2013 sumisse.
    assert (linhas, calculadas, comparaveis, sem_motivo) == (N_MUNICIPIOS, 0, 0, 0)


def test_variacao_2017_2018_e_calculada_mas_nao_comparavel(gold):
    linhas, calculadas, comparaveis, motivo = _um(gold, """
        SELECT count(*), count(variacao_absoluta), count(*) FILTER (WHERE comparavel),
               min(motivo)
        FROM gold.variacao_anual WHERE codigo_indicador = 'pop_estimada' AND ano = 2018""")
    assert (linhas, calculadas, comparaveis) == (N_MUNICIPIOS, N_MUNICIPIOS, 0)
    assert "2018" in motivo and "2013–2017" in motivo


def test_base_da_estimativa_tem_tres_faixas(gold):
    faixas = dict(gold.execute(text("""
        SELECT base_estimativa, array_agg(DISTINCT ano ORDER BY ano)
        FROM gold.painel_municipio_ano WHERE pop_estimada IS NOT NULL GROUP BY 1""")).all())
    assert faixas == {"ate_2012": [2011, 2012], "2013_2017": list(range(2013, 2018)),
                      "desde_2018": list(range(2018, 2022))}


# 4. Censo 2010 × 2022 -------------------------------------------------------------------------

def test_variacao_censo_de_florianopolis(gold):
    linha = _um(gold, "SELECT * FROM gold.variacao_populacao_censo WHERE cod_municipio = '4205407'")
    assert (linha.pop_censo_2010, linha.pop_censo_2022) == (Decimal(421240), Decimal(537211))
    assert linha.variacao_absoluta == Decimal(115971)
    assert linha.variacao_percentual == Decimal("27.53")
    assert linha.motivo is None


def test_municipios_novos_sem_variacao_de_censo_e_com_motivo(gold):
    linhas = gold.execute(text("""
        SELECT cod_municipio, variacao_absoluta, motivo FROM gold.variacao_populacao_censo
        WHERE cod_municipio = ANY(:novos)"""), {"novos": sorted(CODIGOS_NOVOS)}).all()
    assert len(linhas) == len(CODIGOS_NOVOS)
    assert all(v is None and "instalado em 2013" in motivo for _, v, motivo in linhas)


# 5. Sem per capita agregado (regra 4) ---------------------------------------------------------

@pytest.mark.parametrize("view", ["gold.agregado_regiao_ano", "gold.participacao_estadual"])
def test_nenhuma_agregacao_expoe_per_capita(gold, view):
    tabela = view.split(".")[1]
    colunas = gold.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'gold' AND table_name = :t"), {"t": tabela}).scalars().all()
    assert not [c for c in colunas if "per_capita" in c]
    indicadores = gold.execute(text(f"SELECT DISTINCT codigo_indicador FROM {view}")).scalars().all()
    assert "pib_per_capita" not in indicadores


# 6. Os municípios novos estão na mesma região do município de origem --------------------------

def test_municipios_novos_na_mesma_regiao_do_municipio_de_origem(gold):
    # Se não estivessem, excluir os novos em 2012 deixaria a região de origem com dupla contagem.
    for novo, origem in ORIGEM.items():
        regioes = gold.execute(text("""
            SELECT DISTINCT cod_regiao_imediata, cod_regiao_intermediaria
            FROM gold.dim_municipio WHERE cod_municipio IN (:novo, :origem)"""),
            {"novo": novo, "origem": origem}).all()
        assert len(regioes) == 1, f"{novo} e {origem} em regiões diferentes: {regioes}"


# 7. Status da grade ---------------------------------------------------------------------------

def test_grade_sem_status_sem_dado(gold):
    # Regra 10: só os municípios novos antes de 2013 ficam sem valor.
    sem_dado = gold.execute(text(
        "SELECT cod_municipio, codigo_indicador, ano FROM gold.grade_indicador_municipio_ano "
        "WHERE status = 'sem_dado' LIMIT 10")).all()
    assert not sem_dado
    nao_instalados = gold.execute(text(
        "SELECT DISTINCT cod_municipio FROM gold.grade_indicador_municipio_ano "
        "WHERE status = 'municipio_nao_instalado'")).scalars().all()
    assert set(nao_instalados) == set(CODIGOS_NOVOS)


# 8. Painel sem população mista (regra 2) ------------------------------------------------------

def test_painel_separa_estimativa_e_censo(gold):
    colunas = gold.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'gold' AND table_name = 'painel_municipio_ano'")).scalars().all()
    assert {"pop_estimada", "pop_censo", "pib_corrente_reais", "pib_per_capita_reais"} <= set(colunas)
    misturadas = [c for c in colunas if "pop" in c and c not in ("pop_estimada", "pop_censo")]
    assert not misturadas
    assert _um(gold, "SELECT count(*) FROM gold.painel_municipio_ano")[0] == N_MUNICIPIOS * 14


# 9. Privilégios depois de recriar --------------------------------------------------------------

@pytest.mark.parametrize("view", VIEWS)
def test_view_recriada_continua_legivel_e_so_leitura_para_o_readonly(gold, view):
    def privilegio(tipo: str) -> bool:
        return gold.execute(text("SELECT has_table_privilege('bed_readonly', :v, :p)"),
                            {"v": view, "p": tipo}).scalar()

    assert privilegio("SELECT") is True
    assert privilegio("INSERT") is False


# 10. bed_readonly lê todas as views aplicadas --------------------------------------------------

def test_readonly_le_todas_as_views_aplicadas(engine_readonly):
    with engine_readonly.connect() as conexao:
        aplicadas = set(conexao.execute(text(
            "SELECT 'gold.' || table_name FROM information_schema.views "
            "WHERE table_schema = 'gold'")).scalars())
        if not aplicadas:
            pytest.skip("GOLD não aplicada; rode python -m brasil_em_dados.db.aplicar_gold")
        assert set(VIEWS) <= aplicadas, f"views não aplicadas: {sorted(set(VIEWS) - aplicadas)}"
        for view in VIEWS:
            conexao.execute(text(f"SELECT count(*) FROM {view}")).scalar()


# Revisão do D30 ------------------------------------------------------------------------------

def test_grade_tem_uma_linha_por_chave(gold):
    # Uma segunda série no mesmo (indicador, ano) apareceria aqui como chave repetida.
    repetidas = gold.execute(text("""
        SELECT cod_municipio, codigo_indicador, ano, count(*)
        FROM gold.grade_indicador_municipio_ano GROUP BY 1, 2, 3 HAVING count(*) > 1
        LIMIT 10""")).all()
    assert not repetidas


def test_base_da_estimativa_esta_na_grade_e_na_participacao(gold):
    for view in ("gold.grade_indicador_municipio_ano", "gold.participacao_estadual"):
        sem_base, base_fora = _um(gold, f"""
            SELECT count(*) FILTER (WHERE codigo_indicador = 'pop_estimada'
                                    AND base_estimativa IS NULL),
                   count(*) FILTER (WHERE codigo_indicador <> 'pop_estimada'
                                    AND base_estimativa IS NOT NULL)
            FROM {view}""")
        assert (sem_base, base_fora) == (0, 0), view


def test_participacao_soma_100_por_cento_em_cada_indicador_e_ano(gold):
    # Arredondamento a 4 casas em até 295 parcelas: erro máximo de 0,015 ponto percentual.
    fora = gold.execute(text("""
        SELECT codigo_indicador, ano, sum(participacao_percentual)
        FROM gold.participacao_estadual GROUP BY 1, 2
        HAVING abs(sum(participacao_percentual) - 100) > 0.02""")).all()
    assert not fora, f"participações que não somam 100%: {fora}"


def test_total_do_estado_e_a_soma_da_grade_fora_das_exclusoes(gold):
    divergentes = gold.execute(text("""
        SELECT e.codigo_indicador, e.ano, e.valor, g.soma
        FROM gold.agregado_regiao_ano e
        JOIN (SELECT codigo_indicador, ano, sum(valor) FILTER (WHERE aviso IS NULL) AS soma
              FROM gold.grade_indicador_municipio_ano GROUP BY 1, 2) g USING (codigo_indicador, ano)
        WHERE e.nivel = 'estado' AND e.valor IS DISTINCT FROM g.soma""")).all()
    assert not divergentes


def test_comparavel_e_nulo_quando_falta_um_dos_valores(gold):
    errados = _um(gold, """
        SELECT count(*) FROM gold.variacao_anual
        WHERE (valor IS NULL OR valor_anterior IS NULL) AND comparavel IS TRUE""")[0]
    assert errados == 0


def test_variacao_anual_tem_um_par_por_ano_consecutivo(gold):
    anos = _anos_publicados_por_indicador()
    esperado = N_MUNICIPIOS * sum(len(anos[i]) - 1 for i in ("pop_estimada", "pib_corrente"))
    assert _um(gold, "SELECT count(*) FROM gold.variacao_anual")[0] == esperado


def test_variacao_do_pib_e_calculada_em_todo_par_com_valores(gold):
    # Regressão do D31: sem base_estimativa, a quebra virava NULL e zerava a variação do PIB.
    sem_variacao, errados, nao_comparaveis = _um(gold, """
        SELECT count(*) FILTER (WHERE variacao_absoluta IS NULL OR variacao_percentual IS NULL),
               count(*) FILTER (WHERE variacao_absoluta <> valor - valor_anterior),
               count(*) FILTER (WHERE comparavel IS NOT TRUE)
        FROM gold.variacao_anual
        WHERE codigo_indicador = 'pib_corrente'
          AND valor IS NOT NULL AND valor_anterior IS NOT NULL AND valor_anterior <> 0""")
    assert (sem_variacao, errados, nao_comparaveis) == (0, 0, 0)


def test_variacao_do_pib_preenchida_nos_municipios_antigos(gold):
    # (a) Todo par de anos consecutivos dos 293 municípios antigos tem variação calculada.
    pares, preenchidos = _um(gold, """
        SELECT count(*), count(variacao_absoluta)
        FROM gold.variacao_anual
        WHERE codigo_indicador = 'pib_corrente'
          AND cod_municipio NOT IN ('4212650', '4220000')""")
    assert pares == (N_MUNICIPIOS - len(CODIGOS_NOVOS)) * 13
    assert preenchidos == pares


def test_variacao_do_pib_dos_municipios_novos_e_nula_ate_2013(gold):
    # (b) Regra 5: sem PIB em 2010–2012, não há variação até o par 2012→2013; a primeira é 2013→2014.
    linhas = gold.execute(text("""
        SELECT cod_municipio, ano, valor_anterior, valor, variacao_absoluta, variacao_percentual,
               comparavel
        FROM gold.variacao_anual
        WHERE codigo_indicador = 'pib_corrente' AND cod_municipio IN ('4212650', '4220000')
        ORDER BY cod_municipio, ano""")).all()
    ate_2013 = [l for l in linhas if l.ano <= 2013]
    depois = [l for l in linhas if l.ano > 2013]
    assert len(ate_2013) == 6 and len(depois) == 20
    assert all(l.variacao_absoluta is None and l.variacao_percentual is None for l in ate_2013)
    assert all(l.comparavel is None for l in ate_2013)  # sem número, sem juízo
    assert all(l.variacao_absoluta == l.valor - l.valor_anterior for l in depois)
