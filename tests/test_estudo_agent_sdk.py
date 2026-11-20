"""Testes da trava de credenciais do script de estudo do Agent SDK (sem chamar o modelo)."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

_CAMINHO = Path(__file__).resolve().parents[1] / "scripts" / "estudo_agent_sdk.py"
_spec = importlib.util.spec_from_file_location("estudo_agent_sdk", _CAMINHO)
estudo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(estudo)

VALOR_SECRETO = "valor-que-nunca-pode-aparecer"


def test_ambiente_limpo_nao_bloqueia():
    assert estudo.credenciais_fora_do_plano({"PATH": "x", "PG_DATABASE": "y"}) == []


@pytest.mark.parametrize("nome", [*estudo.CREDENCIAIS_DE_API, *estudo.PROVEDORES_DE_NUVEM])
def test_cada_variavel_que_desvia_do_plano_bloqueia(nome):
    assert estudo.credenciais_fora_do_plano({nome: VALOR_SECRETO}) == [nome]


def test_variavel_definida_vazia_tambem_bloqueia():
    assert estudo.credenciais_fora_do_plano({"ANTHROPIC_API_KEY": ""}) == ["ANTHROPIC_API_KEY"]


def test_main_para_sem_chamar_o_modelo_e_sem_mostrar_o_valor(capsys):
    ambiente = {"ANTHROPIC_API_KEY": VALOR_SECRETO}
    with patch.dict(estudo.os.environ, ambiente), \
         patch.object(estudo, "perguntar") as perguntar:
        assert estudo.main() == 2
    perguntar.assert_not_called()
    saida = capsys.readouterr()
    assert "ANTHROPIC_API_KEY" in saida.err
    assert VALOR_SECRETO not in saida.err + saida.out
