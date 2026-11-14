"""Conversão de códigos de município (D09): 6 dígitos sem verificador → 7 dígitos do cadastro."""

from collections import Counter
from collections.abc import Iterable


def mapear_codigos_6_para_7(codigos6: Iterable[str], cadastro7: Iterable[str]) -> dict[str, str]:
    """Mapeia cada código de 6 dígitos para o único código de 7 do cadastro; exige 1:1."""
    cadastro = list(cadastro7)
    lista6 = list(codigos6)

    por_prefixo: dict[str, list[str]] = {}
    for codigo7 in cadastro:
        por_prefixo.setdefault(codigo7[:6], []).append(codigo7)

    problemas: list[str] = []
    repetidos = sorted(c for c, n in Counter(lista6).items() if n > 1)
    if repetidos:
        problemas.append(f"códigos de 6 dígitos repetidos: {repetidos[:5]}")

    mapa: dict[str, str] = {}
    sem_par, ambiguos = [], []
    for codigo6 in lista6:
        candidatos = por_prefixo.get(codigo6, [])
        if len(candidatos) == 1:
            mapa[codigo6] = candidatos[0]
        elif not candidatos:
            sem_par.append(codigo6)
        else:
            ambiguos.append(codigo6)
    if sem_par:
        problemas.append(f"sem correspondente no cadastro: {sorted(sem_par)[:5]}")
    if ambiguos:
        problemas.append(f"com mais de um correspondente: {sorted(ambiguos)[:5]}")

    nao_cobertos = sorted(set(cadastro) - set(mapa.values()))
    if nao_cobertos:
        problemas.append(f"municípios do cadastro sem código na resposta: {nao_cobertos[:5]}")

    if problemas:
        raise ValueError("Correspondência 6→7 dígitos não é 1:1: " + "; ".join(problemas))
    return mapa
