"""Aplica o DDL de sql/ddl/ como bed_app, em ordem, numa única transação (D18/D19).

Uso: python -m brasil_em_dados.db.aplicar_ddl [--pasta sql/ddl]

- Considera os arquivos NN_*.sql com NN >= 01, em ordem numérica. O 00_banco_e_usuarios.sql
  fica de fora: cria banco e usuários, precisa de superusuário e roda no psql.
- Cada arquivo roda UMA vez: o aplicado fica registrado em public.ddl_aplicado (arquivo,
  sha256, aplicado_em). Rodar de novo não reaplica nada.
- Arquivo já aplicado e editado depois (sha256 diferente) é erro: a mudança vai num arquivo
  novo numerado. Também é erro um arquivo registrado que sumiu da pasta, ou um arquivo novo
  com número menor que o de um já aplicado.
- No primeiro erro, a transação é desfeita inteira e nada fica aplicado.
"""

import argparse
import hashlib
import logging
import re
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import SQLAlchemyError

from brasil_em_dados.config import PASTA_DDL
from brasil_em_dados.db import engine_app
from brasil_em_dados.logs import configurar_logging

# Nome fixo: com `python -m`, __name__ vira "__main__" e o log ficaria fora de "brasil_em_dados".
logger = logging.getLogger("brasil_em_dados.db.aplicar_ddl")

PRIMEIRO_NUMERO = 1  # 00 é o script de superusuário
TABELA_REGISTRO = "public.ddl_aplicado"

_NOME_SCRIPT = re.compile(r"^(\d{2})_[a-z0-9_]+\.sql$")
_META_COMANDO_PSQL = re.compile(r"^\s*\\", re.MULTILINE)
_COMENTARIO_LINHA = re.compile(r"--[^\n]*")
_CORPO_DOLAR = re.compile(r"\$([A-Za-z_]*)\$.*?\$\1\$", re.DOTALL)  # DO $$ ... $$, funções
_COMANDO_TRANSACAO = re.compile(
    r"(?:^|;)\s*(BEGIN|COMMIT|ROLLBACK|END|ABORT|START\s+TRANSACTION|SAVEPOINT|RELEASE)\b",
    re.IGNORECASE)

DDL_REGISTRO = f"""
CREATE TABLE IF NOT EXISTS {TABELA_REGISTRO} (
    arquivo     text PRIMARY KEY CHECK (arquivo ~ '^[0-9]{{2}}_[a-z0-9_]+\\.sql$'),
    sha256      text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{{64}}$'),
    aplicado_em timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE {TABELA_REGISTRO} IS
    'Arquivos de sql/ddl/ já aplicados por brasil_em_dados.db.aplicar_ddl; cada um roda uma vez.';
"""


class ErroDDL(Exception):
    """Falha ao ler, planejar ou aplicar um script de DDL; a mensagem cita o arquivo."""


@dataclass(frozen=True)
class Script:
    """Um arquivo de DDL já lido, com o hash do conteúdo."""

    arquivo: Path
    sql: str

    @property
    def nome(self) -> str:
        return self.arquivo.name

    @property
    def numero(self) -> int:
        return int(self.nome[:2])

    @property
    def sha256(self) -> str:
        return calcular_sha256(self.sql)


@dataclass(frozen=True)
class Registro:
    """Linha de public.ddl_aplicado."""

    sha256: str
    aplicado_em: str


