"""Baixa schemas PBIR oficiais (e todos os $ref que eles usam) para uma pasta local.

Uso:

    python scripts/powerbi/baixar_schemas.py scripts/powerbi/schemas 
        fabric/item/report/definition/visualContainer/2.4.0/schema.json 
        fabric/item/report/definition/page/2.1.0/schema.json 
        fabric/item/report/definition/pagesMetadata/1.1.0/schema.json

Fonte: https://github.com/microsoft/json-schemas (ramo main). A pasta de destino é a usada por
verificar_pbir.py; a validação depois roda sem rede.
"""
import json, sys, urllib.request, urllib.parse, pathlib, re

BASE_RAW = "https://raw.githubusercontent.com/microsoft/json-schemas/main/"
BASE_ID = "https://developer.microsoft.com/json-schemas/"
dest = pathlib.Path(sys.argv[1])
fila = sys.argv[2:]
vistos = set()

def refs(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "$ref" and isinstance(v, str) and not v.startswith("#"):
                yield v.split("#")[0]
            else:
                yield from refs(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from refs(v)

while fila:
    rel = fila.pop()
    if rel in vistos:
        continue
    vistos.add(rel)
    url = BASE_RAW + rel
    try:
        data = urllib.request.urlopen(url, timeout=30).read()
    except Exception as e:
        print("FALHOU", rel, e); continue
    alvo = dest / rel
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_bytes(data)
    obj = json.loads(data)
    for r in refs(obj):
        if r.startswith(BASE_ID):
            novo = r[len(BASE_ID):]
        else:
            novo = str(pathlib.PurePosixPath(urllib.parse.urljoin("https://h/" + rel, r)[len("https://h/"):]))
        fila.append(novo)
print(len(vistos), "schemas")
