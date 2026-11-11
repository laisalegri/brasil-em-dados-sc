import importlib

import pytest


@pytest.mark.parametrize("modulo", [
    "requests", "pandas", "sqlalchemy", "psycopg", "dotenv",
    "matplotlib", "seaborn", "brasil_em_dados",
])
def test_modulo_importa(modulo):
    importlib.import_module(modulo)