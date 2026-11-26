"""Números de referência R01–R15 (docs/dashboards.md, seção 6): SQL × Streamlit (D37).

- SQL: as 15 consultas de sql/referencias/ (cópia exata das da seção 6), como bed_readonly, numa
  transação READ ONLY.
- Streamlit: o mesmo caminho que as páginas do app usam (funções de analise.consultas, os tipos
  normalizados por dashboard.dados.normalizar_tipos e os cálculos de dashboard.calculos), só que
  sem o cache do Streamlit e com o filtro padrão (Santa Catarina, 2023, Florianópolis).
- A comparação é pelo valor, não pelo texto formatado: inteiros exatos, reais em centavos,
  participações com 4 casas e a variação entre os Censos com 2 casas (as casas da seção 6).

O Power BI fica de fora: ler as medidas exige o Power BI Desktop aberto (docs/validacao_dashboards.md).
"""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

import pandas as pd
from sqlalchemy import Engine, text

from brasil_em_dados.config import PASTA_CONSULTAS_REFERENCIAS
from brasil_em_dados.db import transacao_somente_leitura

# Nome fixo: com `python -m`, __name__ vira "__main__" e o log ficaria fora de "brasil_em_dados".
logger = logging.getLogger("brasil_em_dados.verificacao.referencias")

PASTA_REFERENCIAS = PASTA_CONSULTAS_REFERENCIAS
CODIGOS = tuple(f"R{n:02d}" for n in range(1, 16))
ITAJAI = "4208203"  # R09 é sempre Itajaí (seção 6); o município do Perfil vem do filtro padrão

# Tipos de comparação: o valor é normalizado antes de comparar.
INTEIRO, REAIS, PCT4, PCT2, TEXTO, LOGICO = "inteiro", "reais", "pct4", "pct2", "texto", "logico"
_CASAS = {REAIS: Decimal("0.01"), PCT4: Decimal("0.0001"), PCT2: Decimal("0.01")}


@dataclass(frozen=True)
class Linha:
    """Um componente de uma referência, com o valor de cada lado e se confere."""

    codigo: str
    componente: str
    tipo: str
    sql: object
    streamlit: object

    @property
    def confere(self) -> bool:
        """Iguais e presentes: nenhuma referência admite ausência, então NULL nunca confere."""
        return self.sql is not None and self.streamlit is not None and self.sql == self.streamlit


def normalizar(valor: object, tipo: str) -> object:
    """Valor comparável: None continua None (ausência nunca vira zero, regra 5)."""
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return None
    if tipo == TEXTO:
        return str(valor)
    if tipo == LOGICO:
        return bool(valor)
    numero = Decimal(str(valor))  # str() evita a expansão binária do float
    if tipo == INTEIRO:
        inteiro = numero.to_integral_value()
        if inteiro != numero:
            raise ValueError(f"Valor não inteiro onde se esperava contagem ou pessoas: {valor}")
        return int(inteiro)
    if tipo in _CASAS:
        return numero.quantize(_CASAS[tipo], rounding=ROUND_HALF_EVEN)
    raise ValueError(f"Tipo de comparação desconhecido: {tipo}")


# -- componentes de cada referência ---------------------------------------------------------------
# (componente, tipo) na ordem em que aparecem; as duas extrações devolvem as mesmas chaves.

def _top3(tipo_valor: str) -> list[tuple[str, str]]:
    """Componentes de um top 3: município, valor e participação de cada posição."""
    return [par for i in (1, 2, 3) for par in
            ((f"{i}º município", TEXTO), (f"{i}º valor", tipo_valor), (f"{i}º participação (%)", PCT4))]


COMPONENTES: dict[str, list[tuple[str, str]]] = {
    "R01": [("população", INTEIRO)],
    "R02": [("população", INTEIRO)],
    "R03": [("PIB nominal (R$)", REAIS)],
    "R04": [("PIB nominal (R$)", REAIS)],
    "R05": [("estimativa", INTEIRO), ("municípios somados", INTEIRO),
            ("municípios excluídos", INTEIRO)],
    "R06": _top3(INTEIRO),
    "R07": _top3(REAIS),
    "R08": [("Censo 2010", INTEIRO), ("Censo 2022", INTEIRO), ("variação (%)", PCT2)],
    "R09": [("participação 2010 (%)", PCT4), ("participação 2023 (%)", PCT4)],
    "R10": [("comparáveis", INTEIRO), ("perderam", INTEIRO)],
    "R11": [("município", TEXTO), ("PIB per capita (R$)", REAIS)],
    "R12": [("mediana entre os municípios (R$)", REAIS), ("municípios com valor", INTEIRO)],
    "R13": [("variações", INTEIRO), ("municípios", INTEIRO)],
    "R14": [("pares", INTEIRO), ("com variação", INTEIRO), ("algum comparável", LOGICO)],
    "R15": [("pares", INTEIRO), ("com variação", INTEIRO), ("algum comparável", LOGICO)],
}


