"""App Streamlit (D36) com streamlit.testing (AppTest).

- Sem banco: as páginas não têm SQL nem conexão própria, e um erro de conexão mostra só a
  mensagem amigável, sem URL, host, usuário ou senha.
- Integração (bed_readonly): cada página abre sem erro; os números de referência R01–R15 de
  docs/dashboards.md (seção 6) aparecem no app; nenhuma tela traz URL de conexão ou senha; os
  visuais de Censo não mudam com o filtro de ano.
"""

import json
import logging
import re
import socket
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from brasil_em_dados import db
from brasil_em_dados.config import RAIZ_PROJETO
from brasil_em_dados.analise.graficos import PALETA
from brasil_em_dados.dashboard import dados
from brasil_em_dados.dashboard import textos as t

PASTA_APP = RAIZ_PROJETO / "dashboards" / "streamlit"
APP = PASTA_APP / "app.py"
PAGINAS = ("visao_geral", "populacao", "economia", "perfil", "comparacao", "sobre")
ARQUIVOS_DO_APP = [APP, *sorted((PASTA_APP / "paginas").glob("*.py"))]
TIMEOUT_S = 120
URL_DE_CONEXAO = re.compile(r"postgres(?:ql)?(?:\+\w+)?://", re.IGNORECASE)

PROIBIDOS_NAS_PAGINAS = {
    "SQL na página": re.compile(r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)\s"),
    "conexão própria": re.compile(r"\bcreate_engine\b|\bpsycopg\b|\bengine_\w+\(|\bsqlalchemy\b"),
    "consulta direta": re.compile(r"\bconsultas\.|\bread_sql\b"),
    "conversão de unidade": re.compile(r"[*/]\s*(?:1e\d+|10{3,}(?:\.0*)?\b|1_000)"),
    "per capita agregado": re.compile(r"pib_per_capita_reais['\"]\]\s*\.\s*(?:sum|mean)\("),
}


def _limpar_cache() -> None:
    st.cache_data.clear()
    st.cache_resource.clear()


def _escolher(app: AppTest, rotulo: str, texto: str) -> None:
    """Escolhe uma opção de um filtro da barra lateral pelo texto exibido."""
    caixa = next(s for s in app.sidebar.selectbox if s.label == rotulo)
    caixa.select_index(list(caixa.options).index(texto)).run()


def _abrir(pagina: str | None = None, ano: int | None = None, regiao: str | None = None,
           municipio: str | None = None) -> AppTest:
    app = AppTest.from_file(str(APP), default_timeout=TIMEOUT_S).run()
    if regiao is not None:
        _escolher(app, "Região intermediária", regiao)
    if municipio is not None:
        _escolher(app, "Município", municipio)
    if ano is not None:
        next(s for s in app.sidebar.selectbox if s.label == "Ano").set_value(ano).run()
    if pagina is not None:
        app.switch_page(f"paginas/{pagina}.py").run()
    return app


def _texto_da_tela(app: AppTest) -> str:
    """Todo o texto visível: títulos, markdown, avisos, métricas, tabelas e specs dos gráficos."""
    partes: list[str] = []
    for tipo in ("title", "header", "subheader", "markdown", "caption", "info", "warning",
                 "error", "success", "text"):
        partes.extend(str(e.value) for e in getattr(app, tipo))
    partes.extend(f"{m.label} {m.value}" for m in app.metric)
    partes.extend(e.label for e in app.expander)
    partes.extend(t.value.to_string() for t in app.dataframe)
    # O spec vem com acentos escapados ("ã" como ã): decodifica para procurar o texto.
    partes.extend(json.dumps(json.loads(g.proto.spec), ensure_ascii=False)
                  for g in app.get("plotly_chart"))
    partes.extend(e.value.message for e in app.exception)
    return "\n".join(partes)


def _tabela(app: AppTest, id_visual: str) -> pd.DataFrame:
    expansor = next(e for e in app.expander if e.label == f"Dados — {id_visual}")
    return expansor.dataframe[0].value


def _grafico(app: AppTest, trecho_do_titulo: str) -> str:
    """Spec (JSON) do único gráfico cujo título contém o trecho."""
    specs = [g.proto.spec for g in app.get("plotly_chart")
             if trecho_do_titulo in json.loads(g.proto.spec)["layout"]["title"]["text"]]
    assert len(specs) == 1, f"{trecho_do_titulo!r}: {len(specs)} gráficos"
    return specs[0]


