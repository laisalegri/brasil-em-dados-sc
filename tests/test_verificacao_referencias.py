"""Números de referência R01–R15: SQL × Streamlit (D37) e a ferramenta do agente de verificação.

- Sem banco: normalização exata dos valores, extração das linhas SQL, comparação e relatório; as
  consultas de sql/referencias/ são cópia exata das da seção 6 de docs/dashboards.md.
- Integração (bed_readonly): os 15 números conferem entre SQL e o caminho de dados do app, e a
  ferramenta do agente devolve o resultado sem segredos.
"""

import asyncio
import re
from decimal import Decimal

import pytest

from brasil_em_dados import db
from brasil_em_dados.config import PASTA_CONSULTAS_VERIFICACAO, RAIZ_PROJETO
from brasil_em_dados.verificacao import referencias as r
from brasil_em_dados.verificacao.ferramentas import Contexto, criar_ferramentas, ler_catalogo
from brasil_em_dados.verificacao.seguranca import segredos_do_banco
from tests.apoio_verificacao import ferramenta

SENHA = "senha-de-teste-xyz"


def _contexto(tmp_path, engine=None, segredos=(SENHA,)) -> Contexto:
    return Contexto("20261126T120000", [], ler_catalogo(PASTA_CONSULTAS_VERIFICACAO), tmp_path,
                    engine, list(segredos))


# -- normalização ---------------------------------------------------------------------------------

@pytest.mark.parametrize("valor, tipo, esperado", [
    (7610361.0, r.INTEIRO, 7610361),
    (Decimal("293"), r.INTEIRO, 293),
    (52591.2, r.REAIS, Decimal("52591.20")),                 # float do app → centavos
    (Decimal("513392972000.00"), r.REAIS, Decimal("513392972000.00")),
    (8.0984, r.PCT4, Decimal("8.0984")),
    (4.747, r.PCT4, Decimal("4.7470")),
    (27.53, r.PCT2, Decimal("27.53")),
    ("Joinville", r.TEXTO, "Joinville"),
    (0, r.LOGICO, False),
])
def test_normalizar_compara_pelo_valor_exato(valor, tipo, esperado):
    assert r.normalizar(valor, tipo) == esperado


@pytest.mark.parametrize("ausente", [None, float("nan")])
@pytest.mark.parametrize("tipo", [r.INTEIRO, r.REAIS, r.PCT4, r.TEXTO])
def test_ausencia_continua_ausencia_nunca_zero(ausente, tipo):
    assert r.normalizar(ausente, tipo) is None


def test_quatro_casas_distinguem_participacoes_proximas():
    assert r.normalizar(9.38770, r.PCT4) != r.normalizar(9.38779, r.PCT4)


def test_inteiro_com_fracao_e_recusado():
    with pytest.raises(ValueError, match="não inteiro"):
        r.normalizar(293.5, r.INTEIRO)


def test_tipo_desconhecido_e_recusado():
    with pytest.raises(ValueError, match="desconhecido"):
        r.normalizar(1, "moeda")


# -- componentes e extração do lado SQL -----------------------------------------------------------

def test_componentes_cobrem_r01_a_r15():
    assert tuple(r.COMPONENTES) == r.CODIGOS == tuple(f"R{n:02d}" for n in range(1, 16))


def test_brutos_sql_achata_o_top3_na_ordem_da_consulta():
    linhas = [{"nome_municipio": "A", "valor": 3, "participacao_percentual": 0.3},
              {"nome_municipio": "B", "valor": 2, "participacao_percentual": 0.2},
              {"nome_municipio": "C", "valor": 1, "participacao_percentual": 0.1}]
    assert r.brutos_sql("R06", linhas) == ["A", 3, 0.3, "B", 2, 0.2, "C", 1, 0.1]


def test_brutos_sql_de_r09_vai_pelo_ano_e_ano_ausente_fica_none():
    assert r.brutos_sql("R09", [{"ano": 2023, "participacao_percentual": 9.3877},
                                {"ano": 2010, "participacao_percentual": 6.5444}]) == [6.5444, 9.3877]
    assert r.brutos_sql("R09", [{"ano": 2023, "participacao_percentual": 9.3877}]) == [None, 9.3877]


