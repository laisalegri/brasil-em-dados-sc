"""Testes unitários da montagem das conexões (sem banco, com variáveis simuladas)."""

import logging
import os
from unittest.mock import patch

import pytest
from sqlalchemy.engine import make_url

from brasil_em_dados import db

SENHA_APP = "s3nh@-app/secreta"
SENHA_RO = "s3nh@-ro:secreta"
AMBIENTE = {
    "PG_HOST": "localhost",
    "PG_PORT": "5432",
    "PG_DATABASE": "brasil_em_dados",
    "PG_USER": "bed_app",
    "PG_PASSWORD": SENHA_APP,
    "PG_READONLY_USER": "bed_readonly",
    "PG_READONLY_PASSWORD": SENHA_RO,
}


def test_url_do_perfil_app_usa_usuario_de_escrita():
    url = db.montar_url(db.PERFIL_APP, AMBIENTE)
    assert url.drivername == "postgresql+psycopg"
    assert (url.username, url.host, url.port, url.database) == (
        "bed_app", "localhost", 5432, "brasil_em_dados")
    assert url.password == SENHA_APP


def test_url_do_perfil_readonly_usa_usuario_somente_leitura():
    url = db.montar_url(db.PERFIL_READONLY, AMBIENTE)
    assert url.username == "bed_readonly"
    assert url.password == SENHA_RO


@pytest.mark.parametrize("perfil, senha", [(db.PERFIL_APP, SENHA_APP),
                                            (db.PERFIL_READONLY, SENHA_RO)])
def test_senha_com_caracteres_especiais_sobrevive_a_ida_e_volta_da_url(perfil, senha):
    # "@", "/" e ":" quebrariam uma URL montada na mão; URL.create codifica corretamente.
    url = db.montar_url(perfil, AMBIENTE)
    reconstruida = make_url(url.render_as_string(hide_password=False))
    assert reconstruida.password == senha
    assert (reconstruida.host, reconstruida.database) == ("localhost", "brasil_em_dados")


@pytest.mark.parametrize("perfil, senha", [(db.PERFIL_APP, SENHA_APP),
                                            (db.PERFIL_READONLY, SENHA_RO)])
def test_texto_e_repr_da_url_nao_mostram_a_senha(perfil, senha):
    url = db.montar_url(perfil, AMBIENTE)
    for texto in (str(url), repr(url), db.descrever_url(url)):
        assert senha not in texto
        assert "***" in texto


@pytest.mark.parametrize("variavel", ["PG_HOST", "PG_PORT", "PG_DATABASE",
                                      "PG_USER", "PG_PASSWORD"])
def test_variavel_ausente_falha_citando_so_o_nome(variavel):
    ambiente = {k: v for k, v in AMBIENTE.items() if k != variavel}
    with pytest.raises(db.ErroConfiguracao, match=variavel) as erro:
        db.montar_url(db.PERFIL_APP, ambiente)
    assert SENHA_APP not in str(erro.value)


def test_variavel_vazia_conta_como_ausente():
    ambiente = {**AMBIENTE, "PG_READONLY_PASSWORD": ""}
    with pytest.raises(db.ErroConfiguracao, match="PG_READONLY_PASSWORD"):
        db.montar_url(db.PERFIL_READONLY, ambiente)


def test_perfil_app_nao_exige_variaveis_do_readonly():
    ambiente = {k: v for k, v in AMBIENTE.items() if not k.startswith("PG_READONLY")}
    assert db.montar_url(db.PERFIL_APP, ambiente).username == "bed_app"


@pytest.mark.parametrize("porta", ["cinco", "²", "0", "65536", "-1", "54 32", "5432.0"])
def test_porta_invalida_falha_sem_mostrar_o_valor(porta):
    with pytest.raises(db.ErroConfiguracao, match="PG_PORT") as erro:
        db.montar_url(db.PERFIL_APP, {**AMBIENTE, "PG_PORT": porta})
    assert porta not in str(erro.value)
    assert SENHA_APP not in str(erro.value)


