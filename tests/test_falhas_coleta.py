"""Falhas da coleta ponta a ponta via coletar() (padrão de coleta, seções 4 a 9).

Sem rede: `baixar_fn` devolve respostas sintéticas por URL. Tudo é gravado em tmp_path.
As respostas seguem o formato real das APIs (cabeçalho SIDRA de tests/fixtures/) com os códigos
sintéticos usados nos demais testes: f"42{i:04d}0" + 4212650 e 4220000.
"""

import errno
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from functools import partial
from itertools import count
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from brasil_em_dados.extract import __main__ as cli
from brasil_em_dados.extract import catalogo, raw
from brasil_em_dados.extract.cliente_http import RespostaHTTP, baixar
from brasil_em_dados.extract.coleta import coletar
from brasil_em_dados.extract.controle import ler_execucoes
from brasil_em_dados.extract.erros import ErroGravacao, ErroHTTP, ErroValidacao

LOCALIDADES = "ibge_localidades_sc"
PESQUISAS = "pesquisas_38_i47001"
SERIES_SIDRA = ["sidra_6579_v9324", "sidra_1378_v93", "sidra_4709_v93", "sidra_5938_v37"]

NOVOS = ["4212650", "4220000"]  # Pescaria Brava e Balneário Rincão, instalados em 2013
ANTIGOS = [f"42{i:04d}0" for i in range(1, 294)]
TODOS = ANTIGOS + NOVOS
DESCONHECIDO = "4299990"  # no padrão 42xxxxx, mas fora do cadastro

CABECALHO_SIDRA = {
    "NC": "Nível Territorial (Código)", "NN": "Nível Territorial",
    "MC": "Unidade de Medida (Código)", "MN": "Unidade de Medida",
    "V": "Valor", "D1C": "Município (Código)", "D1N": "Município",
    "D2C": "Variável (Código)", "D2N": "Variável", "D3C": "Ano (Código)", "D3N": "Ano",
}

# variável, anos, municípios presentes e (município, ano) que vêm com sinal "..."
ESPEC_SIDRA = {
    "sidra_6579_v9324": ("9324", range(2011, 2022), TODOS, {(c, 2011) for c in NOVOS}),
    "sidra_1378_v93": ("93", [2010], ANTIGOS, set()),
    "sidra_4709_v93": ("93", [2022], TODOS, set()),
    "sidra_5938_v37": ("37", range(2010, 2024), TODOS,
                       {(c, a) for c in NOVOS for a in range(2010, 2013)}),
}


# --- respostas sintéticas -------------------------------------------------------------------

# Todos os anos do recorte (2010–2023), exigidos pela validação da API de Pesquisas.
ANOS_VALIDOS = {str(a): "1.00" for a in range(2010, 2024)}

def corpo_localidades(ids=TODOS, sufixo_nome: str = "") -> bytes:
    return json.dumps([{"id": int(i), "nome": f"Município {i}{sufixo_nome}"} for i in ids]
                      ).encode()


def dados_sidra(cod_serie: str, valores: dict | None = None,
                trocar: tuple[str, str] | None = None) -> list:
    """Resposta SIDRA válida da série; `valores` sobrescreve (município, ano) → valor."""
    variavel, anos, municipios, sinais = ESPEC_SIDRA[cod_serie]
    valores = valores or {}
    linhas = [dict(CABECALHO_SIDRA)]
    for ano in anos:
        for municipio in municipios:
            valor = valores.get((municipio, ano), "..." if (municipio, ano) in sinais else "100")
            codigo = trocar[1] if trocar and municipio == trocar[0] else municipio
            linhas.append({"NC": "6", "NN": "Município", "MC": "45", "MN": "Pessoas",
                           "V": valor, "D1C": codigo, "D1N": f"Município {codigo} (SC)",
                           "D2C": variavel, "D2N": "Variável", "D3C": str(ano), "D3N": str(ano)})
    return linhas


def corpo_sidra(cod_serie: str, **kwargs) -> bytes:
    return json.dumps(dados_sidra(cod_serie, **kwargs)).encode()