def _valores_por_componente(codigo: str, brutos: list[object]) -> dict[str, object]:
    """Associa os valores brutos aos componentes da referência, já normalizados."""
    componentes = COMPONENTES[codigo]
    if len(brutos) != len(componentes):
        raise ValueError(f"{codigo}: {len(brutos)} valores para {len(componentes)} componentes")
    return {nome: normalizar(v, tipo) for (nome, tipo), v in zip(componentes, brutos)}


# -- lado SQL -------------------------------------------------------------------------------------

def brutos_sql(codigo: str, linhas: list[Mapping[str, Any]]) -> list[object]:
    """Valores brutos de uma referência a partir das linhas da sua consulta na seção 6."""
    if codigo in ("R06", "R07"):
        return [v for linha in linhas for v in (linha["nome_municipio"], linha["valor"],
                                                linha["participacao_percentual"])]
    if codigo == "R09":
        por_ano = {int(linha["ano"]): linha["participacao_percentual"] for linha in linhas}
        return [por_ano.get(2010), por_ano.get(2023)]
    if len(linhas) != 1:
        raise ValueError(f"{codigo}: a consulta devolveu {len(linhas)} linhas (esperada 1)")
    return list(linhas[0].values())


def valores_sql(engine: Engine, consultas: Mapping[str, str]) -> dict[str, dict[str, object]]:
    """Roda as consultas de referência (bed_readonly, READ ONLY) e normaliza os valores."""
    saida = {}
    with transacao_somente_leitura(engine) as conexao:
        for codigo in CODIGOS:
            linhas = [dict(m) for m in conexao.execute(text(consultas[codigo])).mappings()]
            saida[codigo] = _valores_por_componente(codigo, brutos_sql(codigo, linhas))
    return saida


# -- lado Streamlit -------------------------------------------------------------------------------

def brutos_streamlit(ler: Callable[..., pd.DataFrame]) -> dict[str, list[object]]:
    """Valores brutos como as páginas do app os calculam, com o filtro padrão.

    `ler(funcao, *args)` devolve o DataFrame de uma função de analise.consultas já com os tipos
    normalizados (como dashboard.dados.ler, sem o cache).
    """
    from brasil_em_dados.analise import calculos as ca
    from brasil_em_dados.analise import consultas as q
    from brasil_em_dados.dashboard import calculos as c
    from brasil_em_dados.dashboard.filtros import ANO_PADRAO, MUNICIPIO_PADRAO

    def serie(indicador: str) -> pd.DataFrame:
        return c.serie_territorio(ler(q.agregado, "estado", indicador),
                                  ler(q.agregado, "regiao_intermediaria", indicador), None)

    def top3(indicador: str, ano: int) -> list[object]:
        maiores = ca.top_n(ler(q.participacao, indicador, ano), "valor", 15).head(3)  # POP1, ECO1
        return [v for _, r in maiores.iterrows()
                for v in (r["nome_municipio"], r["valor"], r["participacao_percentual"])]

    estimativa = serie("pop_estimada")
    ano_2012 = estimativa[estimativa["ano"] == 2012].iloc[0]  # POP4
    pop3 = c.variacao_censo_territorios(ler(q.agregado, "regiao_intermediaria", "pop_censo"),
                                        ler(q.agregado, "estado", "pop_censo"))
    censo = ler(q.variacao_censo)
    floripa = censo[censo["cod_municipio"] == MUNICIPIO_PADRAO].iloc[0]  # PER1 (Florianópolis)
    itajai = ler(q.participacao_serie, "pib_corrente")
    itajai = itajai[itajai["cod_municipio"] == ITAJAI].set_index("ano")["participacao_percentual"]
    resumo = c.resumo_censo(censo)  # POP2
    painel = ler(q.painel, ANO_PADRAO)  # ECO3
    maior = ca.extremos(painel, "pib_per_capita_reais", 10).iloc[0]
    saltos = c.saltos_pib(ler(q.variacao_anual, "pib_corrente"))  # ECO4
    bases = c.variacoes_entre_bases(ler(q.variacao_anual, "pop_estimada")).set_index("pares")

    def entre_bases(rotulo: str) -> list[object]:
        linha = bases.loc[rotulo]
        return [linha["municipios"], linha["com_variacao"], int(linha["comparaveis"]) > 0]

    return {
        "R01": [c.valor_no_ano(serie("pop_censo"), 2022)],             # VG1
        "R02": [pop3.iloc[0]["censo_2010"]],                           # POP3, linha do estado
        "R03": [c.valor_no_ano(serie("pib_corrente"), 2023)],          # VG1, VG2
        "R04": [c.valor_no_ano(serie("pib_corrente"), 2010)],          # VG2
        "R05": [ano_2012["valor"], ano_2012["municipios_somados"], ano_2012["municipios_excluidos"]],
        "R06": top3("pop_censo", 2022),
        "R07": top3("pib_corrente", ANO_PADRAO),
        "R08": [floripa["pop_censo_2010"], floripa["pop_censo_2022"], floripa["variacao_percentual"]],
        "R09": [itajai.get(2010), itajai.get(2023)],                   # ECO2, PER5, CMP1
        "R10": [resumo["comparaveis"], resumo["perderam"]],
        "R11": [maior["nome_municipio"], maior["pib_per_capita_reais"]],
        "R12": [c.mediana(painel["pib_per_capita_reais"]),
                int(painel["pib_per_capita_reais"].notna().sum())],
        "R13": [len(saltos), saltos["cod_municipio"].nunique()],
        "R14": entre_bases("2012→2013"),
        "R15": entre_bases("2017→2018"),
    }