def _metrica(app: AppTest, rotulo: str) -> str:
    return next(m.value for m in app.metric if m.label == rotulo)


def _linha(tabela: pd.DataFrame, coluna: str, valor: object) -> pd.Series:
    linhas = tabela[tabela[coluna] == valor]
    assert len(linhas) == 1, f"{coluna} = {valor!r}: {len(linhas)} linhas"
    return linhas.iloc[0]


# -- sem banco -----------------------------------------------------------------------------------

@pytest.mark.parametrize("arquivo", ARQUIVOS_DO_APP, ids=lambda p: p.name)
def test_paginas_so_usam_as_funcoes_do_pacote(arquivo: Path):
    codigo = arquivo.read_text(encoding="utf-8")
    for motivo, padrao in PROIBIDOS_NAS_PAGINAS.items():
        assert not padrao.search(codigo), f"{arquivo.name}: {motivo}"


def test_cada_secao_do_documento_tem_uma_pagina():
    assert sorted(p.stem for p in (PASTA_APP / "paginas").glob("*.py")) == sorted(PAGINAS)
    app = APP.read_text(encoding="utf-8")
    for pagina in PAGINAS:
        assert f'"paginas/{pagina}.py"' in app


@pytest.fixture
def banco_inacessivel(monkeypatch):
    """Ambiente apontando para uma porta fechada, com usuário e senha sentinela."""
    with socket.socket() as s:  # porta livre: ninguém escuta nela depois do close
        s.bind(("127.0.0.1", 0))
        porta = s.getsockname()[1]
    sentinelas = {"PG_HOST": "127.0.0.1", "PG_PORT": str(porta), "PG_DATABASE": "banco_sentinela",
                  "PG_READONLY_USER": "usuario_sentinela", "PG_READONLY_PASSWORD": "senha_sentinela"}
    for nome, valor in sentinelas.items():
        monkeypatch.setenv(nome, valor)  # o processo tem precedência sobre o .env (db.ler_ambiente)
    _limpar_cache()
    yield sentinelas
    _limpar_cache()  # o engine com o ambiente sentinela não pode ficar no cache


def test_erro_de_conexao_mostra_mensagem_amigavel_sem_detalhes(banco_inacessivel, caplog):
    with caplog.at_level(logging.INFO):
        app = AppTest.from_file(str(APP), default_timeout=TIMEOUT_S).run()
    assert "Falha ao ler a GOLD" in caplog.text
    for nome in ("PG_DATABASE", "PG_READONLY_USER", "PG_READONLY_PASSWORD"):
        assert banco_inacessivel[nome] not in caplog.text  # nem no log (só o tipo do erro)
    assert not app.exception
    assert [e.value for e in app.error] == [dados.MENSAGEM_ERRO]
    texto = _texto_da_tela(app)
    assert not URL_DE_CONEXAO.search(texto)
    for valor in banco_inacessivel.values():
        assert valor not in texto


def test_erro_de_configuracao_mostra_a_mesma_mensagem(monkeypatch):
    monkeypatch.setattr(db, "ler_ambiente", lambda arquivo=None: {})
    _limpar_cache()
    try:
        app = AppTest.from_file(str(APP), default_timeout=TIMEOUT_S).run()
    finally:
        _limpar_cache()
    assert not app.exception
    assert [e.value for e in app.error] == [dados.MENSAGEM_ERRO]
    assert "PG_" not in _texto_da_tela(app)  # nem o nome das variáveis vai para a tela


# -- integração (bed_readonly) -------------------------------------------------------------------

@pytest.fixture(scope="module")
def com_banco(request):
    """Pula sem banco (fixture engine_readonly do conftest) e começa com o cache limpo."""
    request.getfixturevalue("engine_readonly")
    _limpar_cache()
    yield
    _limpar_cache()


@pytest.mark.integracao
@pytest.mark.parametrize("pagina", [None, *PAGINAS])
def test_pagina_abre_sem_erro_e_sem_segredos(com_banco, pagina):
    app = _abrir(pagina)
    assert not app.exception, [e.value for e in app.exception]
    assert not app.error
    texto = _texto_da_tela(app)
    assert not URL_DE_CONEXAO.search(texto)
    ambiente = db.ler_ambiente()  # só em memória; nunca impresso
    for variavel in ("PG_PASSWORD", "PG_READONLY_PASSWORD"):
        valor = ambiente.get(variavel)
        if valor:
            assert valor not in texto, f"valor de {variavel} apareceu na tela"


