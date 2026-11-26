"""Baixa schemas PBIR oficiais (e todos os $ref que eles usam) para uma pasta local.

Uso (da raiz do repositório):

    python scripts/powerbi/baixar_schemas.py scripts/powerbi/schemas ^
        fabric/item/report/definition/visualContainer/2.4.0/schema.json ^
        fabric/item/report/definition/page/2.1.0/schema.json ^
        fabric/item/report/definition/pagesMetadata/1.1.0/schema.json

Fonte: https://github.com/microsoft/json-schemas (ramo main). A pasta de destino é a usada por
verificar_pbir.py; a validação depois roda sem rede. Sai com código 1 se algum schema não puder
ser baixado (ex.: versão gravada pelo Desktop e ainda não publicada) e lista quais falharam.
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.parse
import urllib.request
from collections.abc import Iterator

BASE_RAW = "https://raw.githubusercontent.com/microsoft/json-schemas/main/"
BASE_ID = "https://developer.microsoft.com/json-schemas/"


def refs(obj: object) -> Iterator[str]:
    """Caminhos de todos os $ref externos (sem o fragmento #...) de um schema."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "$ref" and isinstance(v, str) and not v.startswith("#"):
                yield v.split("#")[0]
            else:
                yield from refs(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from refs(v)


def relativo(ref: str, base: str) -> str:
    """Caminho do $ref relativo à raiz do repositório de schemas."""
    if ref.startswith(BASE_ID):
        return ref[len(BASE_ID):]
    return str(pathlib.PurePosixPath(urllib.parse.urljoin("https://h/" + base, ref)[len("https://h/"):]))


def baixar(dest: pathlib.Path, iniciais: list[str]) -> tuple[set[str], list[str]]:
    """Baixa os schemas e suas dependências; devolve (baixados, falhas)."""
    fila, vistos, falhas = list(iniciais), set(), []
    while fila:
        rel = fila.pop()
        if rel in vistos:
            continue
        vistos.add(rel)
        try:
            data = urllib.request.urlopen(BASE_RAW + rel, timeout=30).read()
        except OSError as e:  # HTTPError e URLError herdam de OSError
            falhas.append(f"{rel}: {e}")
            continue
        alvo = dest / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_bytes(data)
        fila.extend(relativo(r, rel) for r in refs(json.loads(data)))
    return vistos - {f.split(":")[0] for f in falhas}, falhas


def main(argv: list[str] | None = None) -> int:
    """Linha de comando: <pasta de destino> <schema> [<schema> ...]."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) < 2:
        print(__doc__)
        return 2
    baixados, falhas = baixar(pathlib.Path(args[0]), args[1:])
    print(f"{len(baixados)} schemas baixados")
    for falha in falhas:
        print("FALHOU", falha)
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