def corpo_pesquisas(codigos6=None) -> bytes:
    codigos6 = codigos6 if codigos6 is not None else [c[:6] for c in TODOS]
    res = [{"localidade": c, "res": ANOS_VALIDOS} for c in codigos6]
    return json.dumps([{"id": 47001, "res": res}]).encode()


def corpos_validos() -> dict[str, bytes]:
    corpos = {cod: corpo_sidra(cod) for cod in SERIES_SIDRA}
    corpos[LOCALIDADES] = corpo_localidades()
    corpos[PESQUISAS] = corpo_pesquisas()
    return corpos


# --- infraestrutura -------------------------------------------------------------------------

def relogio():
    """Relógio que avança 500 ms a cada chamada, para carimbos distintos."""
    base = datetime(2026, 11, 14, 15, 30, 0, tzinfo=timezone.utc)
    passos = count()
    return lambda: base + timedelta(milliseconds=500 * next(passos))


def baixar_por_cod(corpos: dict[str, bytes], status: int = 200):
    """baixar_fn que devolve o corpo da fonte cuja URL foi pedida."""
    por_url = {catalogo.obter(cod).url_extrator: corpo for cod, corpo in corpos.items()}

    def baixar_fn(url, sessao):
        return RespostaHTTP(url, status, por_url[url], duracao_ms=10, tentativas=1)
    return baixar_fn


def arquivos(pasta: Path) -> dict[str, bytes]:
    """Conteúdo de todos os arquivos de uma pasta (vazio se ela não existir)."""
    if not pasta.is_dir():
        return {}
    return {p.name: p.read_bytes() for p in sorted(pasta.iterdir())}


class Ambiente:
    """RAW e controle em tmp_path, com um relógio compartilhado entre coletas."""

    def __init__(self, tmp_path: Path) -> None:
        self.pasta_raw = tmp_path / "raw"
        self.controle = tmp_path / "controle" / "execucoes.jsonl"
        self.agora = relogio()

    def coletar(self, cod_serie: str, corpo: bytes | None = None, *, baixar_fn=None,
                agora=None, **kwargs):
        if baixar_fn is None:
            baixar_fn = baixar_por_cod({cod_serie: corpo})
        return coletar(cod_serie, pasta_raw=self.pasta_raw, arquivo_controle=self.controle,
                       baixar_fn=baixar_fn, agora=agora or self.agora, versao="abc1234",
                       **kwargs)

    def gravar_cadastro(self, corpo: bytes | None = None):
        return self.coletar(LOCALIDADES, corpo or corpo_localidades())

    def execucoes(self) -> list[dict]:
        return ler_execucoes(self.controle)


@pytest.fixture
def amb(tmp_path) -> Ambiente:
    return Ambiente(tmp_path)


# --- 2. resposta vazia ou em formato inesperado, por fonte ----------------------------------

RESPOSTAS_INESPERADAS = [
    # (fonte, corpo, trecho esperado da mensagem)
    *[(cod, b"", "não é JSON válido") for cod in [LOCALIDADES, *SERIES_SIDRA, PESQUISAS]],
    *[(cod, b"[]", "esperad") for cod in [LOCALIDADES, *SERIES_SIDRA, PESQUISAS]],
    *[(cod, b"{}", "esperad") for cod in [LOCALIDADES, *SERIES_SIDRA, PESQUISAS]],
    *[(cod, b"null", "esperad") for cod in [LOCALIDADES, *SERIES_SIDRA, PESQUISAS]],
    # SIDRA devolvendo dict em vez de lista
    *[(cod, json.dumps({"V": "Valor", "D1C": "Município (Código)"}).encode(),
       "esperado cabeçalho") for cod in SERIES_SIDRA],
    # SIDRA só com o cabeçalho, sem nenhuma linha de dados
    *[(cod, json.dumps([CABECALHO_SIDRA]).encode(), "pelo menos uma linha")
      for cod in SERIES_SIDRA],
    # SIDRA com linhas de dados, mas sem os rótulos do cabeçalho
    *[(cod, json.dumps([{"V": "1"}, {"V": "2"}]).encode(), "rótulos ausentes")
      for cod in SERIES_SIDRA],
    # SIDRA com linha que é lista, e não objeto
    *[(cod, json.dumps([CABECALHO_SIDRA, ["4205407", "2010", "100"]]).encode(),
       "fora do formato do cabeçalho") for cod in SERIES_SIDRA],
    # Localidades: lista de nomes em vez de objetos com "id"
    (LOCALIDADES, json.dumps(["Florianópolis", "Joinville"]).encode(), "esperados 295"),
    # Localidades recebendo uma resposta SIDRA
    (LOCALIDADES, corpo_sidra("sidra_4709_v93"), "fora do padrão 42xxxxx"),
    # Pesquisas: indicador sem "res", com "res" vazio e resultado sem "localidade"
    (PESQUISAS, json.dumps([{"id": 47001}]).encode(), "sem lista 'res'"),
    (PESQUISAS, json.dumps([{"id": 47001, "res": []}]).encode(), "sem lista 'res'"),
    (PESQUISAS, json.dumps([{"id": 47001, "res": [{"res": {"2021": "1.00"}}]}]).encode(),
     "sem 'localidade'"),
    # Pesquisas recebendo uma resposta SIDRA
    (PESQUISAS, corpo_sidra("sidra_4709_v93"), "sem lista 'res'"),
]