# Números de referência: docs/dashboards.md, seção 6 (consultados como bed_readonly em 24/11/2026).
REFERENCIA = {
    "R01": ["7.610.361"],
    "R02": ["6.248.436"],
    "R03": ["R$ 513.392.972.000,00"],
    "R04": ["R$ 153.726.009.000,00"],
    "R05": ["6.362.734", "293", "2"],
    "R06": ["Joinville", "616.317", "8,0984%", "Florianópolis", "537.211", "7,0589%",
            "Blumenau", "361.261", "4,7470%"],
    "R07": ["Joinville", "R$ 49.815.877.000,00", "9,7033%", "Itajaí", "R$ 48.195.909.000,00",
            "9,3877%", "Florianópolis", "R$ 31.190.132.000,00", "6,0753%"],
    "R08": ["421.240", "537.211", "+27,53%"],
    "R09": ["6,5444%", "9,3877%"],
    "R10": ["293", "70"],
    "R11": ["Araquari", "R$ 218.625,97"],
    "R12": ["R$ 52.591,20"],
    "R13": ["61", "51"],
    "R14": ["295", "0"],
    "R15": ["295"],
}


def test_referencias_do_teste_estao_no_documento():
    """O teste e a tabela do documento andam juntos: cada valor esperado está na linha do R."""
    documento = (RAIZ_PROJETO / "docs" / "dashboards.md").read_text(encoding="utf-8")
    linhas = {m.group(1): m.group(0) for m in re.finditer(r"^\| (R\d\d) \|.*$", documento, re.M)}
    assert sorted(linhas) == sorted(REFERENCIA)
    for codigo, valores in REFERENCIA.items():
        for valor in valores:
            assert valor in linhas[codigo], f"{codigo}: {valor} não está no documento"


@pytest.mark.integracao
def test_referencias_na_visao_geral(com_banco):
    app = _abrir("visao_geral", ano=2023)
    assert _metrica(app, "População (Censo 2022)") == REFERENCIA["R01"][0]
    vg2 = _tabela(app, "VG2")
    assert _linha(vg2, "Ano", 2023)["PIB nominal (R$)"] == REFERENCIA["R03"][0]
    assert _linha(vg2, "Ano", 2010)["PIB nominal (R$)"] == REFERENCIA["R04"][0]
    assert REFERENCIA["R03"][0] in _texto_da_tela(app)  # valor exato do cartão VG1


@pytest.mark.integracao
def test_referencias_na_populacao(com_banco):
    app = _abrir("populacao")
    pop1 = _tabela(app, "POP1").head(3)
    r06 = REFERENCIA["R06"]
    assert pop1["Município"].tolist() == r06[0::3]
    assert pop1["População (Censo 2022)"].tolist() == r06[1::3]
    assert pop1["Participação no estado"].tolist() == r06[2::3]
    assert _metrica(app, "Municípios comparáveis") == REFERENCIA["R10"][0]
    assert _metrica(app, "Perderam população") == REFERENCIA["R10"][1]
    sc = _linha(_tabela(app, "POP3"), "Território", "Santa Catarina")
    assert sc["Censo 2010"] == REFERENCIA["R02"][0] and sc["Censo 2022"] == REFERENCIA["R01"][0]
    ano_2012 = _linha(_tabela(app, "POP4"), "Ano", 2012)
    assert [ano_2012["População estimada"], ano_2012["Municípios somados"],
            ano_2012["Municípios excluídos"]] == REFERENCIA["R05"]
    assert "regra 13" in ano_2012["Aviso"]
    bases = _tabela(app, "POP4 · variações entre bases")
    quebra, revisao = _linha(bases, "Variação", "2012→2013"), _linha(bases, "Variação", "2017→2018")
    assert (quebra["Pares municipais"], quebra["Com variação calculada"],
            quebra["Comparáveis"]) == (295, 0, 0)  # R14
    assert (revisao["Pares municipais"], revisao["Com variação calculada"],
            revisao["Comparáveis"]) == (295, 295, 0)  # R15
    assert "regra 12" in quebra["Motivo"] and "regra 12" in revisao["Motivo"]


