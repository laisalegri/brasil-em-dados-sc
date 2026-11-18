"""Recria as views da GOLD a partir de sql/gold/, como bed_app, numa transação (D30).

Uso: python -m brasil_em_dados.db.aplicar_gold [--pasta sql/gold]

- Arquivos NN_*.sql, em ordem numérica, contendo só CREATE VIEW gold.* e COMMENT ON.
- Todas as views dos arquivos são derrubadas em ordem inversa (DROP VIEW IF EXISTS, sem
  CASCADE) e recriadas em ordem direta. Uma view fora dos arquivos que dependa delas faz o
  DROP falhar e a transação inteira é desfeita.
- Fica fora de public.ddl_aplicado (decisão D30): views não guardam dados e podem ser
  recriadas a qualquer momento a partir dos arquivos versionados.
- O SELECT do bed_readonly vem dos privilégios padrão do schema gold (01_schemas.sql).
"""

import argparse
import logging
import re
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import SQLAlchemyError

from brasil_em_dados.config import PASTA_GOLD
from brasil_em_dados.db import engine_app
from brasil_em_dados.db.aplicar_ddl import (
    ErroDDL,
    Script,
    _executar_no_driver,
    executar_scripts,
    ler_scripts,
)
from brasil_em_dados.logs import configurar_logging

# Nome fixo: com `python -m`, __name__ vira "__main__" e o log ficaria fora de "brasil_em_dados".
logger = logging.getLogger("brasil_em_dados.db.aplicar_gold")

_NOME = r"[a-z_][a-z0-9_]*"
# Cada comando precisa casar por inteiro, a partir do início, com um destes padrões.
_CREATE_VIEW = re.compile(rf"CREATE\s+VIEW\s+(gold\.{_NOME})\s+AS\s", re.IGNORECASE)
_COMMENT = re.compile(
    rf"COMMENT\s+ON\s+(?:VIEW\s+(gold\.{_NOME})|COLUMN\s+(gold\.{_NOME})\.{_NOME})"
    r"\s+IS\s+(?:''\s*)+", re.IGNORECASE)


def _texto_validavel(script: Script) -> str:
    """Texto sem comentários e com literais vazios, lido num único passe da esquerda para a
    direita (literal e comentário na ordem em que aparecem).

    Recusa o que o leitor não trata com segurança: comentário de bloco, '$' fora de literal
    (corpos $$) e '--' dentro de literal.
    """
    sql, saida, i = script.sql, [], 0
    while i < len(sql):
        if sql.startswith("--", i):
            fim = sql.find("\n", i)
            i = len(sql) if fim == -1 else fim
        elif sql.startswith("/*", i):
            raise ErroDDL(f"{script.nome}: comentário de bloco /* */ não é permitido na GOLD")
        elif sql[i] == "$":
            raise ErroDDL(f"{script.nome}: '$' fora de literal não é permitido na GOLD")
        elif sql[i] == "'":
            fim = i + 1
            while True:
                fim = sql.find("'", fim)
                if fim == -1:
                    raise ErroDDL(f"{script.nome}: literal sem aspa de fechamento")
                if sql.startswith("''", fim):  # aspa escapada dentro do literal
                    fim += 2
                    continue
                break
            if "--" in sql[i:fim]:
                raise ErroDDL(f"{script.nome}: '--' dentro de literal não é permitido na GOLD")
            saida.append("''")
            i = fim + 1
        else:
            saida.append(sql[i])
            i += 1
    return "".join(saida)


def comandos_do_script(script: Script) -> list[str]:
    """Comandos SQL do script, já sem comentários e com os literais vazios."""
    return [c.strip() for c in _texto_validavel(script).split(";") if c.strip()]


