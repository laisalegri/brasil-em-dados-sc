"""Gera as páginas PBIR do relatório Brasil em Dados SC (cartão D35).

ATENÇÃO: depois da geração inicial, o PBIP salvo no Power BI Desktop é a versão de referência
(decisão D35). Este script APAGA todas as páginas e as escreve de novo, então desfaz os ajustes
feitos no Desktop e as correções feitas direto nos visual.json (ex.: ECO4, POP2 e o preenchimento
dos cartões, em 26/11/2026). Não rode sobre o PBIP atual sem antes passar esses ajustes para o
código e conferir a diferença com o git.

Uso (da raiz do repositório, com o Power BI Desktop FECHADO):

    python scripts/powerbi/gerar_pbir.py dashboards/powerbi/BrasilEmDadosSC.Report \
        dashboards/powerbi/BrasilEmDadosSC.SemanticModel

- Apaga as páginas existentes em definition/pages/ e escreve, nesta ordem: Início, Visão geral,
  População, Economia, Perfil do município e Sobre os dados (page.json, visuals/<v>/visual.json e
  pages.json), seguindo docs/dashboards.md e o app Streamlit.
- Textos fixos de aviso e o rodapé são lidos das medidas 'Aviso ...' e 'Rodapé' do Medidas.tmdl,
  para ficarem idênticos aos do Streamlit (textos.py).
- Rode antes ajustar_medidas_tmdl.py (medidas de exibição e das páginas Início/Sobre) e depois
  verificar_pbir.py (JSON, schema oficial e referências ao modelo).
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

REPORT = Path(sys.argv[1])
MODELO = Path(sys.argv[2])
PAGES = REPORT / "definition" / "pages"

SCHEMA_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
SCHEMA_PAGES = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"
SCHEMA_VISUAL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.4.0/schema.json"

# Paleta do Streamlit/notebooks (analise/graficos.py)
AZUL, LARANJA, CINZA = "#2a78d6", "#eb6834", "#a3a29d"
TEXTO, TEXTO2 = "#0b0b0b", "#52514e"
CORES_BASES = {"ate_2012": CINZA, "2013_2017": AZUL, "desde_2018": LARANJA}
BILHAO = 1_000_000_000

M = "Medidas"
DIM = "gold dim_municipio"
AGR = "gold agregado_regiao_ano"
PART = "gold participacao_estadual"
PAINEL = "gold painel_municipio_ano"
VAR = "gold variacao_anual"
GRADE = "gold grade_indicador_municipio_ano"
FT = "Filtro territorio"
LARGURA = 1280
MARGEM = 24
W = LARGURA - 2 * MARGEM

# Nomes exibidos para colunas usadas sem rótulo próprio (nada de nome_municipio na tela)
NOMES_AMIGAVEIS = {
    "nome_municipio": "Município", "nome_regiao_intermediaria": "Região intermediária",
    "ano": "Ano", "ano_anterior": "Ano anterior", "cod_serie": "Série", "fonte": "Fonte",
    "codigo_indicador": "Indicador", "tipo_medida": "Tipo de medida", "unidade": "Unidade",
    "status": "Status",
}


# -- textos das medidas de aviso (TMDL) ---------------------------------------------------------

def textos_aviso() -> dict[str, str]:
    """Lê as medidas de texto fixo (Aviso ..., Rodapé) do Medidas.tmdl."""
    txt = (MODELO / "definition" / "tables" / "Medidas.tmdl").read_text(encoding="utf-8-sig")
    saida = {}
    for m in re.finditer(r"^\tmeasure (?:'([^']+)'|(\S+)) = \"((?:[^\"]|\"\")*)\"\s*$", txt, flags=re.M):
        saida[m.group(1) or m.group(2)] = m.group(3).replace('""', '"')
    return saida


AVISOS = textos_aviso()


def aviso(nome: str) -> str:
    return AVISOS[nome]


# -- expressões da consulta semântica ------------------------------------------------------------

def lit(valor) -> dict:
    if isinstance(valor, bool):
        v = "true" if valor else "false"
    elif isinstance(valor, int):
        v = f"{valor}L"
    elif isinstance(valor, float):
        v = f"{int(valor)}D" if valor.is_integer() else f"{valor}D"
    else:
        v = "'" + str(valor).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": v}}}


def cor(hexa: str) -> dict:
    return {"solid": {"color": lit(hexa)}}


def medida(nome: str) -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Entity": M}}, "Property": nome}}


def coluna(tabela: str, nome: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": tabela}}, "Property": nome}}


def _partes(campo: dict) -> tuple[str, str, str]:
    chave = "Measure" if "Measure" in campo else "Column"
    return chave, campo[chave]["Expression"]["SourceRef"]["Entity"], campo[chave]["Property"]


def proj(campo: dict, rotulo: str | None = None) -> dict:
    chave, ent, prop = _partes(campo)
    p = {"field": campo, "queryRef": f"{ent}.{prop}", "nativeQueryRef": prop}
    rotulo = rotulo or (NOMES_AMIGAVEIS.get(prop) if chave == "Column" else None)
    if rotulo:
        p["displayName"] = rotulo
    return p


def qref(campo: dict) -> str:
    _, ent, prop = _partes(campo)
    return f"{ent}.{prop}"


def _src(campo: dict, alias: str) -> dict:
    chave, _, prop = _partes(campo)
    return {chave: {"Expression": {"SourceRef": {"Source": alias}}, "Property": prop}}


def _ent(campo: dict) -> str:
    return _partes(campo)[1]


# -- filtros -------------------------------------------------------------------------------------

_contador = {"f": 0}


def _nome_filtro() -> str:
    _contador["f"] += 1
    return f"filtro{_contador['f']:03d}"


def filtro_topn(categoria: dict, ordem: dict, n: int) -> dict:
    """Top N da categoria pela medida (filtro de visual)."""
    return {
        "name": _nome_filtro(),
        "field": categoria,
        "type": "TopN",
        "filter": {
            "Version": 2,
            "From": [
                {"Name": "subquery", "Expression": {"Subquery": {"Query": {
                    "Version": 2,
                    "From": [{"Name": "c", "Entity": _ent(categoria), "Type": 0},
                             {"Name": "m", "Entity": _ent(ordem), "Type": 0}],
                    "Select": [dict(_src(categoria, "c"), Name="field")],
                    "OrderBy": [{"Direction": 2, "Expression": _src(ordem, "m")}],
                    "Top": n}}}, "Type": 2},
                {"Name": "c", "Entity": _ent(categoria), "Type": 0},
            ],
            "Where": [{"Condition": {"In": {
                "Expressions": [_src(categoria, "c")],
                "Table": {"SourceRef": {"Source": "subquery"}}}}}],
        },
        "howCreated": "User",
    }


def _comparacao(campo: dict, alias: str, valor, tipo: int = 0) -> dict:
    return {"Comparison": {"ComparisonKind": tipo, "Left": _src(campo, alias),
                           "Right": {"Literal": lit(valor)["expr"]["Literal"]}}}


def filtro_medida_igual(campo: dict, valores: list) -> dict:
    """Filtro avançado: medida = valor (ou um dos valores)."""
    cond = _comparacao(campo, "m", valores[0])
    for v in valores[1:]:
        cond = {"Or": {"Left": cond, "Right": _comparacao(campo, "m", v)}}
    return {
        "name": _nome_filtro(),
        "field": campo,
        "type": "Advanced",
        "filter": {"Version": 2, "From": [{"Name": "m", "Entity": _ent(campo), "Type": 0}],
                   "Where": [{"Condition": cond}]},
        "howCreated": "User",
    }


def filtro_valores(campo: dict, valores: list) -> dict:
    return {
        "name": _nome_filtro(),
        "field": campo,
        "type": "Categorical",
        "filter": {"Version": 2, "From": [{"Name": "t", "Entity": _ent(campo), "Type": 0}],
                   "Where": [{"Condition": {"In": {
                       "Expressions": [_src(campo, "t")],
                       "Values": [[lit(v)["expr"]] for v in valores]}}}]},
        "howCreated": "User",
    }


def filtro_selecao(campo: dict, valores: list) -> dict:
    """Definição de filtro (sem container) para o estado salvo de uma segmentação."""
    return {"Version": 2, "From": [{"Name": "t", "Entity": _ent(campo), "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [_src(campo, "t")],
                "Values": [[lit(v)["expr"]] for v in valores]}}}]}


# -- objetos de contêiner comuns ----------------------------------------------------------------

def conteiner(titulo: dict | None, moldura: bool = True) -> dict:
    """Título (ou sem título), subtítulo automático desligado e, se pedido, sem moldura/fundo."""
    obj = {"title": [{"properties": titulo or {"show": lit(False)}}],
           "subTitle": [{"properties": {"show": lit(False)}}]}
    if not moldura:
        obj["border"] = [{"properties": {"show": lit(False)}}]
        obj["background"] = [{"properties": {"show": lit(False)}}]
        obj["dropShadow"] = [{"properties": {"show": lit(False)}}]
    return obj


def titulo_medida(nome: str, tamanho: float = 12.0) -> dict:
    return {"show": lit(True), "text": {"expr": medida(nome)}, "titleWrap": lit(True),
            "fontSize": lit(tamanho), "fontColor": cor(TEXTO), "bold": lit(True)}


def titulo_fixo(texto: str, tamanho: float = 10.0, cor_texto: str = TEXTO2, negrito=False) -> dict:
    return {"show": lit(True), "text": lit(texto), "titleWrap": lit(True), "fontSize": lit(tamanho),
            "fontColor": cor(cor_texto), "bold": lit(negrito)}


# -- página e visuais ----------------------------------------------------------------------------

class Pagina:
    def __init__(self, nome: str, titulo: str):
        self.nome = nome
        self.titulo = titulo
        self.visuais: list[dict] = []
        self.y = MARGEM
        self.z = 0

    def _add(self, nome: str, x: float, y: float, w: float, h: float, visual: dict,
             filtros: list | None = None) -> None:
        self.z += 1
        cont = {
            "$schema": SCHEMA_VISUAL,
            "name": f"{self.nome}_{nome}"[:50],
            "position": {"x": x, "y": y, "z": self.z * 1000, "width": w, "height": h,
                         "tabOrder": self.z * 1000},
            "visual": visual,
        }
        if filtros:
            cont["filterConfig"] = {"filters": filtros}
        self.visuais.append(cont)

    # ---- blocos de texto fixo
    def texto(self, nome, x, y, w, h, linhas: list[tuple[str, dict]]) -> None:
        paragrafos = [{"textRuns": [{"value": valor, "textStyle": estilo}]} for valor, estilo in linhas]
        self._add(nome, x, y, w, h, {
            "visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": paragrafos}}]},
            "visualContainerObjects": conteiner(None, moldura=False),
            "drillFilterOtherVisuals": True,
        })

    def titulo_secao(self, codigo: str, pergunta: str) -> None:
        self.texto(f"{codigo.lower()}_secao", MARGEM, self.y, W, 40,
                   [(f"{codigo} · {pergunta}", {"fontWeight": "bold", "fontSize": "14pt",
                                                 "color": TEXTO})])
        self.y += 44

    def avisos(self, nome: str, nomes_aviso: list[str], x=MARGEM, w=None) -> None:
        w = w or W
        linhas = [("Aviso: " + aviso(n), {"fontSize": "10pt", "color": TEXTO2, "fontStyle": "italic"})
                  for n in nomes_aviso]
        h = 24 * len(nomes_aviso) + 12 * sum(len(aviso(n)) > 170 for n in nomes_aviso) + 8
        self.texto(nome, x, self.y, w, h, linhas)
        self.y += h + 8

    # ---- cartões (sempre medidas de texto: 'sem dado' em vez de '(Em branco)')
    def cartao(self, nome, x, y, w, h, nome_medida: str, titulo: str | None = None,
               titulo_dinamico: str | None = None, texto=False, tamanho=20.0) -> None:
        objetos = {
            "labels": [{"properties": {"fontSize": lit(float(11 if texto else tamanho)),
                                       "color": cor(TEXTO2 if texto else TEXTO)}}],
            "categoryLabels": [{"properties": {"show": lit(False)}}],
            "wordWrap": [{"properties": {"show": lit(True)}}],
        }
        if titulo_dinamico:
            tit = titulo_medida(titulo_dinamico, 10.0) | {"fontColor": cor(TEXTO2), "bold": lit(False)}
        elif titulo:
            tit = titulo_fixo(titulo)
        else:
            tit = None
        self._add(nome, x, y, w, h, {
            "visualType": "card",
            "query": {"queryState": {"Values": {"projections": [proj(medida(nome_medida))]}}},
            "objects": objetos,
            "visualContainerObjects": conteiner(tit, moldura=not texto),
            "drillFilterOtherVisuals": True,
        })

    def texto_dinamico(self, nome: str, nome_medida: str, h=44) -> None:
        """Cartão sem moldura com uma medida de texto (aviso condicional; vazio quando não se aplica)."""
        self.cartao(nome, MARGEM, self.y, W, h, nome_medida, texto=True)
        self.y += h + 6

    # ---- segmentações
    def segmentacao(self, nome, x, y, w, h, campo: dict, titulo: str, grupo: str | None,
                    padrao: list | None = None) -> None:
        objetos = {
            "data": [{"properties": {"mode": lit("Dropdown")}}],
            "selection": [{"properties": {"singleSelect": lit(True)}}],
            "header": [{"properties": {"show": lit(True), "text": lit(titulo),
                                       "fontColor": cor(TEXTO2)}}],
        }
        if padrao is not None:
            objetos["general"] = [{"properties": {"filter": {"filter": filtro_selecao(campo, padrao)}}}]
        visual = {
            "visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": [proj(campo, titulo)]}}},
            "objects": objetos,
            "visualContainerObjects": conteiner(None),
            "drillFilterOtherVisuals": True,
        }
        if grupo:
            visual["syncGroup"] = {"groupName": grupo, "fieldChanges": True, "filterChanges": True}
        self._add(nome, x, y, w, h, visual)

    def cabecalho(self, subtitulo: str, medida_titulo: str | None = None, filtros=True) -> None:
        largura_titulo = 700 if filtros else W
        if medida_titulo:
            self.cartao("titulo", MARGEM, self.y, largura_titulo, 56, medida_titulo, tamanho=24.0)
        else:
            self.texto("titulo", MARGEM, self.y, largura_titulo, 56,
                       [(self.titulo, {"fontWeight": "bold", "fontSize": "24pt", "color": TEXTO})])
        self.texto("subtitulo", MARGEM, self.y + 56, largura_titulo, 48,
                   [(subtitulo, {"fontSize": "11pt", "color": TEXTO2, "fontStyle": "italic"})])
        if filtros:
            x0 = 760
            self.segmentacao("seg_regiao", x0, self.y, 160, 72, coluna(FT, "Região intermediária"),
                             "Região (vazio = SC)", "Regiao")
            self.segmentacao("seg_municipio", x0 + 168, self.y, 200, 72, coluna(FT, "Município"),
                             "Município", "Municipio", ["Florianópolis"])
            self.segmentacao("seg_ano", x0 + 376, self.y, 120, 72, coluna("Anos", "Ano"),
                             "Ano", "Ano", [2023])
        self.y += 112

    def seletor_censo(self, nome: str) -> None:
        """Seletor local de Censo (2010 ou 2022), não sincronizado."""
        self.segmentacao(nome, MARGEM, self.y, 180, 64, coluna("Ano Censo", "Ano Censo"),
                         "Censo", None, [2022])
        self.y += 70

    # ---- gráficos
    def grafico(self, nome, tipo: str, x, y, w, h, categoria: dict, valores: list[tuple[dict, str]],
                medida_titulo: str, eixo_valor: str, cor_medida: str | None = None,
                cores_series: dict[str, str] | None = None, ordenar: dict | None = None,
                ascendente=False, filtros=None, dicas: list[tuple[dict, str]] | None = None,
                legenda=False, rotulos=True, eixo_inicio: float | None = None,
                eixo_fim: float | None = None, unidades: int | None = None, categorico=False,
                referencia: tuple[str, str] | None = None) -> None:
        estado = {"Category": {"projections": [proj(categoria)]},
                  "Y": {"projections": [proj(c, r) for c, r in valores]}}
        if dicas:
            estado["Tooltips"] = {"projections": [proj(c, r) for c, r in dicas]}
        consulta = {"queryState": estado}
        if ordenar is not None:
            consulta["sortDefinition"] = {"sort": [{"field": ordenar,
                                                    "direction": "Ascending" if ascendente else "Descending"}],
                                          "isDefaultSort": False}
        eixo = {"showAxisTitle": lit(True), "titleText": lit(eixo_valor)}
        if eixo_inicio is not None:
            eixo["start"] = lit(float(eixo_inicio))
        if eixo_fim is not None:
            eixo["end"] = lit(float(eixo_fim))
        rot = {"show": lit(rotulos)}
        if unidades:
            eixo["labelDisplayUnits"] = lit(float(unidades))
            rot["labelDisplayUnits"] = lit(float(unidades))
            rot["labelPrecision"] = lit(1)
        eixo_cat = {"showAxisTitle": lit(False)}
        if categorico:
            eixo_cat["axisType"] = lit("Categorical")
        objetos = {
            "valueAxis": [{"properties": eixo}],
            "categoryAxis": [{"properties": eixo_cat}],
            "legend": [{"properties": {"show": lit(legenda)}}],
            "labels": [{"properties": rot}],
        }
        pontos = []
        if cor_medida:
            pontos.append({"properties": {"fill": {"solid": {"color": {"expr": medida(cor_medida)}}}},
                           "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}})
        for ref, hexa in (cores_series or {}).items():
            pontos.append({"properties": {"fill": cor(hexa)}, "selector": {"metadata": ref}})
        if pontos:
            objetos["dataPoint"] = pontos
        if tipo == "lineChart":
            objetos["lineStyles"] = [{"properties": {"lineChartType": lit("linear"),
                                                     "showMarker": lit(True)}}]
        if referencia:
            nome_ref, rotulo_ref = referencia
            objetos["y1AxisReferenceLine"] = [{"properties": {
                "show": lit(True), "displayName": lit(rotulo_ref), "value": {"expr": medida(nome_ref)},
                "lineColor": cor(TEXTO), "style": lit("dashed"), "transparency": lit(0.0),
                "dataLabelShow": lit(True), "dataLabelText": lit("Name"), "dataLabelColor": cor(TEXTO),
            }, "selector": {"id": "1"}}]
        self._add(nome, x, y, w, h, {
            "visualType": tipo,
            "query": consulta,
            "objects": objetos,
            "visualContainerObjects": conteiner(titulo_medida(medida_titulo)),
            "drillFilterOtherVisuals": True,
        }, filtros)

    def tabela(self, nome, x, y, w, h, campos: list[tuple[dict, str | None]], titulo: str | None = None,
               medida_titulo: str | None = None, ordenar: dict | None = None, ascendente=False,
               filtros=None) -> None:
        consulta = {"queryState": {"Values": {"projections": [proj(c, r) for c, r in campos]}}}
        if ordenar is not None:
            consulta["sortDefinition"] = {"sort": [{"field": ordenar,
                                                    "direction": "Ascending" if ascendente else "Descending"}],
                                          "isDefaultSort": False}
        tit = titulo_medida(medida_titulo, 11.0) if medida_titulo else titulo_fixo(titulo or "", 11.0, TEXTO, True)
        self._add(nome, x, y, w, h, {
            "visualType": "tableEx",
            "query": consulta,
            "objects": {
                "total": [{"properties": {"totals": lit(False)}}],
                "columnHeaders": [{"properties": {"wordWrap": lit(True)}}],
                "values": [{"properties": {"wordWrap": lit(True)}}],
            },
            "visualContainerObjects": conteiner(tit),
            "drillFilterOtherVisuals": True,
        }, filtros)

    def rodape(self) -> None:
        self.texto("rodape", MARGEM, self.y + 8, W, 32,
                   [(aviso("Rodapé"), {"fontSize": "9pt", "color": TEXTO2})])
        self.y += 48

    def gravar(self) -> None:
        pasta = PAGES / self.nome
        (pasta / "visuals").mkdir(parents=True, exist_ok=True)
        page = {"$schema": SCHEMA_PAGE, "name": self.nome, "displayName": self.titulo,
                "displayOption": "FitToWidth", "height": int(self.y + MARGEM), "width": LARGURA}
        (pasta / "page.json").write_text(json.dumps(page, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
        for v in self.visuais:
            dv = pasta / "visuals" / v["name"]
            dv.mkdir(parents=True, exist_ok=True)
            (dv / "visual.json").write_text(json.dumps(v, ensure_ascii=False, indent=2) + "\n",
                                            encoding="utf-8")


ESTILO_TEXTO = {"fontSize": "11pt", "color": TEXTO}
ESTILO_NEGRITO = {"fontSize": "12pt", "color": TEXTO, "fontWeight": "bold"}


# ======================= Início =================================================================

def inicio() -> Pagina:
    """Página inicial (dashboards/streamlit/app.py: inicio)."""
    p = Pagina("inicio", "Início")
    p.texto("titulo", MARGEM, p.y, W, 56,
            [("Brasil em Dados SC", {"fontWeight": "bold", "fontSize": "26pt", "color": TEXTO})])
    p.y += 60
    p.texto_dinamico("abertura", "INI Texto de abertura", 36)
    p.texto_dinamico("pergunta", "INI Pergunta central", 52)
    p.texto("navegacao", MARGEM, p.y, W, 210, [
        ("Páginas", ESTILO_NEGRITO),
        ("• Visão geral: o tamanho do estado, a concentração e o peso das regiões.", ESTILO_TEXTO),
        ("• População: quem concentra moradores e como a população variou entre os Censos 2010 e 2022.",
         ESTILO_TEXTO),
        ("• Economia: PIB nominal, participação no PIB do estado e PIB per capita.", ESTILO_TEXTO),
        ("• Perfil do município: um município de cada vez, escolhido no filtro Município.", ESTILO_TEXTO),
        ("• Sobre os dados: fontes, cobertura e regras de leitura.", ESTILO_TEXTO),
        ("A página Comparação existe só no app Streamlit (decisão D35). Os filtros Região, Município e "
         "Ano ficam no topo de cada página e valem para todas elas.",
         {"fontSize": "10pt", "color": TEXTO2, "fontStyle": "italic"}),
    ])
    p.y += 218
    p.texto("como_ler", MARGEM, p.y, W, 32, [("Como ler os números", ESTILO_NEGRITO)])
    p.y += 36
    p.avisos("avisos", ["Aviso PIB nominal", "Aviso PIB per capita", "Aviso Censo oficial",
                        "Aviso quebras da estimativa"])
    p.rodape()
    return p


# ======================= Visão geral ============================================================

def visao_geral() -> Pagina:
    p = Pagina("visao_geral", "Visão geral")
    p.cabecalho("Como os municípios de SC se diferenciam em população e dimensão econômica, e como "
                "esses indicadores evoluíram entre 2010 e 2023?")

    p.titulo_secao("VG1", "Qual o tamanho de Santa Catarina (ou da região escolhida)?")
    cw = (W - 32) / 3
    p.cartao("vg1a", MARGEM, p.y, cw, 96, "VG1a População (Censo 2022) (exibição)",
             titulo="População (Censo 2022)")
    p.cartao("vg1b", MARGEM + cw + 16, p.y, cw, 96, "VG1b PIB nominal no ano (exibição)",
             titulo_dinamico="VG1b Rótulo")
    p.cartao("vg1c", MARGEM + 2 * (cw + 16), p.y, cw, 96, "VG1c Municípios (exibição)",
             titulo="Municípios")
    p.y += 104
    p.texto_dinamico("vg1b_exato", "VG1b Valor exato (texto)", 36)
    p.avisos("vg1_avisos", ["Aviso PIB nominal"])

    p.titulo_secao("VG2", "Como o PIB nominal evoluiu de 2010 a 2023?")
    ano_agr = coluna(AGR, "ano")
    pib = medida("VG2 PIB nominal (valores correntes)")
    varn = medida("VG2 Variação nominal sobre o ano anterior")
    p.grafico("vg2", "clusteredColumnChart", MARGEM, p.y, 780, 400, ano_agr,
              [(pib, "PIB nominal (R$, valores correntes)")], "VG2 Título",
              "PIB nominal (R$ bi, valores correntes)", cor_medida="VG2 Cor do ano",
              ordenar=ano_agr, ascendente=True, unidades=BILHAO, categorico=True,
              dicas=[(varn, "Variação nominal sobre o ano anterior")])
    p.tabela("vg2_dados", MARGEM + 796, p.y, W - 796, 400,
             [(ano_agr, "Ano"), (pib, "PIB nominal (R$)"), (varn, "Variação nominal sobre o ano anterior")],
             titulo="Dados (VG2)", ordenar=ano_agr, ascendente=True)
    p.y += 408
    p.avisos("vg2_avisos", ["Aviso PIB nominal", "Aviso revisão do PIB"])

    p.titulo_secao("VG3", "Quanto os 10 maiores municípios concentram?")
    vg3a = medida("VG3a Participação dos 10 maiores (Censo 2022)")
    vg3b = medida("VG3b Participação dos 10 maiores (PIB nominal no ano)")
    p._add("vg3", MARGEM, p.y, 780, 220, {
        "visualType": "clusteredBarChart",
        "query": {"queryState": {"Y": {"projections": [
            proj(vg3a, "População (Censo 2022)"), proj(vg3b, "PIB nominal (ano do filtro)")]}}},
        "objects": {
            "valueAxis": [{"properties": {"showAxisTitle": lit(True),
                                          "titleText": lit("Participação dos 10 maiores no total de SC (%)"),
                                          "start": lit(0.0), "end": lit(100.0)}}],
            "legend": [{"properties": {"show": lit(True)}}],
            "labels": [{"properties": {"show": lit(True)}}],
            "dataPoint": [{"properties": {"fill": cor(AZUL)}, "selector": {"metadata": qref(vg3a)}},
                          {"properties": {"fill": cor(LARANJA)}, "selector": {"metadata": qref(vg3b)}}],
        },
        "visualContainerObjects": conteiner(titulo_medida("VG3 Título")),
        "drillFilterOtherVisuals": True,
    })
    p.cartao("vg3_metade", MARGEM + 796, p.y, W - 796, 220, "VG3 Texto metade", texto=True)
    p.y += 228
    p.avisos("vg3_avisos", ["Aviso distribuição do PIB"])

    p.titulo_secao("VG4", "Quais regiões pesam mais no PIB que na população?")
    p.seletor_censo("vg4_censo")
    reg = coluna(DIM, "nome_regiao_intermediaria")
    pib_r = medida("VG4 Participação no PIB nominal (%)")
    pop_r = medida("VG4 Participação na população Censo (%)")
    p.grafico("vg4", "clusteredColumnChart", MARGEM, p.y, W, 400, reg,
              [(pib_r, "Participação no PIB nominal (ano do seletor)"),
               (pop_r, "Participação na população (Censo do seletor)")],
              "VG4 Título", "Participação no total de SC (%)",
              cores_series={qref(pib_r): AZUL, qref(pop_r): CINZA}, ordenar=pib_r, legenda=True,
              dicas=[(medida("VG4 Diferença (p.p.)"), "Diferença (p.p.)")])
    p.y += 408
    p.avisos("vg4_avisos", ["Aviso sem per capita regional", "Aviso PIB nominal"])
    p.rodape()
    return p


# ======================= População ==============================================================

def populacao() -> Pagina:
    p = Pagina("populacao", "População")
    p.cabecalho("Quais municípios concentram a população e como ela variou entre os Censos de 2010 "
                "e 2022?")
    mun = coluna(DIM, "nome_municipio")

    p.titulo_secao("POP1", "Quais municípios têm mais moradores?")
    p.seletor_censo("pop1_censo")
    pop1 = medida("POP1 População (Censo)")
    part1 = medida("POP1 Participação no estado (%)")
    p.grafico("pop1", "clusteredBarChart", MARGEM, p.y, 680, 500, mun,
              [(pop1, "População (Censo, pessoas)")], "POP1 Título", "População (Censo, pessoas)",
              cor_medida="Cor destaque município", ordenar=pop1,
              filtros=[filtro_topn(mun, pop1, 15)],
              dicas=[(part1, "Participação no estado"), (medida("POP1 Situação"), "Situação")])
    p.tabela("pop1_dados", MARGEM + 696, p.y, W - 696, 500,
             [(mun, "Município"), (pop1, "População (Censo)"), (part1, "Participação no estado")],
             titulo="Dados (POP1): os 15 maiores, com % do estado", ordenar=pop1,
             filtros=[filtro_topn(mun, pop1, 15)])
    p.y += 508
    p.texto_dinamico("pop1_sem_censo", "POP1 Sem Censo (texto)")

    p.titulo_secao("POP2", "Quem mais ganhou e perdeu população entre os Censos?")
    cw = (W - 48) / 4
    for i, (m, t) in enumerate([("POP2 Municípios comparáveis", "Municípios comparáveis"),
                                ("POP2 Cresceram", "Cresceram"),
                                ("POP2 Perderam população", "Perderam população"),
                                ("POP2 Variação: mediana entre os municípios",
                                 "Variação: mediana entre os municípios")]):
        p.cartao(f"pop2_k{i}", MARGEM + i * (cw + 16), p.y, cw, 88, f"{m} (exibição)", titulo=t)
    p.y += 96
    vp, va = medida("POP2 Variação percentual"), medida("POP2 Variação absoluta")
    meia = (W - 16) / 2
    # 10 maiores ganhos + 10 maiores perdas (calculos.ganhos_e_perdas), do maior para o menor;
    # altura suficiente para as 20 barras sem rolagem
    p.grafico("pop2_pct", "clusteredBarChart", MARGEM, p.y, meia, 700, mun,
              [(vp, "Variação percentual")], "POP2 Título",
              "Variação entre os Censos 2010 e 2022 (%)", cor_medida="Cor destaque município",
              ordenar=vp, filtros=[filtro_medida_igual(medida("POP2 Entre os extremos (percentual)"), [1])],
              dicas=[(va, "Variação absoluta (pessoas)")])
    p.grafico("pop2_abs", "clusteredBarChart", MARGEM + meia + 16, p.y, meia, 700, mun,
              [(va, "Variação absoluta (pessoas)")], "POP2 Título",
              "Variação entre os Censos 2010 e 2022 (pessoas)", cor_medida="Cor destaque município",
              ordenar=va, filtros=[filtro_medida_igual(medida("POP2 Entre os extremos (absoluta)"), [1])],
              dicas=[(vp, "Variação percentual")])
    p.y += 708
    p.texto_dinamico("pop2_sem_var", "POP2 Sem variação (texto)")
    p.avisos("pop2_avisos", ["Aviso Laguna", "Aviso apurações do Censo 2022"])

    p.titulo_secao("POP3", "Que regiões cresceram mais entre os Censos?")
    reg = coluna(DIM, "nome_regiao_intermediaria")
    v3 = medida("POP3 Variação entre os Censos (%)")
    p.grafico("pop3", "clusteredBarChart", MARGEM, p.y, 640, 360, reg,
              [(v3, "Variação entre os Censos (%)")], "POP3 Título",
              "Variação da população entre os Censos 2010 e 2022 (%)", cor_medida="POP3 Cor da região",
              ordenar=v3)
    p.tabela("pop3_dados", MARGEM + 656, p.y, W - 656, 360,
             [(reg, "Região intermediária"), (medida("POP3 Censo 2010 (território)"), "Censo 2010"),
              (medida("POP3 Censo 2022 (território)"), "Censo 2022"), (v3, "Variação")],
             titulo="Dados (POP3)", ordenar=v3)
    p.y += 368
    p.avisos("pop3_avisos", ["Aviso Criciúma"])

    p.titulo_secao("POP4", "Como a estimativa anual de população evoluiu?")
    p.texto_dinamico("pop4_sem_est", "POP4 Sem estimativa (texto)", 36)
    ano_agr = coluna(AGR, "ano")
    b1 = medida("POP4 Estimativa – Base até 2012")
    b2 = medida("POP4 Estimativa – Base 2013–2017 (nova projeção)")
    b3 = medida("POP4 Estimativa – Base desde 2018 (revisão)")
    p.cartao("pop4_ano", MARGEM, p.y, 260, 88, "POP4 Estimativa no ano selecionado (exibição)",
             titulo="Estimativa no ano escolhido")
    p.texto("pop4_quebras", MARGEM, p.y + 96, 260, 120,
            [("Marcações (C8):", {"fontWeight": "bold", "fontSize": "10pt", "color": TEXTO2}),
             ("2013: quebra de série: nova projeção", {"fontSize": "10pt", "color": TEXTO2}),
             ("2018: revisão da projeção", {"fontSize": "10pt", "color": TEXTO2})])
    p.grafico("pop4", "lineChart", MARGEM + 276, p.y, W - 276, 400, ano_agr,
              [(b1, "Base até 2012"), (b2, "Base 2013–2017 (nova projeção)"),
               (b3, "Base desde 2018 (revisão)")], "POP4 Título", "População estimada (pessoas)",
              cores_series={qref(b1): CORES_BASES["ate_2012"], qref(b2): CORES_BASES["2013_2017"],
                            qref(b3): CORES_BASES["desde_2018"]},
              ordenar=ano_agr, ascendente=True, legenda=True, rotulos=False, categorico=True)
    p.y += 408
    p.avisos("pop4_avisos", ["Aviso quebras da estimativa", "Aviso dupla contagem 2012",
                             "Aviso Censo oficial"])
    p.tabela("pop4_dados", MARGEM, p.y, W, 360,
             [(ano_agr, "Ano"), (medida("POP4 Base da estimativa"), "Base da estimativa"),
              (b1, "Estimativa (base até 2012)"), (b2, "Estimativa (base 2013–2017)"),
              (b3, "Estimativa (base desde 2018)"), (medida("POP4 Municípios somados"), "Municípios somados"),
              (medida("POP4 Municípios excluídos"), "Municípios excluídos"),
              (medida("POP4 Aviso da linha"), "Aviso")],
             titulo="Dados (POP4)", ordenar=ano_agr, ascendente=True)
    p.y += 368
    p.tabela("pop4_bases", MARGEM, p.y, W, 190,
             [(medida("POP4 Pares 2012→2013"), "Pares 2012→2013"),
              (medida("POP4 Com variação 2012→2013"), "Com variação 2012→2013"),
              (medida("POP4 Motivo 2012→2013"), "Motivo 2012→2013"),
              (medida("POP4 Pares 2017→2018"), "Pares 2017→2018"),
              (medida("POP4 Com variação 2017→2018"), "Com variação 2017→2018"),
              (medida("POP4 Motivo 2017→2018"), "Motivo 2017→2018")],
             titulo="POP4 · variações entre bases (pares municipais)")
    p.y += 198
    p.avisos("pop4_aviso_2018", ["Aviso revisão 2018"])
    p.rodape()
    return p


# ======================= Economia ===============================================================

def economia() -> Pagina:
    p = Pagina("economia", "Economia")
    p.cabecalho("Quais municípios concentram o PIB, como a participação deles mudou e como se "
                "comparam em PIB per capita?")
    mun = coluna(DIM, "nome_municipio")

    p.titulo_secao("ECO1", "Quais municípios concentram o PIB?")
    pib = medida("ECO1 PIB nominal no ano")
    part = medida("ECO1 Participação no estado (%)")
    p.grafico("eco1", "clusteredBarChart", MARGEM, p.y, 640, 500, mun,
              [(pib, "PIB nominal (R$, valores correntes)")], "ECO1 Título",
              "PIB nominal no ano do filtro (R$ bi, valores correntes)", cor_medida="Cor destaque município",
              ordenar=pib, filtros=[filtro_topn(mun, pib, 15)], unidades=BILHAO,
              dicas=[(part, "Participação no estado")])
    p.tabela("eco1_dados", MARGEM + 656, p.y, W - 656, 500,
             [(mun, "Município"), (pib, "PIB nominal (R$)"), (part, "Participação no estado")],
             titulo="Dados (ECO1): os 15 maiores, com % do estado", ordenar=pib,
             filtros=[filtro_topn(mun, pib, 15)])
    p.y += 508
    p.avisos("eco1_avisos", ["Aviso PIB nominal", "Aviso distribuição do PIB"])

    p.titulo_secao("ECO2", "Quem ganhou e perdeu participação no PIB desde 2010?")
    p.texto_dinamico("eco2_2010", "ECO2 Aviso ano 2010", 36)
    p10, pano = medida("ECO2 Participação 2010"), medida("ECO2 Participação no ano")
    dif = medida("ECO2 Diferença (p.p.)")
    p.grafico("eco2", "clusteredBarChart", MARGEM, p.y, 640, 460, mun,
              [(p10, "Participação em 2010"), (pano, "Participação no ano do filtro")], "ECO2 Título",
              "Participação no PIB nominal de SC (%)", cores_series={qref(p10): CINZA, qref(pano): AZUL},
              ordenar=pano, filtros=[filtro_topn(mun, pib, 10)], legenda=True, rotulos=False,
              dicas=[(dif, "Diferença (p.p.)")])
    p.tabela("eco2_dados", MARGEM + 656, p.y, W - 656, 460,
             [(mun, "Município"), (p10, "Participação 2010"), (pano, "Participação no ano"),
              (dif, "Diferença")], titulo="Dados (ECO2): os 10 maiores do ano", ordenar=pano,
             filtros=[filtro_topn(mun, pib, 10)])
    p.y += 468
    p.avisos("eco2_avisos", ["Aviso participação", "Aviso PIB nominal"])

    p.titulo_secao("ECO3", "Como os municípios se comparam em PIB per capita?")
    p.cartao("eco3_mediana", MARGEM, p.y, 380, 88, "ECO3 PIB per capita: mediana entre os municípios (exibição)",
             titulo_dinamico="ECO3 Rótulo da mediana")
    p.cartao("eco3_n", MARGEM + 396, p.y, 240, 88, "ECO3 Municípios com valor (exibição)",
             titulo="Municípios com valor")
    p.texto("eco3_legenda", MARGEM + 652, p.y, W - 652, 88,
            [("Laranja: município escolhido; azul: os 10 maiores; cinza: os 10 menores. A linha "
              "tracejada é a mediana entre os municípios (não é o PIB per capita do estado nem da região).",
              {"fontSize": "10pt", "color": TEXTO2})])
    p.y += 96
    pc = medida("ECO3 PIB per capita no ano")
    p.grafico("eco3", "clusteredBarChart", MARGEM, p.y, W, 700, mun,
              [(pc, "PIB per capita (R$, publicado pelo IBGE)")], "ECO3 Título",
              "PIB per capita no ano do filtro (R$, publicado pelo IBGE)", cor_medida="ECO3 Cor",
              ordenar=pc, referencia=("ECO3 PIB per capita: mediana entre os municípios",
                                      "mediana entre os municípios"),
              filtros=[filtro_medida_igual(medida("ECO3 Grupo (10 maiores ou 10 menores)"),
                                           ["maior", "menor"])])
    p.y += 708
    p.avisos("eco3_avisos", ["Aviso PIB per capita", "Aviso denominador do per capita", "Aviso A1"])

    p.titulo_secao("ECO4", "Onde houve saltos anuais de PIB nominal acima de 50%?")
    p.cartao("eco4_k1", MARGEM, p.y, 300, 88, "ECO4 Variações acima de 50% em módulo (exibição)",
             titulo="Variações acima de 50% em módulo")
    p.cartao("eco4_k2", MARGEM + 316, p.y, 240, 88, "ECO4 Municípios com saltos (exibição)",
             titulo="Municípios")
    p.y += 96
    varp = coluna(VAR, "variacao_percentual")
    p.tabela("eco4", MARGEM, p.y, W, 480,
             [(medida("ECO4 Destaque"), " "), (coluna(VAR, "nome_municipio"), "Município"),
              (coluna(VAR, "ano_anterior"), "Ano anterior"), (coluna(VAR, "ano"), "Ano"),
              (coluna(VAR, "valor_anterior"), "PIB nominal no ano anterior (R$)"),
              (coluna(VAR, "valor"), "PIB nominal no ano (R$)"),
              (varp, "Variação nominal")],
             medida_titulo="ECO4 Título", ordenar=varp,
             filtros=[filtro_medida_igual(medida("ECO4 Salto na linha"), [1])])
    p.y += 488
    p.avisos("eco4_avisos", ["Aviso A1", "Aviso PIB nominal"])
    p.rodape()
    return p


# ======================= Perfil do município ====================================================

def perfil() -> Pagina:
    p = Pagina("perfil", "Perfil do município")
    p.cabecalho("Qual o retrato do município em população e PIB? (escolha o município no filtro)",
                medida_titulo="PER Título da página")
    p.texto_dinamico("per_ident", "PER Identificação", 36)
    p.texto_dinamico("per_instalacao", "PER Aviso instalação", 36)

    p.titulo_secao("PER1", "Qual o retrato do município?")
    cw = (W - 48) / 4
    for i, (m, t) in enumerate([("PER1 População (Censo 2010) (exibição)", "População (Censo 2010)"),
                                ("PER1 População (Censo 2022) (exibição)", "População (Censo 2022)"),
                                ("PER1 Variação entre os Censos (exibição)", "Variação entre os Censos"),
                                ("PER1 Posição em população (Censo 2022)", "Posição em população (Censo 2022)")]):
        p.cartao(f"per1_a{i}", MARGEM + i * (cw + 16), p.y, cw, 88, m, titulo=t)
    p.y += 96
    p.texto_dinamico("per1_motivo", "PER1 Motivo", 36)
    cw3 = (W - 32) / 3
    for i, (m, t) in enumerate([("PER1 PIB nominal no ano (exibição)", "PIB nominal (ano do filtro)"),
                                ("PER1 PIB per capita no ano (exibição)", "PIB per capita (ano do filtro)"),
                                ("PER1 Posição no PIB nominal", "Posição no PIB nominal (ano do filtro)")]):
        p.cartao(f"per1_b{i}", MARGEM + i * (cw3 + 16), p.y, cw3, 88, m, titulo=t)
    p.y += 96
    p.texto_dinamico("per1_exato", "PER1 Valor exato do PIB (texto)", 36)
    p.avisos("per1_avisos", ["Aviso PIB nominal", "Aviso PIB per capita"])

    ano_p = coluna(PAINEL, "ano")
    p.titulo_secao("PER2", "Como o PIB nominal do município evoluiu?")
    pib = medida("PER2 PIB nominal (valores correntes)")
    varp = medida("PER2 Variação nominal sobre o ano anterior")
    p.grafico("per2", "clusteredColumnChart", MARGEM, p.y, 780, 400, ano_p,
              [(pib, "PIB nominal (R$, valores correntes)")], "PER2 Título",
              "PIB nominal (R$, valores correntes)", cor_medida="PER Cor do ano (painel)", ordenar=ano_p,
              ascendente=True, categorico=True,
              dicas=[(varp, "Variação nominal sobre o ano anterior")])
    p.tabela("per2_dados", MARGEM + 796, p.y, W - 796, 400,
             [(ano_p, "Ano"), (pib, "PIB nominal (R$)"), (varp, "Variação nominal sobre o ano anterior")],
             titulo="Dados (PER2)", ordenar=ano_p, ascendente=True)
    p.y += 408
    p.texto_dinamico("per2_saltos", "PER2 Saltos acima de 50% (texto)", 52)
    p.avisos("per2_avisos", ["Aviso PIB nominal", "Aviso revisão do PIB"])

    p.titulo_secao("PER3", "Como a população do município evoluiu?")
    b1 = medida("PER3a Estimativa – Base até 2012")
    b2 = medida("PER3a Estimativa – Base 2013–2017 (nova projeção)")
    b3 = medida("PER3a Estimativa – Base desde 2018 (revisão)")
    meia = (W - 16) / 2
    p.grafico("per3a", "lineChart", MARGEM, p.y, meia, 400, ano_p,
              [(b1, "Base até 2012"), (b2, "Base 2013–2017 (nova projeção)"),
               (b3, "Base desde 2018 (revisão)")], "PER3a Título", "População estimada (pessoas)",
              cores_series={qref(b1): CORES_BASES["ate_2012"], qref(b2): CORES_BASES["2013_2017"],
                            qref(b3): CORES_BASES["desde_2018"]},
              ordenar=ano_p, ascendente=True, legenda=True, rotulos=False, categorico=True)
    censo = medida("PER3b População (Censo)")
    p.grafico("per3b", "clusteredColumnChart", MARGEM + meia + 16, p.y, meia, 400, ano_p,
              [(censo, "População (Censo, pessoas)")], "PER3b Título", "População (Censo, pessoas)",
              cores_series={qref(censo): AZUL}, ordenar=ano_p, ascendente=True, categorico=True,
              filtros=[filtro_valores(ano_p, [2010, 2022])])
    p.y += 408
    p.texto("per3_marcas", MARGEM, p.y, W, 28,
            [("Marcações (C8): 2013: quebra de série: nova projeção · 2018: revisão da projeção",
              {"fontSize": "10pt", "color": TEXTO2})])
    p.y += 32
    p.texto_dinamico("per3_motivo", "PER3 Motivo 2012→2013", 36)
    p.texto_dinamico("per3_aviso2012", "PER3 Aviso 2012", 44)
    p.avisos("per3_avisos", ["Aviso quebras da estimativa", "Aviso Censo oficial"])

    p.titulo_secao("PER4", "Como o PIB per capita evoluiu?")
    pc = medida("PER4 PIB per capita")
    p.grafico("per4", "lineChart", MARGEM, p.y, W, 360, ano_p,
              [(pc, "PIB per capita (R$, publicado pelo IBGE)")], "PER4 Título",
              "PIB per capita (R$, publicado pelo IBGE)", cores_series={qref(pc): AZUL},
              ordenar=ano_p, ascendente=True, categorico=True)
    p.y += 368
    p.avisos("per4_avisos", ["Aviso PIB per capita", "Aviso denominador do per capita"])

    p.titulo_secao("PER5", "O município ganhou ou perdeu peso no PIB do estado?")
    ano_part = coluna(PART, "ano")
    part = medida("PER5 Participação no PIB nominal do estado")
    p.grafico("per5", "lineChart", MARGEM, p.y, W, 360, ano_part,
              [(part, "Participação no PIB nominal de SC (%)")], "PER5 Título",
              "Participação no PIB nominal de SC (%)", cores_series={qref(part): AZUL},
              ordenar=ano_part, ascendente=True, categorico=True)
    p.y += 368
    p.texto_dinamico("per5_aviso_ano", "PER5 Aviso ano sem valor", 36)
    p.avisos("per5_avisos", ["Aviso participação"])
    p.rodape()
    return p


# ======================= Sobre os dados =========================================================

def sobre() -> Pagina:
    """Sobre os dados (dashboards/streamlit/paginas/sobre.py; docs/dashboards.md, seção 4.6)."""
    p = Pagina("sobre", "Sobre os dados")
    p.cabecalho("De onde vêm os números e o que eles não dizem?", filtros=False)

    p.titulo_secao("SOB1", "Fontes e séries")
    ind = coluna(GRADE, "codigo_indicador")
    p.tabela("sob1", MARGEM, p.y, W, 260,
             [(coluna(GRADE, "cod_serie"), "Série"), (coluna(GRADE, "fonte"), "Fonte"),
              (ind, "Indicador"), (coluna(GRADE, "tipo_medida"), "Tipo de medida"),
              (coluna(GRADE, "unidade"), "Unidade"), (medida("SOB1 Anos"), "Anos"),
              (medida("SOB1 Última coleta"), "Última coleta")],
             titulo="Uma linha por série de origem", ordenar=ind, ascendente=True)
    p.y += 268

    p.titulo_secao("SOB2", "Cobertura")
    p.tabela("sob2", MARGEM, p.y, 760, 300,
             [(ind, "Indicador"), (coluna(GRADE, "status"), "Status"),
              (medida("SOB2 Linhas (município × ano)"), "Linhas (município × ano)")],
             titulo="Linhas da grade por indicador e status", ordenar=ind, ascendente=True)
    p.texto("sob2_legenda", MARGEM + 776, p.y, W - 776, 300,
            [("com_valor: valor publicado; municipio_nao_instalado: ausência esperada de Pescaria "
              "Brava e Balneário Rincão antes de 2013 (regras 6 e 10); sem_dado: ausência não "
              "esperada, que faria os testes falharem.", {"fontSize": "10pt", "color": TEXTO2})])
    p.y += 308

    p.titulo_secao("SOB3", "Regras de leitura")
    regras = [
        ("Censo e estimativa são medidas diferentes (regra 2). Nunca aparecem na mesma série. "
         + aviso("Aviso Censo oficial")),
        "PIB é nominal (regra 3). " + aviso("Aviso PIB nominal") + " " + aviso("Aviso revisão do PIB"),
        ("PIB per capita é o publicado (regra 4). " + aviso("Aviso PIB per capita") + " Não há per "
         "capita de região ou do estado; a única estatística mostrada é a mediana entre os municípios. "
         + aviso("Aviso denominador do per capita")),
        "Ausência não é zero (regra 5). Valor ausente aparece como \"sem dado\" e não é interpolado.",
        "Estimativa em três bases (regra 12). " + aviso("Aviso quebras da estimativa"),
        "Dupla contagem em 2012 (regra 13). " + aviso("Aviso dupla contagem 2012"),
        "Saltos do PIB em municípios pequenos. " + aviso("Aviso A1"),
        "PIB municipal é distribuição do PIB estadual. " + aviso("Aviso distribuição do PIB"),
        "Detalhes em docs/limitacoes.md e docs/dashboards.md no repositório.",
    ]
    h = 30 * len(regras) + 16 * sum(len(r) > 170 for r in regras) + 16
    p.texto("sob3", MARGEM, p.y, W, h, [("• " + r, {"fontSize": "11pt", "color": TEXTO}) for r in regras])
    p.y += h + 8
    p.rodape()
    return p


def main() -> None:
    paginas = [inicio(), visao_geral(), populacao(), economia(), perfil(), sobre()]
    for pasta in PAGES.iterdir():  # remove páginas antigas (inclusive a vazia do Desktop)
        if pasta.is_dir():
            shutil.rmtree(pasta)
    for p in paginas:
        p.gravar()
    meta = {"$schema": SCHEMA_PAGES, "pageOrder": [p.nome for p in paginas],
            "activePageName": paginas[0].nome}
    (PAGES / "pages.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8")
    for p in paginas:
        print(p.nome, len(p.visuais), "visuais; altura", int(p.y + MARGEM))


if __name__ == "__main__":
    main()