@pytest.mark.integracao
def test_referencias_na_economia(com_banco):
    app = _abrir("economia", ano=2023)
    eco1 = _tabela(app, "ECO1").head(3)
    r07 = REFERENCIA["R07"]
    assert eco1["Município"].tolist() == r07[0::3]
    assert eco1["PIB nominal 2023 (R$)"].tolist() == r07[1::3]
    assert eco1["Participação no estado"].tolist() == r07[2::3]
    eco3 = _tabela(app, "ECO3")
    assert eco3.iloc[0].tolist() == REFERENCIA["R11"]
    assert _metrica(app, "PIB per capita 2023: mediana entre os municípios") == REFERENCIA["R12"][0]
    assert _metrica(app, "Variações acima de 50% em módulo") == REFERENCIA["R13"][0]
    assert _metrica(app, "Municípios") == REFERENCIA["R13"][1]


@pytest.mark.integracao
def test_referencias_no_perfil_e_na_comparacao(com_banco):
    perfil = _abrir("perfil")  # município padrão: Florianópolis
    assert [_metrica(perfil, "População (Censo 2010)"), _metrica(perfil, "População (Censo 2022)"),
            _metrica(perfil, "Variação entre os Censos")] == REFERENCIA["R08"]
    comparacao = _abrir("comparacao")  # padrão: Joinville, Florianópolis e Itajaí
    cmp1 = _tabela(comparacao, "CMP1")
    itajai = cmp1[cmp1["Município"] == "Itajaí"].set_index("Ano")
    coluna = "Participação no PIB nominal do estado"
    assert [itajai.loc[2010, coluna], itajai.loc[2023, coluna]] == REFERENCIA["R09"]
    censo = _linha(_tabela(comparacao, "CMP3"), "Município", "Florianópolis")
    assert [censo["Censo 2010"], censo["Censo 2022"], censo["Variação"]] == REFERENCIA["R08"]


def _visuais_de_censo(app: AppTest, pagina: str) -> dict[str, object]:
    """Tabelas, métricas e gráficos de Censo de cada página (ver docs/dashboards.md, seção 3)."""
    if pagina == "visao_geral":
        return {"VG1": _metrica(app, "População (Censo 2022)"), "VG4": _tabela(app, "VG4"),
                "VG4 gráfico": _grafico(app, "a participação no PIB nominal supera")}
    if pagina == "populacao":
        return {"POP1": _tabela(app, "POP1"), "POP2": _tabela(app, "POP2"),
                "POP3": _tabela(app, "POP3"),
                "POP2 métricas": [m.value for m in app.metric],
                "POP1 gráfico": _grafico(app, "lidera a população"),
                "POP2 gráfico": _grafico(app, "perderam população entre os Censos"),
                "POP3 gráfico": _grafico(app, "Entre os Censos, a região de")}
    if pagina == "perfil":
        metricas = {rotulo: _metrica(app, rotulo) for rotulo in (
            "População (Censo 2010)", "População (Censo 2022)", "Variação entre os Censos",
            "Posição em população (Censo 2022)")}
        return {**metricas, "PER3 (b) gráfico": _grafico(app, "Censo de ")}
    if pagina == "comparacao":
        return {"CMP3": _tabela(app, "CMP3"), "CMP3 gráfico": _grafico(app, "Entre os Censos,")}
    raise ValueError(pagina)


@pytest.mark.integracao
@pytest.mark.parametrize("pagina", ["visao_geral", "populacao", "perfil", "comparacao"])
def test_visuais_de_censo_nao_mudam_com_o_ano(com_banco, pagina):
    em_2010 = _visuais_de_censo(_abrir(pagina, ano=2010), pagina)
    em_2023 = _visuais_de_censo(_abrir(pagina, ano=2023), pagina)
    assert em_2010.keys() == em_2023.keys()
    for chave in em_2010:
        a, b = em_2010[chave], em_2023[chave]
        if isinstance(a, pd.DataFrame):
            pd.testing.assert_frame_equal(a, b, obj=chave)
        else:
            assert a == b, chave


