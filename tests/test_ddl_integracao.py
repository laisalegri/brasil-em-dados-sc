"""Testes de integração do DDL da SILVER/GOLD (D18/D19).

Cada teste aplica o DDL como bed_app numa transação que é SEMPRE desfeita: nada fica no banco,
nem tabelas nem dados. Cada caso inválido roda num savepoint, e o SQLSTATE confirma qual
restrição barrou. Os dados de teste usam códigos fictícios (município 4299990, indicadores
teste_*), que não colidem com os dados reais carregados no D20.
"""

from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import Connection, text

from brasil_em_dados.db.aplicar_ddl import (
    TABELA_REGISTRO,
    ErroDDL,
    Script,
    aplicar_em_conexao,
    executar_scripts,
    ler_scripts,
)
from tests.apoio_banco import (
    SQLSTATE_SEM_PRIVILEGIO,
    sqlstate_em_savepoint,
    sqlstate_em_transacao_desfeita,
)

pytestmark = pytest.mark.integracao

CHECK = "23514"        # check_violation
FK = "23503"           # foreign_key_violation
UNICA = "23505"        # unique_violation
NAO_NULO = "23502"     # not_null_violation
ESTOURO = "22003"      # numeric_value_out_of_range

TABELAS_SILVER = ["dim_municipio", "dim_indicador", "dim_serie",
                  "fato_indicador_municipio", "controle_execucao"]
AGORA = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)

MUNICIPIO = {
    "cod_municipio": "4299990", "nome_municipio": "Município de Teste",
    "cod_regiao_imediata": "429999", "nome_regiao_imediata": "Imediata de Teste",
    "cod_regiao_intermediaria": "4299", "nome_regiao_intermediaria": "Intermediária de Teste",
    "cod_microrregiao": "42999", "nome_microrregiao": "Micro de Teste",
    "cod_mesorregiao": "4299", "nome_mesorregiao": "Meso de Teste",
    "cod_uf": "42", "sigla_uf": "SC",
}
INDICADORES = [
    {"codigo_indicador": "teste_pop", "nome": "Pop teste", "unidade_armazenada": "Pessoas",
     "tipo_medida": "estimativa", "descricao": "Indicador de teste"},
    {"codigo_indicador": "teste_pib", "nome": "PIB teste", "unidade_armazenada": "R$",
     "tipo_medida": "nominal", "descricao": "Indicador de teste"},
]
SERIES = [
    {"cod_serie": "teste_serie_pop", "codigo_indicador": "teste_pop", "fonte": "sidra",
     "tabela_ou_pesquisa": "6579", "variavel_ou_indicador": "9324", "unidade_origem": "Pessoas",
     "fator_conversao": 1, "data_referencia": "1º de julho",
     "url_extrator": "https://apisidra.ibge.gov.br/values/t/6579"},
    {"cod_serie": "teste_serie_pib", "codigo_indicador": "teste_pib", "fonte": "sidra",
     "tabela_ou_pesquisa": "5938", "variavel_ou_indicador": "37", "unidade_origem": "Mil Reais",
     "fator_conversao": 1000, "data_referencia": "ano civil",
     "url_extrator": "https://apisidra.ibge.gov.br/values/t/5938"},
]
FATO = {"cod_municipio": "4299990", "codigo_indicador": "teste_pop", "ano": 2015,
        "cod_serie": "teste_serie_pop", "valor": 100, "sinal_origem": None, "data_coleta": AGORA}
CONTROLE = {"cod_serie": "teste_serie_pop", "inicio": AGORA, "fim": AGORA, "status": "sucesso",
            "n_registros": 3245, "arquivo": "teste_serie_pop/x.json", "erro": None}


def _inserir(conexao: Connection, tabela: str, linha: dict) -> None:
    colunas = ", ".join(linha)
    marcadores = ", ".join(f":{c}" for c in linha)
    conexao.execute(text(f"INSERT INTO silver.{tabela} ({colunas}) VALUES ({marcadores})"), linha)


def _aplicar(conexao: Connection) -> None:
    cursor = conexao.connection.cursor()
    try:
        executar_scripts(cursor.execute, ler_scripts())
    finally:
        cursor.close()