def test_brutos_sql_exige_uma_linha_nas_demais():
    assert r.brutos_sql("R10", [{"comparaveis": 293, "perderam": 70}]) == [293, 70]
    with pytest.raises(ValueError, match="2 linhas"):
        r.brutos_sql("R01", [{"valor": 1}, {"valor": 2}])


def test_quantidade_de_valores_tem_de_bater_com_os_componentes():
    with pytest.raises(ValueError, match="componentes"):
        r._valores_por_componente("R05", [1, 2])


# -- comparação e relatório -----------------------------------------------------------------------

def _todos(valor_r01: object) -> dict[str, dict[str, object]]:
    valores = {c: {nome: 1 for nome, _ in comps} for c, comps in r.COMPONENTES.items()}
    valores["R01"]["população"] = valor_r01
    return valores


def test_comparar_marca_a_divergencia_e_o_relatorio_a_aponta():
    linhas = r.comparar(_todos(7610361), _todos(7610360))
    assert len(linhas) == sum(len(c) for c in r.COMPONENTES.values())
    divergentes = [l for l in linhas if not l.confere]
    assert [(l.codigo, l.componente) for l in divergentes] == [("R01", "população")]
    texto = r.relatorio_markdown(linhas)
    assert texto.startswith("14 de 15 referências conferem") and "Divergem: R01." in texto
    assert "| R01 | população | 7610361 | 7610360 | NÃO |" in texto


def test_ausencia_de_um_lado_so_nao_confere():
    linhas = r.comparar(_todos(None), _todos(7610361))
    assert not linhas[0].confere and "| NULL |" in r.relatorio_markdown(linhas)


def test_ausencia_dos_dois_lados_tambem_nao_confere():
    """Nenhuma referência admite ausência: NULL = NULL é dado faltando, não concordância."""
    linhas = r.comparar(_todos(None), _todos(None))
    assert not linhas[0].confere
    assert "| R01 | população | NULL | NULL | NÃO |" in r.relatorio_markdown(linhas)


def test_relatorio_sem_divergencia():
    texto = r.relatorio_markdown(r.comparar(_todos(1), _todos(1)))
    assert texto.startswith("15 de 15 referências conferem") and "Divergem" not in texto


# -- consultas: cópia exata do documento, só leitura da GOLD --------------------------------------

def test_consultas_sao_as_da_secao_6_do_documento():
    documento = (RAIZ_PROJETO / "docs" / "dashboards.md").read_text(encoding="utf-8")
    no_documento = {m.group(1): m.group(2).strip().rstrip(";") for m in
                    re.finditer(r"^\| (R\d\d) \| [^|]+ \| `([^`]+)` \|", documento, re.M)}
    catalogo = ler_catalogo(r.PASTA_REFERENCIAS)  # recusa o que não for um único SELECT
    assert {c.nome.upper(): c.sql for c in catalogo.values()} == no_documento
    assert set(no_documento) == set(r.CODIGOS)


def test_consultas_so_leem_a_gold():
    for consulta in ler_catalogo(r.PASTA_REFERENCIAS).values():
        origens = re.findall(r"\bFROM\s+([a-z_]+)\.", consulta.sql, re.I)
        assert origens and set(origens) == {"gold"}, consulta.nome


# -- ferramenta do agente (sem banco) -------------------------------------------------------------

def test_ferramenta_do_agente_usa_a_comparacao_e_limpa_o_texto(tmp_path, monkeypatch):
    recebido = {}

    def conferir_falso(engine, consultas):
        recebido["engine"], recebido["codigos"] = engine, sorted(consultas)
        return r.comparar(_todos(SENHA), _todos(SENHA))

    monkeypatch.setattr(r, "conferir", conferir_falso)
    texto = _contexto(tmp_path, engine="engine").referencias_dashboards()
    assert recebido == {"engine": "engine", "codigos": list(r.CODIGOS)}
    assert SENHA not in texto and "15 de 15" in texto
    assert "Power BI não entra" in texto and "Desktop" in texto


