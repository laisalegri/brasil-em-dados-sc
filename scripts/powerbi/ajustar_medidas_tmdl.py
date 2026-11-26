"""Ajusta Medidas.tmdl em disco (Desktop FECHADO) para as páginas do D35. Idempotente.

Uso: python scripts/powerbi/ajustar_medidas_tmdl.py <pasta BrasilEmDadosSC.SemanticModel>

- Acrescenta medidas de exibição em texto para os cartões ("... (exibição)"): ausência vira
  "sem dado" (C4, regra 5) e o número aparece exato, como no Streamlit. As medidas numéricas
  originais não mudam (o número nunca vira zero).
- Acrescenta as medidas das páginas Início (INI) e Sobre os dados (SOB), lidas de
  'gold grade_indicador_municipio_ano' (mesma lógica de sql/analise/fontes_series.sql e cobertura.sql).
- Participações nos títulos com 2 casas decimais (VG3, POP1, ECO1, PER5).
- PER Identificação devolve "" quando não há município (o cartão não mostra "(Em branco)").
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path


INTEIRO = 'VAR _v = [{m}] RETURN IF ( ISBLANK ( _v ), "sem dado", FORMAT ( _v, "#,0" ) )'
REAIS = 'VAR _v = [{m}] RETURN IF ( ISBLANK ( _v ), "sem dado", "R$ " & FORMAT ( _v, "#,0.00" ) )'
REAIS_ABREV = ('VAR _v = [{m}] RETURN IF ( ISBLANK ( _v ), "sem dado", IF ( _v >= 1000000000, '
               '"R$ " & FORMAT ( _v, "0,,,.0" ) & " bi", IF ( _v >= 1000000, "R$ " & FORMAT ( _v, '
               '"0,,.0" ) & " mi", "R$ " & FORMAT ( _v, "#,0" ) ) ) )')
VARIACAO1 = ('VAR _v = [{m}] RETURN IF ( ISBLANK ( _v ), "sem dado", FORMAT ( _v, '
             '"+0.0;−0.0;0.0" ) & "%" )')
VARIACAO2 = ('VAR _v = [{m}] RETURN IF ( ISBLANK ( _v ), "sem dado", FORMAT ( _v, '
             '"+0.00;−0.00;0.00" ) & "%" )')

EXIBICAO = [  # (medida numérica, modelo, pasta)
    ("VG1a População (Censo 2022)", INTEIRO, "1 Visão geral"),
    ("VG1b PIB nominal no ano", REAIS_ABREV, "1 Visão geral"),
    ("VG1c Municípios", INTEIRO, "1 Visão geral"),
    ("POP2 Municípios comparáveis", INTEIRO, "2 População"),
    ("POP2 Cresceram", INTEIRO, "2 População"),
    ("POP2 Perderam população", INTEIRO, "2 População"),
    ("POP2 Variação: mediana entre os municípios", VARIACAO1, "2 População"),
    ("POP4 Estimativa no ano selecionado", INTEIRO, "2 População"),
    ("ECO3 PIB per capita: mediana entre os municípios", REAIS, "3 Economia"),
    ("ECO3 Municípios com valor", INTEIRO, "3 Economia"),
    ("ECO4 Variações acima de 50% em módulo", INTEIRO, "3 Economia"),
    ("ECO4 Municípios com saltos", INTEIRO, "3 Economia"),
    ("PER1 População (Censo 2010)", INTEIRO, "4 Perfil"),
    ("PER1 População (Censo 2022)", INTEIRO, "4 Perfil"),
    ("PER1 Variação entre os Censos", VARIACAO2, "4 Perfil"),
    ("PER1 PIB nominal no ano", REAIS_ABREV, "4 Perfil"),
    ("PER1 PIB per capita no ano", REAIS, "4 Perfil"),
]

GRADE = "'gold grade_indicador_municipio_ano'"
NOVAS = [  # (nome, expressão, pasta, formato, descrição)
    ("INI Texto de abertura",
     f'"População e PIB dos " & COUNTROWS ( \'gold dim_municipio\' ) & " municípios de Santa Catarina, '
     f'de " & MIN ( {GRADE}[ano] ) & " a " & MAX ( {GRADE}[ano] ) & ", a partir de dados públicos do IBGE."',
     "0 Início", None, "Início: abertura com o número de municípios e os anos da GOLD (app.py)."),
    ("INI Pergunta central",
     f'"Pergunta central: como os municípios de Santa Catarina se diferenciam em população e dimensão '
     f'econômica, e como esses indicadores evoluíram entre " & MIN ( {GRADE}[ano] ) & " e " & '
     f'MAX ( {GRADE}[ano] ) & "?"',
     "0 Início", None, "Início: pergunta central com os anos da GOLD (app.py)."),
    ("SOB1 Anos",
     f'VAR _i = MIN ( {GRADE}[ano] ) VAR _f = MAX ( {GRADE}[ano] ) RETURN IF ( NOT ISBLANK ( _i ), _i & "–" & _f )',
     "5 Sobre", None, "SOB1: anos cobertos pela série (mín.–máx.), como em sql/analise/fontes_series.sql."),
    ("SOB1 Última coleta",
     f'VAR _d = MAX ( {GRADE}[data_coleta] ) RETURN IF ( NOT ISBLANK ( _d ), FORMAT ( _d, "dd/MM/yyyy" ) )',
     "5 Sobre", None, "SOB1: data da última coleta da série (max(data_coleta))."),
    ("SOB2 Linhas (município × ano)",
     f"COUNTROWS ( {GRADE} )", "5 Sobre", "#,0",
     "SOB2: linhas da grade por indicador e status, como em sql/analise/cobertura.sql (contagem)."),
]

TROCAS = [  # (medida, trecho antigo, trecho novo)
    ("VG3 Título", '(Censo 2022)], "0.0" )', '(Censo 2022)], "0.00" )'),
    ("VG3 Título", '(PIB nominal no ano)], "0.0" )', '(PIB nominal no ano)], "0.00" )'),
    ("POP1 Título", "'gold participacao_estadual'[participacao_percentual] ), \"0.0\" )",
     "'gold participacao_estadual'[participacao_percentual] ), \"0.00\" )"),
    ("ECO1 Título", "'gold participacao_estadual'[participacao_percentual] ), \"0.0\" )",
     "'gold participacao_estadual'[participacao_percentual] ), \"0.00\" )"),
    ("PER5 Título", 'FORMAT ( _vi, "0.0" )', 'FORMAT ( _vi, "0.00" )'),
    ("PER5 Título", 'FORMAT ( _vf, "0.0" )', 'FORMAT ( _vf, "0.00" )'),
    ("PER Identificação",
     "LOOKUPVALUE ( 'gold dim_municipio'[nome_regiao_imediata], 'gold dim_municipio'[cod_municipio], _m ) )",
     "LOOKUPVALUE ( 'gold dim_municipio'[nome_regiao_imediata], 'gold dim_municipio'[cod_municipio], _m ), \"\" )"),
]


def nome_tmdl(nome: str) -> str:
    return f"'{nome}'"


def bloco(nome: str, expr: str, pasta: str, formato: str | None, descricao: str) -> str:
    linhas = [f"\t/// {descricao}", f"\tmeasure {nome_tmdl(nome)} = {expr}"]
    if formato:
        linhas.append(f"\t\tformatString: {formato}")
    linhas += [f"\t\tdisplayFolder: {pasta}", f"\t\tlineageTag: {uuid.uuid4()}", ""]
    return "\r\n".join(linhas) + "\r\n"


class ErroTmdl(Exception):
    """Medida esperada ausente ou trecho a trocar fora do esperado."""


def main(argv: list[str] | None = None) -> int:
    """Linha de comando: <pasta BrasilEmDadosSC.SemanticModel>."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__)
        return 2
    arq = Path(args[0]) / "definition" / "tables" / "Medidas.tmdl"
    txt = arq.read_bytes().decode("utf-8")  # mantém CRLF (read_text converteria)
    novos = []
    for m, modelo, pasta in EXIBICAO:
        nome = f"{m} (exibição)"
        if f"measure {nome_tmdl(m)} = " not in txt:
            raise ErroTmdl(f"medida ausente: {m}")
        if f"measure {nome_tmdl(nome)} = " not in txt:
            novos.append(bloco(nome, modelo.format(m=m), pasta, None,
                               f"Exibição em texto de [{m}] para cartão: 'sem dado' quando ausente "
                               "(C4, regra 5), valor exato como no Streamlit."))
    for nome, expr, pasta, formato, desc in NOVAS:
        if f"measure {nome_tmdl(nome)} = " not in txt:
            novos.append(bloco(nome, expr, pasta, formato, desc))
    linhas = txt.split("\n")
    for medida, antigo, novo in TROCAS:
        alvo = f"\tmeasure {nome_tmdl(medida)} = "
        idx = [i for i, l in enumerate(linhas) if l.startswith(alvo)]
        if len(idx) != 1:
            raise ErroTmdl(f"medida {medida}: {len(idx)} definições (esperada 1)")
        l = linhas[idx[0]]
        if novo in l:
            continue
        if l.count(antigo) != 1:
            raise ErroTmdl(f"medida {medida}: trecho a trocar não encontrado uma única vez")
        linhas[idx[0]] = l.replace(antigo, novo)
    txt = "\n".join(linhas)
    # insere as medidas novas antes do primeiro 'column' da tabela (fim da lista de medidas)
    pos = txt.find("\r\n\tcolumn ")
    if pos < 0:
        pos = len(txt)
    txt = txt[:pos].rstrip("\r\n") + "\r\n\r\n" + "".join(novos) + txt[pos:].lstrip("\r\n") \
        if novos else txt
    arq.write_bytes(txt.encode("utf-8"))
    print(f"{len(novos)} medidas novas; trocas conferidas: {len(TROCAS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