def views_do_script(script: Script) -> list[str]:
    """Views criadas pelo script, na ordem. Só são aceitos CREATE VIEW gold.<nome> AS e
    COMMENT ON VIEW/COLUMN sobre views criadas no próprio arquivo."""
    views: list[str] = []
    comentados: list[tuple[str, str]] = []
    for comando in comandos_do_script(script):
        criacao = _CREATE_VIEW.match(comando)
        comentario = _COMMENT.fullmatch(comando)
        if criacao:
            views.append(criacao.group(1).lower())
        elif comentario:
            comentados.append((comentario.group(1) or comentario.group(2), comando))
        else:
            raise ErroDDL(f"{script.nome}: só CREATE VIEW gold.<nome> AS e COMMENT ON VIEW/COLUMN "
                          f"gold.* são permitidos na GOLD (achado: {' '.join(comando.split()[:4])})")
    if not views:
        raise ErroDDL(f"{script.nome}: nenhum CREATE VIEW gold.* no arquivo")
    alheios = [comando for alvo, comando in comentados if alvo.lower() not in views]
    if alheios:
        raise ErroDDL(f"{script.nome}: COMMENT ON sobre view que não é criada neste arquivo: "
                      f"{' '.join(alheios[0].split()[:5])}")
    return views


def views_em_ordem(scripts: list[Script]) -> list[str]:
    """Todas as views dos scripts, na ordem de criação; nomes repetidos são erro."""
    views = [view for script in scripts for view in views_do_script(script)]
    repetidas = sorted(v for v, n in Counter(views).items() if n > 1)
    if repetidas:
        raise ErroDDL(f"Views criadas em mais de um arquivo: {repetidas}")
    return views


def _views_so_no_banco(conexao: Connection, views: list[str]) -> list[str]:
    no_banco = conexao.execute(text(
        "SELECT 'gold.' || table_name FROM information_schema.views "
        "WHERE table_schema = 'gold'")).scalars()
    return sorted(set(no_banco) - set(views))


def recriar_em_conexao(conexao: Connection, scripts: list[Script]) -> list[str]:
    """DROP em ordem inversa e CREATE em ordem direta, na transação aberta em `conexao`."""
    views = views_em_ordem(scripts)
    for view in reversed(views):
        conexao.execute(text(f"DROP VIEW IF EXISTS {view}"))
    executar_scripts(lambda sql: _executar_no_driver(conexao, sql), scripts)
    extras = _views_so_no_banco(conexao, views)
    if extras:
        logger.warning("Views no schema gold que não estão em sql/gold/ (mantidas): %s", extras)
    return views


def aplicar_gold(engine: Engine, pasta: Path = PASTA_GOLD) -> list[str]:
    """Recria todas as views da GOLD numa transação; devolve os nomes recriados."""
    ignorados = sorted(p.name for p in pasta.glob("00_*.sql"))
    if ignorados:
        # ler_scripts pula o 00 (script de superusuário da pasta ddl); na GOLD isso seria
        # um arquivo ignorado em silêncio.
        raise ErroDDL(f"Arquivos 00_*.sql não são permitidos em {pasta}: {ignorados}")
    scripts = ler_scripts(pasta)
    views_em_ordem(scripts)  # valida os arquivos antes de abrir a conexão
    with engine.begin() as conexao:
        return recriar_em_conexao(conexao, scripts)


def main(argv: list[str] | None = None, engine: Engine | None = None) -> int:
    """Linha de comando; devolve 0 se as views foram recriadas e 1 em erro (nada muda)."""
    parser = argparse.ArgumentParser(prog="python -m brasil_em_dados.db.aplicar_gold",
                                     description=__doc__.splitlines()[0])
    parser.add_argument("--pasta", type=Path, default=PASTA_GOLD, help="pasta das views")
    args = parser.parse_args(argv)
    configurar_logging()
    engine = engine or engine_app()
    try:
        views = aplicar_gold(engine, args.pasta)
    except (ErroDDL, SQLAlchemyError) as exc:
        logger.error("GOLD não recriada; transação desfeita. %s", exc)
        return 1
    finally:
        engine.dispose()
    logger.info("Views da GOLD recriadas (%d): %s", len(views), ", ".join(views))
    return 0


if __name__ == "__main__":
    sys.exit(main())