@pytest.fixture
def silver(engine_app) -> Iterator[Connection]:
    """Conexão bed_app com o DDL aplicado e dimensões de teste, numa transação desfeita."""
    with engine_app.connect() as conexao:
        transacao = conexao.begin()
        try:
            _aplicar(conexao)
            _inserir(conexao, "dim_municipio", MUNICIPIO)
            for indicador in INDICADORES:
                _inserir(conexao, "dim_indicador", indicador)
            for serie in SERIES:
                _inserir(conexao, "dim_serie", serie)
            yield conexao
        finally:
            transacao.rollback()


# --- idempotência -----------------------------------------------------------------------------

def test_ddl_roda_duas_vezes_sem_erro_e_cria_as_tabelas(engine_app):
    with engine_app.connect() as conexao:
        transacao = conexao.begin()
        try:
            _aplicar(conexao)
            _aplicar(conexao)
            tabelas = conexao.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'silver'"
            )).scalars().all()
            schemas = conexao.execute(text(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name IN ('silver', 'gold')")).scalars().all()
        finally:
            transacao.rollback()
    # Subconjunto: tabelas criadas depois (estágio do D21) não quebram este teste.
    assert set(TABELAS_SILVER) <= set(tabelas)
    assert sorted(schemas) == ["gold", "silver"]


# --- registro em public.ddl_aplicado ------------------------------------------------------------

SCRIPT_TESTE = Script(Path("90_teste_registro.sql"),
                      "CREATE TABLE IF NOT EXISTS silver.teste_registro (x integer);")


def test_registro_aplica_uma_vez_e_recusa_arquivo_editado(engine_app):
    scripts = [*ler_scripts(), SCRIPT_TESTE]
    with engine_app.connect() as conexao:
        transacao = conexao.begin()
        try:
            primeira = aplicar_em_conexao(conexao, scripts)
            segunda = aplicar_em_conexao(conexao, scripts)
            sha = conexao.execute(text(
                f"SELECT sha256 FROM {TABELA_REGISTRO} WHERE arquivo = :a"),
                {"a": SCRIPT_TESTE.nome}).scalar_one()
            editado = Script(SCRIPT_TESTE.arquivo, SCRIPT_TESTE.sql + "\n-- edição")
            with pytest.raises(ErroDDL, match="editado depois") as erro:
                aplicar_em_conexao(conexao, [*ler_scripts(), editado])
        finally:
            transacao.rollback()
    assert SCRIPT_TESTE.nome in primeira
    assert segunda == []
    assert sha == SCRIPT_TESTE.sha256
    assert "crie um arquivo novo numerado" in str(erro.value)


# --- casos válidos ----------------------------------------------------------------------------

def test_linha_valida_da_fato_e_aceita(silver):
    assert sqlstate_em_savepoint(silver, lambda: _inserir(silver, "fato_indicador_municipio", FATO)) is None


@pytest.mark.parametrize("valor, sinal", [
    (None, "..."),  # ausência (regra 5) com o sinal que a explica
    (0, "-"),       # "-" do SIDRA: zero absoluto, carrega como 0 (regra 9)
    (None, "-"),    # "-" da API de Pesquisas: ausência, carrega como NULL
    (None, "X"),    # valor inibido
    (None, "B"),    # letra de faixa
    (0, None),      # "0" do SIDRA: numérico, sem sinal
], ids=["ausente-...", "traco-sidra-zero", "traco-pesquisas-nulo", "inibido-X", "faixa-B", "zero"])
def test_combinacoes_validas_de_valor_e_sinal_sao_aceitas(silver, valor, sinal):
    linha = {**FATO, "valor": valor, "sinal_origem": sinal}
    assert sqlstate_em_savepoint(silver, lambda: _inserir(silver, "fato_indicador_municipio", linha)) is None


@pytest.mark.parametrize("linha", [
    CONTROLE,
    {**CONTROLE, "status": "falha", "n_registros": None, "arquivo": None, "erro": "ErroHTTP: 503"},
], ids=["sucesso", "falha"])
def test_execucao_valida_e_aceita(silver, linha):
    assert sqlstate_em_savepoint(silver, lambda: _inserir(silver, "controle_execucao", linha)) is None


# --- restrições: cada caso inválido é barrado pela restrição certa -----------------------------

CASOS_INVALIDOS = [
    # fato
    pytest.param("fato_indicador_municipio", {**FATO, "cod_municipio": "4300000"}, CHECK,
                 id="fato-codigo-fora-de-sc"),
    pytest.param("fato_indicador_municipio", {**FATO, "cod_municipio": "420540"}, CHECK,
                 id="fato-codigo-com-6-digitos"),
    pytest.param("fato_indicador_municipio", {**FATO, "ano": 2009}, CHECK, id="fato-ano-2009"),
    pytest.param("fato_indicador_municipio", {**FATO, "ano": 2024}, CHECK, id="fato-ano-2024"),
    pytest.param("fato_indicador_municipio", {**FATO, "valor": None, "sinal_origem": None}, CHECK,
                 id="fato-valor-e-sinal-nulos"),
    pytest.param("fato_indicador_municipio", {**FATO, "valor": None, "sinal_origem": ""}, CHECK,
                 id="fato-sinal-vazio"),
    pytest.param("fato_indicador_municipio", {**FATO, "valor": None, "sinal_origem": "abc"},
                 CHECK, id="fato-sinal-fora-do-dominio"),
    pytest.param("fato_indicador_municipio", {**FATO, "valor": None, "sinal_origem": "x"},
                 CHECK, id="fato-sinal-letra-minuscula"),
    pytest.param("fato_indicador_municipio", {**FATO, "valor": 100, "sinal_origem": "..."},
                 CHECK, id="fato-valor-numerico-com-sinal"),
    pytest.param("fato_indicador_municipio", {**FATO, "valor": 5, "sinal_origem": "-"},
                 CHECK, id="fato-traco-com-valor-diferente-de-zero"),
    pytest.param("fato_indicador_municipio", {**FATO, "valor": 10 ** 16}, ESTOURO,
                 id="fato-valor-maior-que-numeric-18-2"),
    pytest.param("fato_indicador_municipio", {**FATO, "cod_serie": "teste_serie_pib"}, FK,
                 id="fato-serie-de-outro-indicador"),
    pytest.param("fato_indicador_municipio", {**FATO, "cod_municipio": "4299991"}, FK,
                 id="fato-municipio-fora-da-dimensao"),
    pytest.param("fato_indicador_municipio",
                 {**FATO, "codigo_indicador": "teste_nao_existe"}, FK,
                 id="fato-indicador-inexistente"),
    pytest.param("fato_indicador_municipio", {**FATO, "cod_serie": "teste_serie_nao_existe"}, FK,
                 id="fato-serie-inexistente"),
    pytest.param("fato_indicador_municipio", {**FATO, "data_coleta": None}, NAO_NULO,
                 id="fato-sem-data-de-coleta"),
    # dim_municipio
    pytest.param("dim_municipio", {**MUNICIPIO, "cod_municipio": "4300000"}, CHECK,
                 id="municipio-codigo-fora-de-sc"),
    pytest.param("dim_municipio", {**MUNICIPIO, "cod_municipio": "4299991",
                                   "cod_mesorregiao": "429"}, CHECK,
                 id="municipio-mesorregiao-com-3-digitos"),
    pytest.param("dim_municipio", {**MUNICIPIO, "cod_municipio": "4299991", "cod_uf": "43"},
                 CHECK, id="municipio-uf-diferente-de-42"),
    pytest.param("dim_municipio", {**MUNICIPIO, "cod_municipio": "4299991",
                                   "cod_regiao_imediata": "42999"}, CHECK,
                 id="municipio-imediata-com-5-digitos"),
    pytest.param("dim_municipio", {**MUNICIPIO, "cod_municipio": "4299991",
                                   "cod_regiao_intermediaria": "4399"}, CHECK,
                 id="municipio-intermediaria-fora-de-sc"),
    pytest.param("dim_municipio", {**MUNICIPIO, "cod_municipio": "4299991",
                                   "cod_microrregiao": "4299"}, CHECK,
                 id="municipio-micro-com-4-digitos"),
    pytest.param("dim_municipio", {**MUNICIPIO, "cod_municipio": "4299991", "sigla_uf": "RS"},
                 CHECK, id="municipio-sigla-diferente-de-sc"),
    pytest.param("dim_municipio", {**MUNICIPIO, "cod_municipio": "4299991",
                                   "nome_municipio": ""}, CHECK, id="municipio-nome-vazio"),
    # dim_indicador
    pytest.param("dim_indicador", {**INDICADORES[0], "codigo_indicador": "teste_x",
                                   "tipo_medida": "real"}, CHECK, id="indicador-tipo-medida-invalido"),
    pytest.param("dim_indicador", {**INDICADORES[0], "codigo_indicador": "teste_x",
                                   "tipo_medida": None}, NAO_NULO, id="indicador-tipo-medida-nulo"),
    pytest.param("dim_indicador", {**INDICADORES[0], "codigo_indicador": "Teste-X"}, CHECK,
                 id="indicador-codigo-fora-do-padrao"),
    pytest.param("dim_indicador", {**INDICADORES[0], "codigo_indicador": "teste_x", "nome": ""},
                 CHECK, id="indicador-nome-vazio"),
    # dim_serie
    pytest.param("dim_serie", {**SERIES[0], "cod_serie": "teste_x", "fator_conversao": 0}, CHECK,
                 id="serie-fator-zero"),
    pytest.param("dim_serie", {**SERIES[0], "cod_serie": "teste_x", "fator_conversao": -1000},
                 CHECK, id="serie-fator-negativo"),
    pytest.param("dim_serie", {**SERIES[0], "cod_serie": "teste_x", "fonte": "outra"}, CHECK,
                 id="serie-fonte-desconhecida"),
    pytest.param("dim_serie", {**SERIES[0], "cod_serie": "teste_x",
                               "codigo_indicador": "teste_nao_existe"}, FK,
                 id="serie-indicador-inexistente"),
    pytest.param("dim_serie", {**SERIES[0], "cod_serie": "teste_x",
                               "url_extrator": "http://apisidra.ibge.gov.br/x"}, CHECK,
                 id="serie-url-sem-https"),
    # controle_execucao
    pytest.param("controle_execucao", {**CONTROLE, "status": "ok"}, CHECK, id="controle-status"),
    pytest.param("controle_execucao", {**CONTROLE, "arquivo": None}, CHECK,
                 id="controle-sucesso-sem-arquivo"),
    pytest.param("controle_execucao", {**CONTROLE, "status": "falha", "arquivo": None,
                                       "n_registros": None, "erro": None}, CHECK,
                 id="controle-falha-sem-erro"),
    pytest.param("controle_execucao", {**CONTROLE, "fim": datetime(2026, 1, 1, tzinfo=timezone.utc)},
                 CHECK, id="controle-fim-antes-do-inicio"),
    pytest.param("controle_execucao", {**CONTROLE, "n_registros": -1}, CHECK,
                 id="controle-contagem-negativa"),
    pytest.param("controle_execucao", {**CONTROLE, "erro": "ErroHTTP: 503"}, CHECK,
                 id="controle-sucesso-com-erro"),
    pytest.param("controle_execucao", {**CONTROLE, "status": "falha", "n_registros": None,
                                       "erro": "ErroHTTP: 503"}, CHECK,
                 id="controle-falha-com-arquivo"),
]


@pytest.mark.parametrize("tabela, linha, sqlstate", CASOS_INVALIDOS)
def test_restricao_rejeita_caso_invalido(silver, tabela, linha, sqlstate):
    assert sqlstate_em_savepoint(silver, lambda: _inserir(silver, tabela, linha)) == sqlstate


@pytest.mark.parametrize("tabela, linha", [
    ("fato_indicador_municipio", FATO),
    ("controle_execucao", CONTROLE),
    ("dim_municipio", MUNICIPIO),
], ids=["fato-chave-municipio-indicador-ano", "controle-serie-inicio", "municipio-codigo"])
def test_duplicata_da_chave_e_rejeitada(silver, tabela, linha):
    if tabela != "dim_municipio":  # o município já foi inserido pela fixture
        _inserir(silver, tabela, linha)
    assert sqlstate_em_savepoint(silver, lambda: _inserir(silver, tabela, linha)) == UNICA


def test_fato_herda_tipo_medida_pelo_indicador(silver):
    _inserir(silver, "fato_indicador_municipio", FATO)
    tipo = silver.execute(text(
        "SELECT i.tipo_medida FROM silver.fato_indicador_municipio f "
        "JOIN silver.dim_indicador i USING (codigo_indicador) WHERE f.cod_municipio = '4299990'"
    )).scalar_one()
    assert tipo == "estimativa"


# --- bed_readonly: lê mas não escreve em silver e gold ------------------------------------------

def _privilegio(conexao: Connection, funcao: str, objeto: str, privilegio: str) -> bool:
    return conexao.execute(text(f"SELECT {funcao}('bed_readonly', :obj, :priv)"),
                           {"obj": objeto, "priv": privilegio}).scalar_one()


@pytest.mark.parametrize("schema", ["silver", "gold"])
def test_readonly_usa_o_schema_mas_nao_cria_nele(silver, schema):
    assert _privilegio(silver, "has_schema_privilege", schema, "USAGE") is True
    assert _privilegio(silver, "has_schema_privilege", schema, "CREATE") is False


@pytest.mark.parametrize("tabela", TABELAS_SILVER)
def test_readonly_le_mas_nao_escreve_nas_tabelas_da_silver(silver, tabela):
    objeto = f"silver.{tabela}"
    assert _privilegio(silver, "has_table_privilege", objeto, "SELECT") is True
    for privilegio in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
        assert _privilegio(silver, "has_table_privilege", objeto, privilegio) is False, privilegio


def test_tabela_nova_na_gold_ja_nasce_legivel_pelo_readonly(silver):
    # Privilégios padrão do 01_schemas.sql: vale para o que o bed_app criar depois.
    silver.execute(text("CREATE TABLE gold.teste_privilegio_padrao (x integer)"))
    objeto = "gold.teste_privilegio_padrao"
    assert _privilegio(silver, "has_table_privilege", objeto, "SELECT") is True
    assert _privilegio(silver, "has_table_privilege", objeto, "INSERT") is False


def _schema_aplicado(engine_readonly) -> bool:
    with engine_readonly.connect() as conexao:
        return conexao.execute(text("SELECT to_regclass('silver.dim_municipio')")).scalar() is not None


def _como_leitura_e_escrita(comando):
    """O bed_readonly pode desligar default_transaction_read_only; a ACL tem de barrar mesmo assim."""
    def executar(conexao):
        conexao.execute(text("SET TRANSACTION READ WRITE"))
        comando(conexao)
    return executar


def _exigir_schema_aplicado(engine_readonly) -> None:
    if not _schema_aplicado(engine_readonly):
        pytest.skip("DDL ainda não aplicado; rode python -m brasil_em_dados.db.aplicar_ddl")


@pytest.mark.parametrize("tabela", TABELAS_SILVER)
def test_readonly_le_as_tabelas_da_silver_aplicada(engine_readonly, tabela):
    """Comportamento real como bed_readonly; precisa do DDL já aplicado (aplicar_ddl)."""
    _exigir_schema_aplicado(engine_readonly)
    with engine_readonly.connect() as conexao:
        conexao.execute(text(f"SELECT count(*) FROM silver.{tabela}")).scalar_one()


def test_acl_barra_insert_do_readonly_mesmo_em_transacao_de_escrita(engine_readonly):
    _exigir_schema_aplicado(engine_readonly)
    sqlstate = sqlstate_em_transacao_desfeita(engine_readonly, _como_leitura_e_escrita(
        lambda conexao: _inserir(conexao, "dim_indicador", INDICADORES[0])))
    assert sqlstate == SQLSTATE_SEM_PRIVILEGIO


def test_acl_barra_create_do_readonly_na_gold_mesmo_em_transacao_de_escrita(engine_readonly):
    _exigir_schema_aplicado(engine_readonly)
    sqlstate = sqlstate_em_transacao_desfeita(engine_readonly, _como_leitura_e_escrita(
        lambda conexao: conexao.execute(text("CREATE TABLE gold.teste_readonly (x integer)"))))
    assert sqlstate == SQLSTATE_SEM_PRIVILEGIO