def calcular_sha256(sql: str) -> str:
    """SHA-256 do texto com quebras de linha normalizadas (CRLF do Windows = LF do Git)."""
    return hashlib.sha256(sql.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _sem_comentarios_e_corpos(sql: str) -> str:
    return _COMENTARIO_LINHA.sub("", _CORPO_DOLAR.sub("", sql))


def ler_scripts(pasta: Path = PASTA_DDL) -> list[Script]:
    """Lê os scripts NN_*.sql (NN >= 01) em ordem; recusa nomes fora do padrão e comandos
    do psql ou de transação (que quebrariam a transação única)."""
    scripts: list[Script] = []
    numeros: dict[int, Path] = {}
    for arquivo in sorted(pasta.glob("*.sql")):
        casamento = _NOME_SCRIPT.match(arquivo.name)
        if not casamento:
            raise ErroDDL(f"Nome fora do padrão NN_nome.sql: {arquivo.name}")
        numero = int(casamento.group(1))
        if numero < PRIMEIRO_NUMERO:
            continue
        if numero in numeros:
            raise ErroDDL(f"Número repetido: {numeros[numero].name} e {arquivo.name}")
        numeros[numero] = arquivo
        sql = arquivo.read_text(encoding="utf-8")
        if not sql.strip():
            raise ErroDDL(f"{arquivo.name}: arquivo vazio")
        if _META_COMANDO_PSQL.search(sql):
            raise ErroDDL(f"{arquivo.name}: comando do psql (\\...) não roda pelo aplicador")
        comando = _COMANDO_TRANSACAO.search(_sem_comentarios_e_corpos(sql))
        if comando:
            raise ErroDDL(f"{arquivo.name}: comando de transação ({comando.group(1).upper()}) "
                          "não é permitido; o aplicador já roda tudo numa transação")
        scripts.append(Script(arquivo, sql))
    if not scripts:
        raise ErroDDL(f"Nenhum script de DDL em {pasta}")
    return scripts


def planejar(scripts: list[Script], registrados: Mapping[str, Registro]) -> list[Script]:
    """Decide o que aplicar: só os scripts ainda não registrados, em ordem.

    Falha se um script aplicado foi editado, se um registrado sumiu da pasta, ou se um script
    novo tem número menor que o de um já aplicado.
    """
    nomes = {script.nome for script in scripts}
    sumidos = sorted(set(registrados) - nomes)
    if sumidos:
        raise ErroDDL(f"Arquivos aplicados não estão mais em sql/ddl/: {', '.join(sumidos)}. "
                      "Arquivos aplicados não podem ser apagados nem renomeados.")
    for script in scripts:
        registro = registrados.get(script.nome)
        if registro and registro.sha256 != script.sha256:
            raise ErroDDL(
                f"{script.nome} já foi aplicado em {registro.aplicado_em} e foi editado depois "
                "(sha256 diferente). Não edite arquivos aplicados: desfaça a edição e crie um "
                "arquivo novo numerado (por exemplo, "
                f"{max(s.numero for s in scripts) + 1:02d}_descricao.sql) com a mudança.")
    pendentes = [script for script in scripts if script.nome not in registrados]
    ultimo_aplicado = max((int(nome[:2]) for nome in registrados), default=0)
    fora_de_ordem = [script.nome for script in pendentes if script.numero < ultimo_aplicado]
    if fora_de_ordem:
        raise ErroDDL(f"Arquivos novos com número menor que o último aplicado "
                      f"({ultimo_aplicado:02d}): {', '.join(fora_de_ordem)}. Renumere-os.")
    return pendentes


def executar_scripts(executar: Callable[[str], object], scripts: list[Script]) -> None:
    """Executa os scripts em ordem e para no primeiro erro, citando o arquivo."""
    for script in scripts:
        logger.info("Aplicando %s", script.nome)
        try:
            executar(script.sql)
        except Exception as exc:
            raise ErroDDL(f"{script.nome}: {exc}") from exc


def _executar_no_driver(conexao: Connection, sql: str) -> None:
    """Executa texto com vários comandos pelo cursor do driver (sem parâmetros)."""
    cursor = conexao.connection.cursor()
    try:
        cursor.execute(sql)
    finally:
        cursor.close()


def ler_registrados(conexao: Connection) -> dict[str, Registro]:
    """Cria o registro se faltar, trava-o contra execuções simultâneas e devolve o conteúdo."""
    _executar_no_driver(conexao, DDL_REGISTRO)
    conexao.execute(text(f"LOCK TABLE {TABELA_REGISTRO} IN SHARE ROW EXCLUSIVE MODE"))
    linhas = conexao.execute(text(
        f"SELECT arquivo, sha256, aplicado_em::text FROM {TABELA_REGISTRO}")).all()
    return {arquivo: Registro(sha256, aplicado_em) for arquivo, sha256, aplicado_em in linhas}


def aplicar_em_conexao(conexao: Connection, scripts: list[Script]) -> list[str]:
    """Aplica os pendentes e os registra, na transação já aberta em `conexao`."""
    pendentes = planejar(scripts, ler_registrados(conexao))
    # Cada arquivo vai inteiro pelo driver (vários comandos, blocos $$), sem parâmetros.
    executar_scripts(lambda sql: _executar_no_driver(conexao, sql), pendentes)
    for script in pendentes:
        conexao.execute(text(f"INSERT INTO {TABELA_REGISTRO} (arquivo, sha256) "
                             "VALUES (:arquivo, :sha256)"),
                        {"arquivo": script.nome, "sha256": script.sha256})
    return [script.nome for script in pendentes]


def aplicar_ddl(engine: Engine, pasta: Path = PASTA_DDL) -> list[str]:
    """Aplica os scripts pendentes numa transação; devolve os nomes aplicados (pode ser vazio)."""
    scripts = ler_scripts(pasta)
    with engine.begin() as conexao:
        return aplicar_em_conexao(conexao, scripts)


def main(argv: list[str] | None = None, engine: Engine | None = None) -> int:
    """Linha de comando; devolve 0 se deu certo (mesmo sem nada a aplicar) e 1 em erro."""
    parser = argparse.ArgumentParser(prog="python -m brasil_em_dados.db.aplicar_ddl",
                                     description=__doc__.splitlines()[0])
    parser.add_argument("--pasta", type=Path, default=PASTA_DDL, help="pasta dos scripts")
    args = parser.parse_args(argv)
    configurar_logging()
    engine = engine or engine_app()
    try:
        aplicados = aplicar_ddl(engine, args.pasta)
    except ErroDDL as exc:
        logger.error("DDL não aplicado; transação desfeita. %s", exc)
        return 1
    except SQLAlchemyError as exc:
        # Erro de banco fora dos scripts (conexão, permissão no registro); sem senha na mensagem.
        logger.error("DDL não aplicado; transação desfeita. Erro do banco: %s", exc)
        return 1
    finally:
        engine.dispose()
    if aplicados:
        logger.info("DDL aplicado: %s", ", ".join(aplicados))
    else:
        logger.info("Nada a aplicar: todos os arquivos já estão em %s", TABELA_REGISTRO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
