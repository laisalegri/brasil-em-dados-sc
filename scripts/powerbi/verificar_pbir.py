"""Verifica o PBIR: JSON válido, schema oficial e referências ao modelo (TMDL).

Uso (da raiz do repositório):

    python scripts/powerbi/verificar_pbir.py dashboards/powerbi/BrasilEmDadosSC.Report ^
        dashboards/powerbi/BrasilEmDadosSC.SemanticModel scripts/powerbi/schemas

    python scripts/powerbi/verificar_pbir.py <Report> <SemanticModel> --sem-schema

A pasta de schemas é preenchida por baixar_schemas.py (schemas oficiais microsoft/json-schemas:
visualContainer 2.4.0, page 2.1.0, pagesMetadata 1.1.0 e os que eles referenciam). Checagens:
JSON válido; schema oficial; toda coluna/medida referenciada existe no TMDL; pages.json coerente
com as pastas; toda ordenação usa um campo do próprio visual; nenhum cartão usa medida numérica
(medida com formatString), que mostraria "(Em branco)" em vez de "sem dado" (C4, regra 5).

- Pasta de schemas inexistente ou vazia é erro (nada seria validado). `--sem-schema` pula a
  validação de schema de propósito (ex.: nos testes, sem rede) e o resultado diz isso.
- Versão de schema que não está na pasta (ex.: gravada pelo Desktop e ainda não publicada) gera
  AVISO e pula só a validação de schema daquele arquivo; o resultado final diz "OK com avisos".
- Sai com código 1 se houver erro, 0 caso contrário.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

BASE_ID = "https://developer.microsoft.com/json-schemas/"


@dataclass
class Resultado:
    """Saída da verificação: erros, avisos e contagens."""

    erros: list[str] = field(default_factory=list)
    sem_schema: dict[str, int] = field(default_factory=dict)
    arquivos: int = 0
    referencias: int = 0
    medidas: int = 0
    medidas_numericas: int = 0
    schema_validado: bool = True


def ler_modelo(modelo: Path) -> tuple[dict[str, set[str]], set[str], set[str]]:
    """Tabelas com suas colunas, medidas e medidas numéricas (com formatString) do TMDL."""
    tabelas: dict[str, set[str]] = {}
    medidas: set[str] = set()
    numericas: set[str] = set()
    for arquivo in (modelo / "definition" / "tables").glob("*.tmdl"):
        txt = arquivo.read_text(encoding="utf-8-sig")
        nome = re.search(r"^table (.+)$", txt, flags=re.M).group(1).strip().strip("'")
        tabelas[nome] = {c.group(1) or c.group(2)
                         for c in re.finditer(r"^\tcolumn (?:'([^']+)'|(\S+))", txt, flags=re.M)}
        if nome != "Medidas":
            continue
        for me in re.finditer(r"^\tmeasure (?:'([^']+)'|(\S+)) = ", txt, flags=re.M):
            nome_medida = me.group(1) or me.group(2)
            medidas.add(nome_medida)
            props = []  # propriedades: linhas com dois tabs logo abaixo da definição
            for linha in txt[me.end():].split("\n")[1:]:
                if not linha.startswith("\t\t"):
                    break
                props.append(linha.strip())
            if any(pr.startswith("formatString:") for pr in props):
                numericas.add(nome_medida)
    return tabelas, medidas, numericas


def registro_de_schemas(pasta: Path):
    """Registro local dos schemas (resolve $ref relativos e absolutos sem rede)."""
    from referencing import Registry
    from referencing.jsonschema import DRAFT7

    recursos = {}
    for arquivo in pasta.rglob("*.json"):
        conteudo = json.loads(arquivo.read_text(encoding="utf-8"))
        recurso = DRAFT7.create_resource(conteudo)
        recursos[BASE_ID + arquivo.relative_to(pasta).as_posix()] = recurso
        if "$id" in conteudo:
            recursos[conteudo["$id"]] = recurso
    return Registry().with_resources(recursos.items())


def refs(obj, aliases=None):
    """Percorre o JSON e devolve (tipo, entidade, propriedade, origem) de cada Column/Measure."""
    if isinstance(obj, dict):
        if "From" in obj and isinstance(obj["From"], list):
            aliases = dict(aliases or {})
            for fr in obj["From"]:
                if "Entity" in fr:
                    aliases[fr["Name"]] = fr["Entity"]
        for chave in ("Column", "Measure"):
            if chave in obj and isinstance(obj[chave], dict) and "Property" in obj[chave]:
                src = obj[chave]["Expression"]["SourceRef"]
                ent = src.get("Entity") or (aliases or {}).get(src.get("Source"))
                yield chave, ent, obj[chave]["Property"], src
        for v in obj.values():
            yield from refs(v, aliases)
    elif isinstance(obj, list):
        for v in obj:
            yield from refs(v, aliases)


def verificar(report: Path, modelo: Path, schemas: Path | None) -> Resultado:
    """Roda todas as checagens; `schemas=None` pula a validação de schema (dito no resultado)."""
    res = Resultado(schema_validado=schemas is not None)
    tabelas, medidas, numericas = ler_modelo(modelo)
    res.medidas, res.medidas_numericas = len(medidas), len(numericas)

    registro = None
    if schemas is not None:
        if not schemas.is_dir() or not any(schemas.rglob("*.json")):
            res.erros.append(f"pasta de schemas inexistente ou vazia: {schemas} "
                             "(rode baixar_schemas.py ou use --sem-schema)")
        else:
            registro = registro_de_schemas(schemas)

    paginas = report / "definition" / "pages"
    arquivos = sorted(paginas.rglob("*.json"))
    res.arquivos = len(arquivos)
    for arq in arquivos:
        rel = arq.relative_to(report)
        try:
            dado = json.loads(arq.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            res.erros.append(f"JSON inválido: {rel}: {e}")
            continue
        if registro is not None:
            _validar_schema(dado, rel, registro, res)
        for tipo, ent, prop, src in refs(dado):
            res.referencias += 1
            if ent is None:
                res.erros.append(f"alias sem entidade: {rel}: {src}")
            elif tipo == "Measure":
                if ent != "Medidas" or prop not in medidas:
                    res.erros.append(f"medida inexistente: {rel}: {ent}[{prop}]")
            elif ent not in tabelas or prop not in tabelas[ent]:
                res.erros.append(f"coluna inexistente: {rel}: {ent}[{prop}]")
        _checar_visual(dado, rel, numericas, res)

    meta = json.loads((paginas / "pages.json").read_text(encoding="utf-8"))
    pastas = {p.name for p in paginas.iterdir() if p.is_dir()}
    if set(meta["pageOrder"]) != pastas or meta["activePageName"] not in pastas:
        res.erros.append(f"pages.json incoerente: {meta} x {pastas}")
    return res


def _validar_schema(dado: dict, rel: Path, registro, res: Resultado) -> None:
    """Valida contra o schema declarado; versão ausente na pasta vira aviso."""
    from jsonschema import Draft7Validator
    from referencing.exceptions import NoSuchResource

    url = dado.get("$schema")
    try:
        schema = registro.get_or_retrieve(url).value.contents
    except NoSuchResource:
        res.sem_schema[url] = res.sem_schema.get(url, 0) + 1
        return
    for e in Draft7Validator(schema, registry=registro).iter_errors(dado):
        res.erros.append(f"schema: {rel}: {list(e.absolute_path)}: {e.message[:200]}")


def _checar_visual(dado: dict, rel: Path, numericas: set[str], res: Resultado) -> None:
    """Cartão sem medida numérica e ordenação só por campo do próprio visual."""
    visual = dado.get("visual") or {}
    consulta = visual.get("query") or {}
    if visual.get("visualType") == "card":
        for estado in consulta.get("queryState", {}).values():
            for pr in estado["projections"]:
                nome = pr["field"].get("Measure", {}).get("Property")
                if nome in numericas:
                    res.erros.append(f"cartão com medida numérica: {rel}: {nome}")
    if "sortDefinition" in consulta:
        campos = {json.dumps(pr["field"], sort_keys=True)
                  for estado in consulta["queryState"].values() for pr in estado["projections"]}
        for s in consulta["sortDefinition"].get("sort", []):
            if json.dumps(s["field"], sort_keys=True) not in campos:
                res.erros.append(f"ordenação por campo fora do visual: {rel}")


def resumo(res: Resultado) -> str:
    """Texto final: contagens, avisos, erros e a conclusão (OK, OK com avisos ou erro)."""
    linhas = [f"{res.arquivos} arquivos JSON; {res.referencias} referências ao modelo; "
              f"{res.medidas} medidas no TMDL ({res.medidas_numericas} numéricas)"]
    linhas += [f"AVISO: schema não disponível localmente ({n} arquivos; só JSON e referências "
               f"conferidos): {url}" for url, n in res.sem_schema.items()]
    if not res.schema_validado:
        linhas.append("AVISO: validação de schema pulada (--sem-schema)")
    if res.erros:
        linhas += res.erros
    elif res.sem_schema or not res.schema_validado:
        linhas.append("OK com avisos: JSON válido e referências conferidos; schema oficial "
                      "conferido só onde havia schema (veja os avisos acima)")
    else:
        linhas.append("OK: JSON válido, schema oficial e referências conferidos")
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    """Linha de comando: <Report> <SemanticModel> (<pasta de schemas> | --sem-schema)."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3:
        print(__doc__)
        return 2
    report, modelo, terceiro = args
    schemas = None if terceiro == "--sem-schema" else Path(terceiro)
    res = verificar(Path(report), Path(modelo), schemas)
    print(resumo(res))
    return 1 if res.erros else 0


if __name__ == "__main__":
    raise SystemExit(main())
