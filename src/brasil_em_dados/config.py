"""Caminhos padrão do projeto."""

from pathlib import Path

RAIZ_PROJETO: Path = Path(__file__).resolve().parents[2]
PASTA_RAW: Path = RAIZ_PROJETO / "data" / "raw"
ARQUIVO_CONTROLE: Path = RAIZ_PROJETO / "data" / "controle" / "execucoes.jsonl"
PASTA_LOGS: Path = RAIZ_PROJETO / "logs"
PASTA_DDL: Path = RAIZ_PROJETO / "sql" / "ddl"