@pytest.mark.parametrize(
    "cod_serie, corpo, trecho", RESPOSTAS_INESPERADAS,
    ids=[f"{c}-{i}" for i, (c, _, _) in enumerate(RESPOSTAS_INESPERADAS)],
)
def test_resposta_vazia_ou_inesperada_falha_sem_gravar_raw_e_registra_falha(
        amb, cod_serie, corpo, trecho):
    amb.gravar_cadastro()  # o cadastro existe: a falha vem só da resposta
    pasta_serie = amb.pasta_raw / cod_serie
    antes = arquivos(pasta_serie)

    with pytest.raises(ErroValidacao, match=trecho):
        amb.coletar(cod_serie, corpo)

    assert arquivos(pasta_serie) == antes
    ultima = amb.execucoes()[-1]
    assert ultima["cod_serie"] == cod_serie
    assert ultima["status"] == "falha"
    assert ultima["arquivo"] is None
    assert ultima["n_registros"] is None
    assert ultima["erro"].startswith("ErroValidacao:")


def test_status_204_com_corpo_vazio_falha_na_validacao_minima(amb):
    sessao = Mock()
    sessao.get.return_value = Mock(status_code=204, content=b"", headers={})
    with pytest.raises(ErroValidacao, match="Status HTTP 204"):
        amb.coletar(LOCALIDADES, baixar_fn=baixar, sessao=sessao)
    assert not (amb.pasta_raw / LOCALIDADES).exists()
    assert amb.execucoes()[-1]["status"] == "falha"


def test_429_persistente_via_coletar_nao_grava_raw_e_registra_o_status(amb):
    sessao = Mock()
    sessao.get.return_value = Mock(status_code=429, content=b"", headers={})
    dormir = Mock()
    with pytest.raises(ErroHTTP) as erro:
        amb.coletar(LOCALIDADES, baixar_fn=partial(baixar, dormir=dormir), sessao=sessao)
    assert erro.value.status_http == 429
    assert sessao.get.call_count == 3
    assert not (amb.pasta_raw / LOCALIDADES).exists()
    [execucao] = amb.execucoes()
    assert execucao["status"] == "falha"
    assert "HTTP 429" in execucao["erro"]


def test_timeout_persistente_via_coletar_nao_grava_raw(amb):
    sessao = Mock()
    sessao.get.side_effect = requests.Timeout()
    with pytest.raises(ErroHTTP, match="timeout"):
        amb.coletar(LOCALIDADES, baixar_fn=partial(baixar, dormir=Mock()), sessao=sessao)
    assert not (amb.pasta_raw / LOCALIDADES).exists()
    assert amb.execucoes()[-1]["erro"].startswith("ErroHTTP:")


# --- 3. não sobrescrita da RAW e coleta incompleta ------------------------------------------

