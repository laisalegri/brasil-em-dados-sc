"""Verifica o PBIR gerado: JSON válido, schema oficial e referências ao modelo (TMDL).

Uso (da raiz do repositório):

    python scripts/powerbi/verificar_pbir.py dashboards/powerbi/BrasilEmDadosSC.Report 
        dashboards/powerbi/BrasilEmDadosSC.SemanticModel scripts/powerbi/schemas

A pasta de schemas é preenchida por baixar_schemas.py (schemas oficiais microsoft/json-schemas:
visualContainer 2.4.0, page 2.1.0, pagesMetadata 1.1.0 e os que eles referenciam). Checagens:
JSON válido; schema oficial; toda coluna/medida referenciada existe no TMDL; pages.json coerente
com as pastas; toda ordenação usa um campo do próprio visual; nenhum cartão usa medida numérica
(medida com formatString), que mostraria "(Em branco)" em vez de "sem dado" (C4, regra 5).
Versão de schema que não está na pasta (ex.: gravada pelo Desktop e ainda não publicada) gera
AVISO e pula só a validação de schema daquele arquivo. Sai com código 1 se houver erro.
"""
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft7Validator
from referencing import Registry
from referencing.exceptions import NoSuchResource
from referencing.jsonschema import DRAFT7

REPORT, MODELO, SCHEMAS = (Path(a) for a in sys.argv[1:4])
BASE_ID = "https://developer.microsoft.com/json-schemas/"

# -- registro local dos schemas (resolve $ref relativos e absolutos sem rede)
recursos = {}
for f in SCHEMAS.rglob("*.json"):
    rel = f.relative_to(SCHEMAS).as_posix()
    conteudo = json.loads(f.read_text(encoding="utf-8"))
    recurso = DRAFT7.create_resource(conteudo)
    recursos[BASE_ID + rel] = recurso
    if "$id" in conteudo:
        recursos[conteudo["$id"]] = recurso
registro = Registry().with_resources(recursos.items())

# -- objetos do modelo
tabelas: dict[str, set[str]] = {}
medidas: set[str] = set()
medidas_numericas: set[str] = set()
for f in (MODELO / "definition" / "tables").glob("*.tmdl"):
    txt = f.read_text(encoding="utf-8-sig")
    m = re.search(r"^table (.+)$", txt, flags=re.M)
    nome = m.group(1).strip().strip("'")
    cols = set()
    for c in re.finditer(r"^\tcolumn (?:'([^']+)'|(\S+))", txt, flags=re.M):
        cols.add(c.group(1) or c.group(2))
    tabelas[nome] = cols
    for me in re.finditer(r"^\tmeasure (?:'([^']+)'|(\S+)) = ", txt, flags=re.M):
        if nome == "Medidas":
            nome_medida = me.group(1) or me.group(2)
            medidas.add(nome_medida)
            # propriedades da medida: linhas com dois tabs logo abaixo da definição
            props = []
            for linha in txt[me.end():].split("\n")[1:]:
                if not linha.startswith("\t\t"):
                    break
                props.append(linha.strip())
            if any(pr.startswith("formatString:") for pr in props):
                medidas_numericas.add(nome_medida)

erros = []


def refs(obj, aliases=None):
    """Percorre o JSON e devolve (tipo, entidade, propriedade) de cada Column/Measure."""
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


sem_schema: dict[str, int] = {}
arquivos = sorted((REPORT / "definition" / "pages").rglob("*.json"))
n_ref = 0
for arq in arquivos:
    try:
        dado = json.loads(arq.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        erros.append(f"JSON inválido: {arq}: {e}")
        continue
    url = dado.get("$schema")
    try:
        schema = registro.get_or_retrieve(url).value.contents
    except NoSuchResource:
        # O Desktop pode gravar uma versão de schema ainda não publicada em microsoft/json-schemas.
        sem_schema.setdefault(url, 0)
        sem_schema[url] += 1
    else:
        val = Draft7Validator(schema, registry=registro)
        for e in val.iter_errors(dado):
            erros.append(f"schema: {arq.relative_to(REPORT)}: {list(e.absolute_path)}: {e.message[:200]}")
    for tipo, ent, prop, src in refs(dado):
        n_ref += 1
        if ent is None:
            erros.append(f"alias sem entidade: {arq.relative_to(REPORT)}: {src}")
        elif tipo == "Measure":
            if ent != "Medidas" or prop not in medidas:
                erros.append(f"medida inexistente: {arq.relative_to(REPORT)}: {ent}[{prop}]")
        else:
            if ent not in tabelas or prop not in tabelas[ent]:
                erros.append(f"coluna inexistente: {arq.relative_to(REPORT)}: {ent}[{prop}]")

    visual = dado.get("visual") or {}
    consulta = visual.get("query") or {}
    if visual.get("visualType") == "card":
        for st in consulta.get("queryState", {}).values():
            for pr in st["projections"]:
                nome_m = pr["field"].get("Measure", {}).get("Property")
                if nome_m in medidas_numericas:
                    erros.append(f"cartão com medida numérica: {arq.relative_to(REPORT)}: {nome_m}")
    if "sortDefinition" in consulta:
        campos = {json.dumps(pr["field"], sort_keys=True)
                  for st in consulta["queryState"].values() for pr in st["projections"]}
        for s in consulta["sortDefinition"].get("sort", []):
            if json.dumps(s["field"], sort_keys=True) not in campos:
                erros.append(f"ordenação por campo fora do visual: {arq.relative_to(REPORT)}")

# pages.json coerente com as pastas
meta = json.loads((REPORT / "definition" / "pages" / "pages.json").read_text(encoding="utf-8"))
pastas = {p.name for p in (REPORT / "definition" / "pages").iterdir() if p.is_dir()}
if set(meta["pageOrder"]) != pastas or meta["activePageName"] not in pastas:
    erros.append(f"pages.json incoerente: {meta} x {pastas}")

print(f"{len(arquivos)} arquivos JSON; {n_ref} referências ao modelo; {len(medidas)} medidas no TMDL "
      f"({len(medidas_numericas)} numéricas)")
for url, n in sem_schema.items():
    print(f"AVISO: schema não disponível localmente ({n} arquivos; só JSON e referências conferidos): {url}")
print("\n".join(erros) if erros else "OK: JSON válido, schema oficial e referências conferidos")
sys.exit(1 if erros else 0)