@pytest.mark.parametrize("porta, esperada", [("1", 1), ("5433", 5433), ("65535", 65535)])
def test_porta_valida_nos_limites(porta, esperada):
    assert db.montar_url(db.PERFIL_APP, {**AMBIENTE, "PG_PORT": porta}).port == esperada


def test_engine_e_criado_sem_conectar_e_log_nao_mostra_senha(caplog):
    with caplog.at_level(logging.INFO, logger="brasil_em_dados.db"):
        engine_app = db.engine_app(AMBIENTE)
        engine_ro = db.engine_readonly(AMBIENTE)
    assert engine_app.url.username == "bed_app"
    assert engine_ro.url.username == "bed_readonly"
    assert "bed_app" in caplog.text and "bed_readonly" in caplog.text
    assert SENHA_APP not in caplog.text and SENHA_RO not in caplog.text
    engine_app.dispose()
    engine_ro.dispose()


def test_engine_esconde_parametros_e_tem_tempo_limite_de_conexao():
    with patch("brasil_em_dados.db.create_engine") as criar:
        db.engine_app(AMBIENTE)
    opcoes = criar.call_args.kwargs
    assert opcoes["hide_parameters"] is True
    assert opcoes["connect_args"] == {"connect_timeout": db.TIMEOUT_CONEXAO_S}


# --- leitura do .env -------------------------------------------------------------------------

def _limpar_variaveis_do_banco(monkeypatch):
    for nome in AMBIENTE:
        monkeypatch.delenv(nome, raising=False)


def _escrever_env(pasta, valores: dict[str, str]):
    arquivo = pasta / ".env"
    arquivo.write_text("".join(f"{k}={v}\n" for k, v in valores.items()), encoding="utf-8")
    return arquivo


def test_ler_ambiente_da_precedencia_ao_processo_e_nao_altera_os_environ(tmp_path, monkeypatch):
    _limpar_variaveis_do_banco(monkeypatch)
    monkeypatch.setenv("PG_HOST", "do-processo")
    arquivo = _escrever_env(tmp_path, {"PG_HOST": "do-arquivo", "PG_DATABASE": "do-arquivo"})

    ambiente = db.ler_ambiente(arquivo)

    assert ambiente["PG_HOST"] == "do-processo"
    assert ambiente["PG_DATABASE"] == "do-arquivo"
    assert "PG_DATABASE" not in os.environ


def test_ler_ambiente_sem_arquivo_usa_so_o_processo(tmp_path, monkeypatch):
    _limpar_variaveis_do_banco(monkeypatch)
    monkeypatch.setenv("PG_HOST", "do-processo")
    ambiente = db.ler_ambiente(tmp_path / "nao_existe.env")
    assert ambiente["PG_HOST"] == "do-processo"
    assert "PG_DATABASE" not in ambiente


def test_engine_sem_argumento_le_o_env_padrao(tmp_path, monkeypatch, caplog):
    # Caminho usado pelo pipeline e pelos agentes: engine_app() / engine_readonly().
    _limpar_variaveis_do_banco(monkeypatch)
    monkeypatch.setattr(db, "ARQUIVO_ENV", _escrever_env(tmp_path, AMBIENTE))

    with caplog.at_level(logging.INFO, logger="brasil_em_dados.db"):
        engine_app = db.engine_app()
        engine_ro = db.engine_readonly()

    assert (engine_app.url.username, engine_app.url.host) == ("bed_app", "localhost")
    assert engine_app.url.password == SENHA_APP
    assert engine_ro.url.username == "bed_readonly"
    assert SENHA_APP not in caplog.text and SENHA_RO not in caplog.text
    assert "PG_PASSWORD" not in os.environ
    engine_app.dispose()
    engine_ro.dispose()


def test_engine_sem_argumento_e_sem_env_falha_citando_as_variaveis(tmp_path, monkeypatch):
    _limpar_variaveis_do_banco(monkeypatch)
    monkeypatch.setattr(db, "ARQUIVO_ENV", tmp_path / "nao_existe.env")
    with pytest.raises(db.ErroConfiguracao, match="PG_HOST"):
        db.engine_readonly()
