"""Testes da trava de credenciais e da limpeza de texto da verificação."""

import pytest

from brasil_em_dados.verificacao.seguranca import (
    CREDENCIAIS_DE_API,
    PROVEDORES_DE_NUVEM,
    SENHA_OMITIDA,
    URL_OMITIDA,
    ErroCredencial,
    credenciais_fora_do_plano,
    exigir_login_do_plano,
    limpar_texto,
    segredos_do_banco,
)

VALOR_SECRETO = "valor-que-nunca-pode-aparecer"


def test_ambiente_limpo_passa():
    exigir_login_do_plano({"PATH": "x", "PG_DATABASE": "y"})


@pytest.mark.parametrize("nome", [*CREDENCIAIS_DE_API, *PROVEDORES_DE_NUVEM])
def test_cada_variavel_que_desvia_do_plano_para_sem_mostrar_o_valor(nome):
    with pytest.raises(ErroCredencial) as erro:
        exigir_login_do_plano({nome: VALOR_SECRETO})
    assert nome in str(erro.value)
    assert VALOR_SECRETO not in str(erro.value)


def test_variavel_vazia_tambem_conta():
    assert credenciais_fora_do_plano({"ANTHROPIC_API_KEY": ""}) == ["ANTHROPIC_API_KEY"]


@pytest.mark.parametrize("url", [
    "postgresql+psycopg://bed_app:***@localhost:5432/brasil_em_dados",
    "postgresql://bed_readonly:abc@127.0.0.1/brasil_em_dados",
    "postgres://u@h/b",
])
def test_url_de_conexao_e_omitida(url):
    texto = limpar_texto(f"Engine do perfil app: {url} pronto")
    assert "://" not in texto
    assert URL_OMITIDA in texto


def test_senhas_do_banco_sao_omitidas():
    ambiente = {"PG_PASSWORD": "senha-app-123", "PG_READONLY_PASSWORD": "senha-leitura-456",
                "PG_USER": "bed_app"}
    segredos = segredos_do_banco(ambiente)
    texto = limpar_texto("erro: senha-app-123 e senha-leitura-456; usuário bed_app", segredos)
    assert "senha-app-123" not in texto and "senha-leitura-456" not in texto
    assert texto.count(SENHA_OMITIDA) == 2
    assert "bed_app" in texto


def test_senha_curta_ou_ausente_nao_vira_segredo():
    assert segredos_do_banco({"PG_PASSWORD": "ab"}) == []
    assert segredos_do_banco({}) == []


def test_filtro_limpa_mensagem_e_traceback_dos_logs(tmp_path):
    import io
    import logging

    from brasil_em_dados.verificacao.seguranca import proteger_logs

    nome = "brasil_em_dados_teste_filtro"
    raiz = logging.getLogger(nome)
    fluxo = io.StringIO()
    handler = logging.StreamHandler(fluxo)
    handler.setFormatter(logging.Formatter("%(name)s %(message)s"))
    raiz.addHandler(handler)
    raiz.setLevel(logging.INFO)
    try:
        proteger_logs(["senha-de-log-123"], nome)
        filho = logging.getLogger(f"{nome}.filho")  # filtro no handler vale para os filhos
        filho.info("conectando em %s", "postgresql+psycopg://bed_app:senha-de-log-123@h/b")
        try:
            raise RuntimeError("falhou com senha-de-log-123 em postgresql://u:x@h/b")
        except RuntimeError:
            filho.exception("erro")
    finally:
        raiz.removeHandler(handler)
    saida = fluxo.getvalue()
    assert "senha-de-log-123" not in saida and "postgresql" not in saida
    assert URL_OMITIDA in saida and "RuntimeError" in saida and "Traceback" in saida
