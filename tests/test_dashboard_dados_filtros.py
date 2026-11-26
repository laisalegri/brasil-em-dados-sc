"""Leitura dos dados do app (erro de conexão sem detalhes, tipos) e filtros globais."""

import logging

import pandas as pd
import pytest
from sqlalchemy.exc import OperationalError

from brasil_em_dados import db
from brasil_em_dados.dashboard import dados, filtros

SEGREDO = "postgresql+psycopg://usuario_x:senha_x@host_x:5432/banco_x"


@pytest.fixture
def sem_engine(monkeypatch):
    monkeypatch.setattr(dados, "_engine", lambda: "engine")


@pytest.mark.parametrize("erro", [
    OperationalError(SEGREDO, None, Exception(SEGREDO)),
    db.ErroConfiguracao("Variáveis de ambiente ausentes para o perfil readonly: PG_HOST"),
    ConnectionRefusedError(SEGREDO),
])
def test_erro_de_conexao_vira_erro_dados_sem_detalhes(sem_engine, caplog, erro):
    def falhar(engine):
        raise erro

    with caplog.at_level(logging.WARNING), pytest.raises(dados.ErroDados) as capturado:
        dados.ler(falhar)
    assert str(capturado.value) == dados.MENSAGEM_ERRO
    assert capturado.value.__cause__ is None and capturado.value.__suppress_context__
    assert "senha_x" not in caplog.text and "usuario_x" not in caplog.text


def test_erro_que_nao_e_de_conexao_nao_e_escondido(sem_engine):
    def falhar(engine):
        raise KeyError("coluna")

    with pytest.raises(KeyError):
        dados.ler(falhar)


def test_ler_passa_o_engine_e_normaliza_os_tipos(sem_engine):
    def consulta(engine, ano):
        assert engine == "engine" and ano == 2023
        return pd.DataFrame({"cod_municipio": ["1", "2"], "pop_estimada": [None, None],
                             "valor": [1, None]})

    df = dados.ler(consulta, 2023)
    assert df["pop_estimada"].dtype == "float64" and df["pop_estimada"].isna().all()
    assert df["valor"].tolist()[0] == 1.0 and pd.isna(df["valor"].tolist()[1])  # NULL continua NULL
    assert df["cod_municipio"].tolist() == ["1", "2"]  # código continua texto (regra 1)


MUNICIPIOS = pd.DataFrame({
    "cod_municipio": ["4205407", "4209102", "4200101"],
    "nome_municipio": ["Florianópolis", "Joinville", "Abelardo Luz"],
    "cod_regiao_intermediaria": ["4201", "4202", "4205"],
})


def test_opcoes_de_municipio_seguem_a_regiao_em_ordem_alfabetica():
    assert filtros.opcoes_municipios(MUNICIPIOS, None) == ["4200101", "4205407", "4209102"]
    assert filtros.opcoes_municipios(MUNICIPIOS, "4202") == ["4209102"]


def test_municipio_padrao_e_florianopolis_quando_esta_na_lista():
    assert filtros.indice_padrao(["4200101", "4205407"]) == 1
    assert filtros.indice_padrao(["4209102"]) == 0


def test_anos_do_filtro():
    assert filtros.ANOS == tuple(range(2010, 2024)) and filtros.ANO_PADRAO == 2023


class _ErroDoDriver(Exception):
    """Imita o erro do psycopg: mensagem com detalhes da conexão e o atributo sqlstate."""

    def __init__(self, sqlstate: object) -> None:
        super().__init__(SEGREDO)
        self.sqlstate = sqlstate


@pytest.mark.parametrize(("codigo", "no_log"), [
    ("28P01", "SQLSTATE 28P01"),          # senha recusada
    ("3D000", "SQLSTATE 3D000"),          # banco inexistente
    (None, "SQLSTATE sem código"),        # falha de rede: o driver não dá código
    (SEGREDO, "SQLSTATE sem código"),     # valor fora do formato nunca vai para o log
])
def test_log_traz_o_sqlstate_e_nenhum_detalhe_da_conexao(sem_engine, caplog, codigo, no_log):
    def falhar(engine):
        raise OperationalError("SELECT 1", None, _ErroDoDriver(codigo))

    with caplog.at_level(logging.WARNING), pytest.raises(dados.ErroDados):
        dados.ler(falhar)
    assert no_log in caplog.text and "OperationalError" in caplog.text
    for detalhe in ("usuario_x", "senha_x", "host_x", "banco_x"):
        assert detalhe not in caplog.text