def test_ferramenta_do_agente_sem_banco_vira_erro_para_o_modelo(tmp_path):
    contexto = _contexto(tmp_path, engine=None)
    resposta = asyncio.run(ferramenta(criar_ferramentas(contexto),
                                      "referencias_dashboards").handler({}))
    assert resposta["is_error"] and "bed_readonly" in resposta["content"][0]["text"]


def test_main_sai_com_1_quando_algo_diverge(monkeypatch, capsys):
    class EngineFalso:
        def dispose(self):
            pass

    monkeypatch.setattr(db, "engine_readonly", lambda: EngineFalso())
    monkeypatch.setattr(r, "conferir", lambda e, c: r.comparar(_todos(1), _todos(2)))
    assert r.main() == 1
    assert "Divergem: R01." in capsys.readouterr().out


class _ErroDoDriver(Exception):
    """Imita o erro do psycopg: mensagem com detalhes da conexão e o atributo sqlstate."""

    def __init__(self) -> None:
        super().__init__("postgresql://usuario_x:senha_x@host_x:5432/banco_x")
        self.sqlstate = "28P01"


def test_main_com_falha_de_conexao_sai_com_2_sem_detalhes(monkeypatch, caplog, capsys):
    from sqlalchemy.exc import OperationalError

    def falhar():
        raise OperationalError("SELECT 1", None, _ErroDoDriver())

    monkeypatch.setattr(db, "engine_readonly", falhar)
    with caplog.at_level("ERROR"):
        assert r.main() == 2
    saida = caplog.text + capsys.readouterr().out
    assert "OperationalError" in caplog.text and "SQLSTATE 28P01" in caplog.text
    for detalhe in ("usuario_x", "senha_x", "host_x", "banco_x", "postgresql://"):
        assert detalhe not in saida


def test_main_sem_configuracao_do_banco_sai_com_2(monkeypatch, caplog):
    def sem_config():
        raise db.ErroConfiguracao("Variáveis de ambiente ausentes para o perfil readonly")

    monkeypatch.setattr(db, "engine_readonly", sem_config)
    with caplog.at_level("ERROR"):
        assert r.main() == 2
    assert "ErroConfiguracao" in caplog.text and "sem código" in caplog.text


def test_filtro_padrao_e_o_do_app():
    """O espelho do Streamlit usa as constantes do app, não uma cópia (Perfil = Florianópolis)."""
    import inspect

    from brasil_em_dados.dashboard import filtros

    fonte = inspect.getsource(r.brutos_streamlit)
    assert "MUNICIPIO_PADRAO" in fonte and "ANO_PADRAO" in fonte
    assert (filtros.MUNICIPIO_PADRAO, filtros.ANO_PADRAO) == ("4205407", 2023)  # R08, R07, R11, R12


# -- integração -----------------------------------------------------------------------------------

@pytest.mark.integracao
def test_sql_e_streamlit_conferem_nas_15_referencias(engine_readonly):
    consultas = {c.nome.upper(): c.sql for c in ler_catalogo(r.PASTA_REFERENCIAS).values()}
    linhas = r.conferir(engine_readonly, consultas)
    divergentes = [l for l in linhas if not l.confere]
    assert not divergentes, r.relatorio_markdown(linhas)
    por_chave = {(l.codigo, l.componente): l.sql for l in linhas}
    assert por_chave[("R12", "municípios com valor")] == 295  # a mediana usa os 295 municípios


@pytest.mark.integracao
def test_ferramenta_do_agente_com_banco_volta_limpa(engine_readonly, tmp_path):
    ambiente = db.ler_ambiente()  # só em memória; nunca impresso
    contexto = _contexto(tmp_path, engine_readonly, segredos_do_banco(ambiente))
    texto = contexto.referencias_dashboards()
    assert texto.startswith("15 de 15 referências conferem")
    assert "postgresql" not in texto.lower()
    for variavel in ("PG_PASSWORD", "PG_READONLY_PASSWORD"):
        if ambiente.get(variavel):
            assert ambiente[variavel] not in texto
