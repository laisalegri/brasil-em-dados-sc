"""Integração das ferramentas do agente com o PostgreSQL local, como bed_readonly."""

import pytest
from sqlalchemy import text

from brasil_em_dados import db
from brasil_em_dados.config import PASTA_CONSULTAS_VERIFICACAO
from brasil_em_dados.verificacao.ferramentas import (
    Contexto,
    ler_catalogo,
    transacao_somente_leitura,
)
from brasil_em_dados.verificacao.seguranca import segredos_do_banco
from tests.apoio_banco import BLOQUEIOS_READONLY, sqlstate_em_savepoint

pytestmark = pytest.mark.integracao


@pytest.fixture(scope="module")
def ambiente() -> dict[str, str]:
    return db.ler_ambiente()  # só em memória; nunca impresso


@pytest.fixture()
def contexto(engine_readonly, ambiente, tmp_path) -> Contexto:
    return Contexto("20261120T120000", [], ler_catalogo(PASTA_CONSULTAS_VERIFICACAO), tmp_path,
                    engine_readonly, segredos_do_banco(ambiente))


def test_transacao_e_somente_leitura_e_como_bed_readonly(engine_readonly, ambiente):
    with transacao_somente_leitura(engine_readonly) as conexao:
        assert conexao.execute(text("SELECT current_user")).scalar() == ambiente["PG_READONLY_USER"]
        assert conexao.execute(text("SHOW transaction_read_only")).scalar() == "on"
        estado = sqlstate_em_savepoint(conexao, lambda: conexao.execute(
            text("CREATE TEMP TABLE verificacao_nao_pode (a int)")))
    assert estado in BLOQUEIOS_READONLY


def _sem_segredos(texto: str, ambiente: dict[str, str]) -> None:
    assert "postgres" not in texto.lower().replace("postgresql_", "")
    for nome in ("PG_PASSWORD", "PG_READONLY_PASSWORD"):
        valor = ambiente.get(nome)
        if valor:
            assert valor not in texto, f"valor de {nome} apareceu no texto"


@pytest.mark.parametrize("nome", sorted(ler_catalogo(PASTA_CONSULTAS_VERIFICACAO)))
def test_cada_consulta_do_catalogo_roda_e_volta_limpa(contexto, ambiente, nome):
    texto = contexto.consulta_qualidade(nome)
    assert texto.strip()
    _sem_segredos(texto, ambiente)


def test_controle_execucao_le_o_banco_e_volta_limpo(contexto, ambiente):
    texto = contexto.controle_execucao()
    assert "Última execução por série" in texto and "ibge_localidades_sc" in texto
    _sem_segredos(texto, ambiente)


def test_consultas_que_devem_vir_vazias(contexto):
    for nome in ("nulos_fora_da_regra", "series_por_indicador_ano", "valores_negativos"):
        assert "(nenhuma linha)" in contexto.consulta_qualidade(nome), nome