def test_segunda_coleta_com_o_mesmo_carimbo_falha_e_preserva_o_original(amb):
    instante = datetime(2026, 11, 14, 15, 30, 0, 123000, tzinfo=timezone.utc)
    meta = amb.coletar(LOCALIDADES, corpo_localidades(), agora=lambda: instante)
    pasta = amb.pasta_raw / LOCALIDADES
    antes = arquivos(pasta)
    assert set(antes) == {meta["arquivo_dados"],
                          meta["arquivo_dados"].replace(".json", ".meta.json")}

    with pytest.raises(ErroGravacao, match="nunca é sobrescrita"):
        amb.coletar(LOCALIDADES, corpo_localidades(sufixo_nome=" (novo)"),
                    agora=lambda: instante)

    assert arquivos(pasta) == antes  # bytes e .meta.json intactos, sem temporário sobrando
    primeira, segunda = amb.execucoes()
    assert primeira["status"] == "sucesso"
    assert segunda["status"] == "falha"
    assert segunda["arquivo"] is None
    assert segunda["erro"].startswith("ErroGravacao:")


def _coletar_incompleta(amb: Ambiente, cod_serie: str, corpo: bytes) -> None:
    """Simula uma coleta interrompida: os dados são gravados, o .meta.json não."""
    link_real = os.link

    def link_falha_no_meta(origem, destino):
        if str(destino).endswith(raw.SUFIXO_META):
            raise OSError(errno.EIO, "falha simulada")
        return link_real(origem, destino)

    with patch("brasil_em_dados.extract.raw.os.link", side_effect=link_falha_no_meta):
        with pytest.raises(ErroGravacao):
            amb.coletar(cod_serie, corpo)


def test_coleta_incompleta_e_ignorada_por_ultima_coleta_valida(amb):
    valida = amb.coletar(LOCALIDADES, corpo_localidades())
    _coletar_incompleta(amb, LOCALIDADES, corpo_localidades(sufixo_nome=" (B)"))

    assert len(raw.coletas_incompletas(amb.pasta_raw / LOCALIDADES)) == 1
    dados, meta = raw.ultima_coleta_valida(amb.pasta_raw, LOCALIDADES)
    assert dados.name == valida["arquivo_dados"]
    assert meta["sha256"] == valida["sha256"]


def test_igual_a_anterior_compara_com_a_ultima_valida_e_nao_com_a_incompleta(amb, caplog):
    amb.coletar(LOCALIDADES, corpo_localidades())                       # A, válida
    _coletar_incompleta(amb, LOCALIDADES, corpo_localidades(sufixo_nome=" (B)"))  # B, incompleta

    with caplog.at_level(logging.WARNING, logger="brasil_em_dados.extract.raw"):
        meta = amb.coletar(LOCALIDADES, corpo_localidades(sufixo_nome=" (B)"))  # B, válida

    assert meta["igual_a_anterior"] is False  # comparou com A, não com a B incompleta
    assert "Coleta incompleta ignorada" in caplog.text


def test_igual_a_anterior_ignora_incompleta_diferente_entre_duas_validas_iguais(amb):
    amb.coletar(LOCALIDADES, corpo_localidades())
    _coletar_incompleta(amb, LOCALIDADES, corpo_localidades(sufixo_nome=" (B)"))
    meta = amb.coletar(LOCALIDADES, corpo_localidades())
    assert meta["igual_a_anterior"] is True


def test_igual_a_anterior_em_coletas_seguidas(amb):
    primeira = amb.coletar(LOCALIDADES, corpo_localidades())
    repetida = amb.coletar(LOCALIDADES, corpo_localidades())
    mudou = amb.coletar(LOCALIDADES, corpo_localidades(sufixo_nome=" (novo)"))

    assert primeira["igual_a_anterior"] is False  # sem coleta anterior
    assert repetida["igual_a_anterior"] is True
    assert mudou["igual_a_anterior"] is False
    # toda coleta grava arquivos novos, mesmo com resposta idêntica
    nomes = {primeira["arquivo_dados"], repetida["arquivo_dados"], mudou["arquivo_dados"]}
    assert len(nomes) == 3
    assert len(arquivos(amb.pasta_raw / LOCALIDADES)) == 6