def valores_streamlit(engine: Engine) -> dict[str, dict[str, object]]:
    """Valores do app (caminho das páginas, sem cache), normalizados para comparar."""
    # Fora do `streamlit run`, cada st.cache_data avisa "No runtime found"; é esperado aqui. O
    # Streamlit configura os próprios loggers ao ser importado, então o nível vem depois disso.
    import streamlit  # noqa: F401

    logger_cache = logging.getLogger("streamlit.runtime.caching.cache_data_api")
    nivel_anterior = logger_cache.level
    logger_cache.setLevel(logging.ERROR)
    try:
        from brasil_em_dados.dashboard.dados import normalizar_tipos
    finally:
        logger_cache.setLevel(nivel_anterior)

    def ler(funcao: Callable[..., pd.DataFrame], *args: object) -> pd.DataFrame:
        return normalizar_tipos(funcao(engine, *args))

    brutos = brutos_streamlit(ler)
    return {codigo: _valores_por_componente(codigo, brutos[codigo]) for codigo in CODIGOS}


# -- comparação -----------------------------------------------------------------------------------

def comparar(sql: Mapping[str, Mapping[str, object]],
             app: Mapping[str, Mapping[str, object]]) -> list[Linha]:
    """Uma linha por componente, na ordem R01–R15."""
    return [Linha(codigo, nome, tipo, sql[codigo].get(nome), app[codigo].get(nome))
            for codigo in CODIGOS for nome, tipo in COMPONENTES[codigo]]


def _texto(valor: object) -> str:
    """Valor como aparece na tabela do relatório (NULL para ausência)."""
    return "NULL" if valor is None else str(valor)


def relatorio_markdown(linhas: list[Linha]) -> str:
    """Resumo e tabela da comparação (valores normalizados, não o texto formatado do app)."""
    divergentes = sorted({l.codigo for l in linhas if not l.confere})
    resumo = (f"{len(CODIGOS) - len(divergentes)} de {len(CODIGOS)} referências conferem "
              f"({sum(l.confere for l in linhas)} de {len(linhas)} componentes).")
    if divergentes:
        resumo += f" Divergem: {', '.join(divergentes)}."
    tabela = ["| # | componente | SQL | Streamlit | confere |", "|---|---|---|---|---|"]
    tabela += [f"| {l.codigo} | {l.componente} | {_texto(l.sql)} | {_texto(l.streamlit)} | "
               f"{'sim' if l.confere else 'NÃO'} |" for l in linhas]
    return resumo + "\n\n" + "\n".join(tabela)


def conferir(engine: Engine, consultas: Mapping[str, str]) -> list[Linha]:
    """SQL × Streamlit para R01–R15."""
    return comparar(valores_sql(engine, consultas), valores_streamlit(engine))


def main() -> int:
    """Imprime a comparação SQL × Streamlit (python -m brasil_em_dados.verificacao.referencias).

    Códigos de saída: 0, tudo confere; 1, alguma referência diverge; 2, falha de conexão ou de
    configuração do banco (o log traz só o tipo do erro e o SQLSTATE, sem host, usuário ou banco).
    A tabela vai para a saída padrão porque é o resultado do comando, não um log.
    """
    from brasil_em_dados import db
    from brasil_em_dados.logs import configurar_logging
    from brasil_em_dados.verificacao.ferramentas import ler_catalogo
    from brasil_em_dados.verificacao.seguranca import proteger_logs, segredos_do_banco

    configurar_logging()
    proteger_logs(segredos_do_banco(db.ler_ambiente()))  # nada de senha nos logs
    consultas = {c.nome.upper(): c.sql for c in ler_catalogo(PASTA_REFERENCIAS).values()}
    try:
        engine = db.engine_readonly()
        try:
            linhas = conferir(engine, consultas)
        finally:
            engine.dispose()
    except db.ERROS_DE_CONEXAO as exc:
        logger.error("Falha ao ler a GOLD (%s, SQLSTATE %s); detalhes omitidos.",
                     type(exc).__name__, db.sqlstate(exc))
        return 2
    print(relatorio_markdown(linhas))
    return 0 if all(l.confere for l in linhas) else 1



if __name__ == "__main__":
    raise SystemExit(main())