@pytest.mark.integracao
def test_ano_sem_estimativa_nao_usa_o_censo_no_lugar(com_banco):
    app = _abrir("populacao", ano=2022)
    assert any("Sem estimativa publicada em 2022" in i.value for i in app.info)
    anos = _tabela(app, "POP4")["Ano"].tolist()
    assert 2022 not in anos and 2010 not in anos


# -- região, anos-limite e municípios instalados em 2013 (revisão do D36) ------------------------

@pytest.mark.integracao
@pytest.mark.parametrize("regiao", ["Caçador", "Criciúma"])  # Caçador: a menor (16 municípios)
@pytest.mark.parametrize("ano", [2010, 2012, 2023])
@pytest.mark.parametrize("pagina", PAGINAS)
def test_paginas_abrem_com_regiao_e_anos_limite(com_banco, pagina, ano, regiao):
    app = _abrir(pagina, ano=ano, regiao=regiao)
    assert not app.exception, [e.value for e in app.exception]
    assert not app.error
    assert "de a região" not in _texto_da_tela(app)


@pytest.mark.integracao
def test_textos_com_regiao_usam_da_regiao(com_banco):
    app = _abrir("visao_geral", regiao="Florianópolis")
    assert "VG1 · Qual o tamanho da região de Florianópolis?" in [s.value for s in app.subheader]
    assert "PIB nominal da região de Florianópolis:" in _texto_da_tela(app)
    economia = _abrir("economia", regiao="Florianópolis")
    assert any(m.label.endswith("mediana entre os municípios da região de Florianópolis")
               for m in economia.metric)


@pytest.mark.integracao
def test_eco3_em_regiao_pequena_mostra_todos_e_colore_por_pertenca(com_banco):
    app = _abrir("economia", regiao="Caçador")
    tabela = _tabela(app, "ECO3")
    com_valor = int(_metrica(app, "Municípios com valor"))
    assert len(tabela) == com_valor < 20  # com até 20 municípios, aparecem todos, sem repetir
    spec = json.loads(_grafico(app, "o PIB per capita de"))
    barras = spec["data"][0]
    maiores = set(tabela["Município"].head(10))  # a tabela vem do maior para o menor
    for nome, cor in zip(barras["y"], barras["marker"]["color"]):
        if cor != PALETA["contraste"]:  # o município do filtro fica em destaque
            assert (cor == PALETA["principal"]) == (nome in maiores), nome
    rodape = next(a["text"] for a in spec["layout"]["annotations"] if a["text"].startswith("Fonte"))
    assert f"Todos os {com_valor} municípios" in rodape


@pytest.mark.integracao
def test_eco2_em_2010_pede_outro_ano(com_banco):
    app = _abrir("economia", ano=2010)
    assert any("depois de 2010" in i.value for i in app.info)


@pytest.mark.integracao
def test_municipio_instalado_em_2013_antes_da_instalacao(com_banco):
    perfil = _abrir("perfil", ano=2010, municipio="Pescaria Brava")
    assert not perfil.exception
    texto = _texto_da_tela(perfil)
    assert t.AVISO_NAO_INSTALADO in texto
    assert "Sem participação no PIB em 2010" in texto  # M5: o título não troca de ano em silêncio
    assert '"sem dado"' in _grafico(perfil, "Censo de Pescaria Brava")  # I4: coluna de 2010
    comparacao = _abrir("comparacao", ano=2010)
    comparacao.multiselect[0].set_value(["4212650", "4205407"]).run()
    assert not comparacao.exception
    assert '"sem dado"' in _grafico(comparacao, "maior PIB per capita")  # I4: CMP2
    cmp4 = comparacao.dataframe[-1].value
    assert set(cmp4["População estimada 2010"]) == {"sem estimativa publicada em 2010"}  # M2


@pytest.mark.integracao
def test_filtros_persistem_entre_paginas(com_banco):
    app = _abrir(regiao="Criciúma", municipio="Laguna", ano=2012)
    app.switch_page("paginas/economia.py").run()
    valores = {s.label: s.value for s in app.sidebar.selectbox}
    assert valores["Ano"] == 2012 and valores["Município"] == "4209409"
    assert "o PIB nominal da região de Criciúma de 2012" in _texto_da_tela(app)
    app.switch_page("paginas/perfil.py").run()
    assert app.title[0].value == "Perfil: Laguna"
    assert {s.label: s.value for s in app.sidebar.selectbox} == valores