# --- 5. códigos no cadastro e zero suspeito, ponta a ponta ----------------------------------

@pytest.mark.parametrize("cod_serie", SERIES_SIDRA)
def test_serie_sidra_valida_com_cadastro_da_raw_grava_coleta(amb, cod_serie):
    amb.gravar_cadastro()
    meta = amb.coletar(cod_serie, corpo_sidra(cod_serie))
    assert (amb.pasta_raw / cod_serie / meta["arquivo_dados"]).exists()
    assert amb.execucoes()[-1]["status"] == "sucesso"


@pytest.mark.parametrize("cod_serie", SERIES_SIDRA)
def test_serie_sidra_com_municipio_fora_do_cadastro_nao_grava_raw(amb, cod_serie):
    amb.gravar_cadastro()
    corpo = corpo_sidra(cod_serie, trocar=(ANTIGOS[0], DESCONHECIDO))

    with pytest.raises(ErroValidacao, match=f"municípios fora do cadastro: .*{DESCONHECIDO}"):
        amb.coletar(cod_serie, corpo)

    assert not (amb.pasta_raw / cod_serie).exists()
    ultima = amb.execucoes()[-1]
    assert ultima["status"] == "falha"
    assert "municípios fora do cadastro" in ultima["erro"]


@pytest.mark.parametrize("cod_serie", [*SERIES_SIDRA, PESQUISAS])
def test_serie_sem_cadastro_na_raw_falha_pedindo_para_coletar_localidades(amb, cod_serie):
    corpo = corpo_pesquisas() if cod_serie == PESQUISAS else corpo_sidra(cod_serie)

    with pytest.raises(ErroValidacao, match="colete ibge_localidades_sc antes"):
        amb.coletar(cod_serie, corpo)

    assert not (amb.pasta_raw / cod_serie).exists()
    [execucao] = amb.execucoes()
    assert execucao["status"] == "falha"
    assert "colete ibge_localidades_sc antes" in execucao["erro"]


def test_cadastro_so_com_coleta_incompleta_conta_como_ausente(amb):
    _coletar_incompleta(amb, LOCALIDADES, corpo_localidades())
    with pytest.raises(ErroValidacao, match="colete ibge_localidades_sc antes"):
        amb.coletar("sidra_4709_v93", corpo_sidra("sidra_4709_v93"))
    assert not (amb.pasta_raw / "sidra_4709_v93").exists()


def test_serie_usa_o_ultimo_cadastro_valido_e_ignora_cadastro_incompleto_mais_novo(amb):
    amb.gravar_cadastro()
    _coletar_incompleta(amb, LOCALIDADES, corpo_localidades(TODOS[:-1] + [DESCONHECIDO]))
    meta = amb.coletar("sidra_4709_v93", corpo_sidra("sidra_4709_v93"))
    assert meta["n_registros"] == 295


def test_pesquisas_com_codigo_sem_correspondente_no_cadastro_registra_o_motivo(amb):
    amb.gravar_cadastro()
    codigos6 = [c[:6] for c in TODOS[:-1]] + [DESCONHECIDO[:6]]
    with pytest.raises(ErroValidacao, match="sem correspondente no cadastro: .*429999"):
        amb.coletar(PESQUISAS, corpo_pesquisas(codigos6))
    assert not (amb.pasta_raw / PESQUISAS).exists()
    assert "sem correspondente" in amb.execucoes()[-1]["erro"]


def test_valor_zero_no_sidra_avisa_no_log_e_grava_a_coleta(amb, caplog):
    amb.gravar_cadastro()
    corpo = corpo_sidra("sidra_4709_v93", valores={(ANTIGOS[0], 2022): "0"})

    with caplog.at_level(logging.WARNING, logger="brasil_em_dados.extract.conteudo"):
        meta = amb.coletar("sidra_4709_v93", corpo)

    assert (amb.pasta_raw / "sidra_4709_v93" / meta["arquivo_dados"]).exists()
    avisos = [r for r in caplog.records
              if r.name == "brasil_em_dados.extract.conteudo" and r.levelno == logging.WARNING]
    assert len(avisos) == 1
    assert ANTIGOS[0] in avisos[0].getMessage()
    assert amb.execucoes()[-1]["status"] == "sucesso"


# --- 4. linha de comando com "todas", ponta a ponta -----------------------------------------

def _coletar_fn(amb: Ambiente, corpos: dict[str, bytes]):
    return partial(coletar, pasta_raw=amb.pasta_raw, arquivo_controle=amb.controle,
                   baixar_fn=baixar_por_cod(corpos), agora=amb.agora, versao="abc1234")


def test_todas_com_respostas_validas_grava_todas_as_fontes(amb):
    resultados = cli.executar(cli.ordem_de_coleta(), _coletar_fn(amb, corpos_validos()))
    assert [r.erro for r in resultados] == [None] * len(catalogo.FONTES)
    for cod_serie in catalogo.FONTES:
        assert raw.ultima_coleta_valida(amb.pasta_raw, cod_serie) is not None
    assert [e["status"] for e in amb.execucoes()] == ["sucesso"] * len(catalogo.FONTES)


def test_todas_com_uma_serie_falhando_grava_as_demais(amb):
    corpos = corpos_validos()
    corpos["sidra_1378_v93"] = b"{}"
    resultados = cli.executar(cli.ordem_de_coleta(), _coletar_fn(amb, corpos))

    falhas = {r.cod_serie: r.erro for r in resultados if r.meta is None}
    assert list(falhas) == ["sidra_1378_v93"]
    assert falhas["sidra_1378_v93"].startswith("ErroValidacao:")
    assert not (amb.pasta_raw / "sidra_1378_v93").exists()
    for cod_serie in set(catalogo.FONTES) - {"sidra_1378_v93"}:
        assert raw.ultima_coleta_valida(amb.pasta_raw, cod_serie) is not None
    status = {e["cod_serie"]: e["status"] for e in amb.execucoes()}
    assert status["sidra_1378_v93"] == "falha"
    assert sum(s == "sucesso" for s in status.values()) == len(catalogo.FONTES) - 1


def test_todas_com_cadastro_falhando_faz_as_series_falharem_sem_gravar(amb):
    corpos = corpos_validos()
    corpos[LOCALIDADES] = b""
    resultados = cli.executar(cli.ordem_de_coleta(), _coletar_fn(amb, corpos))

    assert all(r.meta is None for r in resultados)
    for r in resultados[1:]:
        assert "colete ibge_localidades_sc antes" in r.erro
    assert not amb.pasta_raw.exists() or not any(amb.pasta_raw.rglob("*"))
    assert [e["status"] for e in amb.execucoes()] == ["falha"] * len(catalogo.FONTES)


def test_main_todas_com_uma_falha_devolve_1_e_registra_no_resumo(amb, caplog):
    corpos = corpos_validos()
    corpos[PESQUISAS] = b"[]"
    with patch.object(cli, "configurar_logging"), \
            patch.object(cli, "coletar", _coletar_fn(amb, corpos)), \
            caplog.at_level(logging.INFO, logger="brasil_em_dados"):
        codigo = cli.main(["todas"])

    assert codigo == 1
    linhas_falha = [r.getMessage() for r in caplog.records
                    if r.name == "brasil_em_dados.extract.cli" and r.levelno == logging.ERROR]
    assert len(linhas_falha) == 1
    assert PESQUISAS in linhas_falha[0]
    assert f"Total: {(n := len(catalogo.FONTES))} coleta(s), {n - 1} sucesso(s), 1 falha(s)" in caplog.text


def test_main_todas_com_sucesso_devolve_0_e_resumo_sem_falhas(amb, caplog):
    with patch.object(cli, "configurar_logging"), \
            patch.object(cli, "coletar", _coletar_fn(amb, corpos_validos())), \
            caplog.at_level(logging.INFO, logger="brasil_em_dados"):
        codigo = cli.main(["todas"])

    assert codigo == 0
    assert f"Total: {(n := len(catalogo.FONTES))} coleta(s), {n} sucesso(s), 0 falha(s)" in caplog.text
    assert not [r for r in caplog.records
                if r.name == "brasil_em_dados.extract.cli" and r.levelno >= logging.ERROR]
