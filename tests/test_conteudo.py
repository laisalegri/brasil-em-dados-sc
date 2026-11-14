"""Testes do conteúdo esperado por fonte (D12–D14), com dados sintéticos e amostras reais."""

import json
import logging

import pytest

from brasil_em_dados.config import RAIZ_PROJETO
from brasil_em_dados.extract import catalogo, conteudo
from brasil_em_dados.extract.erros import ErroValidacao

FIXTURES = RAIZ_PROJETO / "tests" / "fixtures"
NOVOS = sorted(conteudo.CODIGOS_NOVOS)
# 293 códigos sintéticos no padrão 42xxxxx + os dois municípios instalados em 2013 = 295.
# O 7º dígito faz o papel do verificador, então os prefixos de 6 dígitos são únicos (D09).
ANTIGOS = [f"42{i:04d}0" for i in range(1, 294)]
TODOS = ANTIGOS + NOVOS

ROTULOS_PADRAO = {"municipio": "D1C", "variavel": "D2C", "ano": "D3C", "valor": "V"}


def _sidra(municipios, anos, variavel, sinais=(), chaves=ROTULOS_PADRAO, valor="100"):
    """Monta uma resposta SIDRA sintética; `sinais` lista (município, ano) com '...'."""
    cabecalho = {"NC": "Nível Territorial (Código)",
                 chaves["municipio"]: conteudo.ROTULO_MUNICIPIO,
                 chaves["variavel"]: conteudo.ROTULO_VARIAVEL,
                 chaves["ano"]: conteudo.ROTULO_ANO,
                 chaves["valor"]: conteudo.ROTULO_VALOR}
    linhas = [cabecalho]
    for ano in anos:
        for municipio in municipios:
            linhas.append({"NC": "6",
                           chaves["municipio"]: municipio,
                           chaves["variavel"]: variavel,
                           chaves["ano"]: str(ano),
                           chaves["valor"]: "..." if (municipio, ano) in sinais else valor})
    return linhas


def _validar(cod_serie, dados, cadastro=TODOS):
    conteudo.validar_conteudo(cod_serie, dados, cadastro=cadastro)


# --- leitura do cabeçalho SIDRA -------------------------------------------------------------

def test_le_amostra_real_pelo_cabecalho():
    dados = json.loads((FIXTURES / "sidra_6579_amostra.json").read_bytes())
    linhas = conteudo.linhas_sidra(dados)
    assert [(l.municipio, l.ano, l.variavel, l.valor) for l in linhas] == [
        ("4205407", 2011, "9324", "427298"),
        ("4212650", 2011, "9324", "..."),
    ]


def test_campos_em_outra_ordem_sao_localizados_pelo_rotulo():
    chaves = {"municipio": "D3C", "variavel": "D1C", "ano": "D2C", "valor": "V"}
    dados = _sidra(TODOS, [2022], "93", chaves=chaves)
    _validar("sidra_4709_v93", dados)


def test_cabecalho_sem_rotulo_de_municipio_falha():
    dados = _sidra(TODOS, [2022], "93")
    dados[0]["D1C"] = "Outra coisa"
    with pytest.raises(ErroValidacao, match="rótulos ausentes"):
        _validar("sidra_4709_v93", dados)


def test_cabecalho_que_nao_e_dicionario_falha():
    dados = _sidra(TODOS, [2022], "93")
    dados[0] = ["Município (Código)", "Ano (Código)"]
    with pytest.raises(ErroValidacao, match="deveria ser o cabeçalho"):
        _validar("sidra_4709_v93", dados)


def test_resposta_sidra_que_nao_e_lista_falha():
    with pytest.raises(ErroValidacao, match="esperada lista"):
        _validar("sidra_4709_v93", {"erro": "x"})


def test_linha_com_ano_nao_numerico_falha():
    dados = _sidra(TODOS, [2022], "93")
    dados[1]["D3C"] = "dois mil e vinte e dois"
    with pytest.raises(ErroValidacao, match="fora do formato"):
        _validar("sidra_4709_v93", dados)


def test_linha_sem_campo_do_cabecalho_falha():
    dados = _sidra(TODOS, [2022], "93")
    del dados[1]["V"]
    with pytest.raises(ErroValidacao, match="fora do formato"):
        _validar("sidra_4709_v93", dados)


# --- sidra_6579_v9324 -----------------------------------------------------------------------

ANOS_6579 = range(2011, 2022)


def test_6579_valida_com_sinais_dos_novos_em_2011():
    sinais = {(c, 2011) for c in NOVOS}
    _validar("sidra_6579_v9324", _sidra(TODOS, ANOS_6579, "9324", sinais))


def test_6579_sinal_dos_novos_em_2012_falha():
    sinais = {("4212650", 2012)}
    with pytest.raises(ErroValidacao, match="sinais não permitidos"):
        _validar("sidra_6579_v9324", _sidra(TODOS, ANOS_6579, "9324", sinais))


def test_6579_sinal_de_outro_municipio_falha():
    sinais = {(ANTIGOS[0], 2011)}
    with pytest.raises(ErroValidacao, match="sinais não permitidos"):
        _validar("sidra_6579_v9324", _sidra(TODOS, ANOS_6579, "9324", sinais))


def test_6579_linha_faltando_falha():
    dados = _sidra(TODOS, ANOS_6579, "9324")
    dados.pop()
    with pytest.raises(ErroValidacao, match="esperadas 3245 linhas"):
        _validar("sidra_6579_v9324", dados)


def test_6579_anos_diferentes_com_mesma_contagem_falha():
    # 11 anos × 295 = 3245 linhas: só a regra do conjunto de anos é quebrada.
    with pytest.raises(ErroValidacao, match=r"^sidra_6579_v9324: anos \[2012"):
        _validar("sidra_6579_v9324", _sidra(TODOS, range(2012, 2023), "9324"))


# --- sidra_1378_v93 -------------------------------------------------------------------------

def test_1378_valida_sem_os_novos():
    _validar("sidra_1378_v93", _sidra(ANTIGOS, [2010], "93"))


def test_1378_com_292_linhas_falha():
    with pytest.raises(ErroValidacao, match="esperadas 293 linhas, vieram 292"):
        _validar("sidra_1378_v93", _sidra(ANTIGOS[:-1], [2010], "93"))


def test_1378_com_os_novos_falha():
    with pytest.raises(ErroValidacao, match="deveriam estar ausentes"):
        _validar("sidra_1378_v93", _sidra(TODOS, [2010], "93"))


# --- sidra_4709_v93 -------------------------------------------------------------------------

def test_4709_valida_com_295_numericos():
    _validar("sidra_4709_v93", _sidra(TODOS, [2022], "93"))


def test_4709_qualquer_sinal_falha():
    with pytest.raises(ErroValidacao, match="sinais não permitidos"):
        _validar("sidra_4709_v93", _sidra(TODOS, [2022], "93", {("4212650", 2022)}))


def test_4709_variavel_errada_falha():
    with pytest.raises(ErroValidacao, match="variáveis"):
        _validar("sidra_4709_v93", _sidra(TODOS, [2022], "1000093"))


def test_4709_municipio_repetido_falha():
    municipios = ANTIGOS[:-1] + [ANTIGOS[0]] + NOVOS
    with pytest.raises(ErroValidacao, match="repetidos"):
        _validar("sidra_4709_v93", _sidra(municipios, [2022], "93"))


def test_4709_codigo_fora_do_padrao_falha():
    municipios = ANTIGOS[:-1] + ["4300001"] + NOVOS
    with pytest.raises(ErroValidacao, match="fora do padrão"):
        _validar("sidra_4709_v93", _sidra(municipios, [2022], "93"))


# --- sidra_5938_v37 -------------------------------------------------------------------------

ANOS_5938 = range(2010, 2024)


def test_5938_valida_com_sinais_dos_novos_em_2010_a_2012():
    sinais = {(c, a) for c in NOVOS for a in range(2010, 2013)}
    _validar("sidra_5938_v37", _sidra(TODOS, ANOS_5938, "37", sinais))


def test_5938_sinal_em_2013_falha():
    with pytest.raises(ErroValidacao, match="sinais não permitidos"):
        _validar("sidra_5938_v37", _sidra(TODOS, ANOS_5938, "37", {("4220000", 2013)}))


def test_5938_linha_faltando_falha():
    dados = _sidra(TODOS, ANOS_5938, "37")
    dados.pop()
    with pytest.raises(ErroValidacao, match="esperadas 4130 linhas"):
        _validar("sidra_5938_v37", dados)


def test_5938_anos_diferentes_com_mesma_contagem_falha():
    with pytest.raises(ErroValidacao, match=r"^sidra_5938_v37: anos \[2011"):
        _validar("sidra_5938_v37", _sidra(TODOS, range(2011, 2025), "37"))


def test_regras_sidra_usam_a_variavel_do_catalogo():
    for cod_serie, regra in conteudo.REGRAS_SIDRA.items():
        assert regra.variavel == catalogo.obter(cod_serie).variavel_ou_indicador


# --- ibge_localidades_sc --------------------------------------------------------------------

def _localidades(ids):
    return [{"id": int(i), "nome": f"Município {i}"} for i in ids]


def test_localidades_valida_com_295_ids():
    _validar("ibge_localidades_sc", _localidades(TODOS))


def test_localidades_amostra_real_de_5_falha_na_contagem():
    dados = json.loads((FIXTURES / "localidades_sc_amostra.json").read_bytes())
    with pytest.raises(ErroValidacao, match="esperados 295 municípios, vieram 5"):
        _validar("ibge_localidades_sc", dados)


def test_localidades_id_repetido_falha():
    with pytest.raises(ErroValidacao, match="repetidos"):
        _validar("ibge_localidades_sc", _localidades(TODOS[:-1] + [TODOS[0]]))


def test_localidades_id_com_6_digitos_falha():
    with pytest.raises(ErroValidacao, match="fora do padrão"):
        _validar("ibge_localidades_sc", _localidades(TODOS[:-1] + ["420540"]))


def test_localidades_id_que_nao_comeca_com_42_falha():
    with pytest.raises(ErroValidacao, match="fora do padrão"):
        _validar("ibge_localidades_sc", _localidades(TODOS[:-1] + ["4300001"]))


def test_cadastro_valido_devolve_codigos_de_7_digitos():
    assert conteudo.codigos_do_cadastro(_localidades(TODOS)) == TODOS


def test_cadastro_invalido_falha():
    with pytest.raises(ErroValidacao, match="esperados 295 municípios"):
        conteudo.codigos_do_cadastro(_localidades(TODOS[:-1]))


# --- pesquisas_38_i47001 --------------------------------------------------------------------

PREFIXOS = [c[:6] for c in TODOS]


def _pesquisas(codigos6):
    return [{"id": 47001, "res": [{"localidade": c, "res": {"2021": "1.00"}} for c in codigos6]}]


def test_pesquisas_valida_com_cadastro_1_para_1():
    _validar("pesquisas_38_i47001", _pesquisas(PREFIXOS), TODOS)


def test_pesquisas_codigo_sem_par_no_cadastro_falha():
    with pytest.raises(ErroValidacao, match="sem correspondente"):
        _validar("pesquisas_38_i47001", _pesquisas(PREFIXOS[:-1] + ["429999"]), TODOS)


def test_pesquisas_localidade_repetida_falha():
    with pytest.raises(ErroValidacao, match="repetidos"):
        _validar("pesquisas_38_i47001", _pesquisas(PREFIXOS[:-1] + [PREFIXOS[0]]), TODOS)


def test_pesquisas_localidade_com_7_digitos_falha():
    with pytest.raises(ErroValidacao, match="fora do padrão 42xxxx"):
        _validar("pesquisas_38_i47001", _pesquisas(PREFIXOS[:-1] + [TODOS[-1]]), TODOS)


def test_pesquisas_municipio_do_cadastro_sem_codigo_na_resposta_falha():
    cadastro = TODOS + ["4299990"]
    with pytest.raises(ErroValidacao, match="sem código na resposta"):
        _validar("pesquisas_38_i47001", _pesquisas(PREFIXOS), cadastro)


def test_pesquisas_com_294_localidades_falha():
    with pytest.raises(ErroValidacao, match="esperadas 295 localidades"):
        _validar("pesquisas_38_i47001", _pesquisas(PREFIXOS[:-1]), TODOS)


def test_pesquisas_item_sem_res_falha():
    with pytest.raises(ErroValidacao, match="sem lista 'res'"):
        _validar("pesquisas_38_i47001", [{"id": 47001}], TODOS)


def test_pesquisas_resultado_sem_localidade_falha():
    with pytest.raises(ErroValidacao, match="sem 'localidade'"):
        _validar("pesquisas_38_i47001", [{"id": 47001, "res": [{"res": {}}]}], TODOS)


def test_pesquisas_sem_cadastro_falha():
    with pytest.raises(ErroValidacao, match="cadastro de municípios é obrigatório"):
        conteudo.validar_conteudo("pesquisas_38_i47001", _pesquisas(PREFIXOS), cadastro=None)


# --- cobertura das regras -------------------------------------------------------------------

@pytest.mark.parametrize("cod_serie", list(catalogo.FONTES))
def test_toda_fonte_do_catalogo_tem_regra(cod_serie):
    with pytest.raises(ErroValidacao) as erro:
        _validar(cod_serie, [{"x": 1}, {"y": 2}], TODOS)
    assert "Sem regra" not in str(erro.value)


# --- D16: códigos conferidos no cadastro ----------------------------------------------------

DESCONHECIDO = "4299990"  # no padrão 42xxxxx, mas fora do cadastro

# Resposta válida de cada série SIDRA: (variável, anos, municípios, (município, ano) com sinal).
SIDRA_VALIDA = {
    "sidra_6579_v9324": ("9324", ANOS_6579, TODOS, {(c, 2011) for c in NOVOS}),
    "sidra_1378_v93": ("93", [2010], ANTIGOS, set()),
    "sidra_4709_v93": ("93", [2022], TODOS, set()),
    "sidra_5938_v37": ("37", ANOS_5938, TODOS, {(c, a) for c in NOVOS for a in range(2010, 2013)}),
}


def _sidra_valida(cod_serie, trocar=None):
    """Resposta válida da série; `trocar` = (código antigo, código novo) em todos os anos."""
    variavel, anos, municipios, sinais = SIDRA_VALIDA[cod_serie]
    if trocar:
        municipios = [trocar[1] if m == trocar[0] else m for m in municipios]
    return _sidra(municipios, anos, variavel, sinais)


@pytest.mark.parametrize("cod_serie", list(conteudo.REGRAS_SIDRA))
def test_sidra_municipio_fora_do_cadastro_falha(cod_serie):
    dados = _sidra_valida(cod_serie, trocar=(ANTIGOS[0], DESCONHECIDO))
    with pytest.raises(ErroValidacao, match=rf"municípios fora do cadastro: \['{DESCONHECIDO}'\]"):
        _validar(cod_serie, dados)


@pytest.mark.parametrize("cod_serie", list(conteudo.REGRAS_SIDRA))
def test_sidra_com_todos_os_municipios_no_cadastro_passa(cod_serie):
    _validar(cod_serie, _sidra_valida(cod_serie))


def test_sidra_municipio_fora_do_cadastro_falha_mesmo_com_contagem_certa():
    # 295 linhas, padrão 42xxxxx e sem repetição: só a regra do cadastro é quebrada.
    dados = _sidra_valida("sidra_4709_v93", trocar=(ANTIGOS[0], DESCONHECIDO))
    with pytest.raises(ErroValidacao, match=r"^sidra_4709_v93: municípios fora do cadastro"):
        _validar("sidra_4709_v93", dados)


def test_sidra_com_cadastro_vazio_falha():
    with pytest.raises(ErroValidacao, match="municípios fora do cadastro"):
        _validar("sidra_4709_v93", _sidra_valida("sidra_4709_v93"), cadastro=[])


@pytest.mark.parametrize("cod_serie", list(conteudo.REGRAS_SIDRA))
def test_sidra_sem_cadastro_falha(cod_serie):
    with pytest.raises(ErroValidacao, match="cadastro de municípios é obrigatório"):
        conteudo.validar_conteudo(cod_serie, _sidra_valida(cod_serie), cadastro=None)


def test_localidades_nao_exige_cadastro():
    conteudo.validar_conteudo("ibge_localidades_sc", _localidades(TODOS), cadastro=None)


def test_pesquisas_codigo_desconhecido_no_padrao_42_falha_sem_correspondente():
    codigos = PREFIXOS[:-1] + [DESCONHECIDO[:6]]
    with pytest.raises(ErroValidacao, match=r"sem correspondente no cadastro: \['429999'\]"):
        _validar("pesquisas_38_i47001", _pesquisas(codigos), TODOS)


# --- D16: aviso de zero suspeito no SIDRA ---------------------------------------------------

LOGGER_CONTEUDO = "brasil_em_dados.extract.conteudo"


def _avisos(caplog):
    return [r for r in caplog.records
            if r.name == LOGGER_CONTEUDO and r.levelno == logging.WARNING]


@pytest.mark.parametrize("zero", ["0", "0.00"])
def test_sidra_valor_zero_avisa_no_log_e_nao_reprova(caplog, zero):
    dados = _sidra(TODOS, [2022], "93")
    dados[1]["V"] = zero
    with caplog.at_level(logging.WARNING, logger=LOGGER_CONTEUDO):
        _validar("sidra_4709_v93", dados)
    [aviso] = _avisos(caplog)
    assert "1 valor(es) zero" in aviso.getMessage()
    assert TODOS[0] in aviso.getMessage()


def test_sidra_zero_no_pib_tambem_avisa(caplog):
    dados = _sidra_valida("sidra_5938_v37")
    dados[-1]["V"] = "0"
    with caplog.at_level(logging.WARNING, logger=LOGGER_CONTEUDO):
        _validar("sidra_5938_v37", dados)
    assert len(_avisos(caplog)) == 1


def test_sidra_varios_zeros_geram_um_aviso_com_a_contagem(caplog):
    dados = _sidra(TODOS, [2022], "93")
    for linha in dados[1:4]:
        linha["V"] = "0"
    with caplog.at_level(logging.WARNING, logger=LOGGER_CONTEUDO):
        _validar("sidra_4709_v93", dados)
    [aviso] = _avisos(caplog)
    assert "3 valor(es) zero" in aviso.getMessage()


@pytest.mark.parametrize("valor", ["100", "0.5", "10"])
def test_sidra_valor_nao_zero_nao_gera_aviso(caplog, valor):
    with caplog.at_level(logging.WARNING, logger=LOGGER_CONTEUDO):
        _validar("sidra_4709_v93", _sidra(TODOS, [2022], "93", valor=valor))
    assert _avisos(caplog) == []


def test_sidra_traco_nos_municipios_novos_reprova(caplog):
    # A fonte devolve "..." para Pescaria Brava e Balneário Rincão em 2011; "-" viraria
    # população 0 na carga (regra 9) para município que ainda não existia.
    dados = _sidra(TODOS, ANOS_6579, "9324")
    for linha in dados[1:]:
        if linha["D1C"] in NOVOS and linha["D3C"] == "2011":
            linha["V"] = "-"
    with caplog.at_level(logging.WARNING, logger=LOGGER_CONTEUDO):
        with pytest.raises(ErroValidacao, match="sinais não permitidos"):
            _validar("sidra_6579_v9324", dados)
    assert _avisos(caplog) == []


def test_sidra_traco_nao_permitido_continua_sendo_sinal_e_reprova(caplog):
    dados = _sidra(TODOS, [2022], "93")
    dados[1]["V"] = "-"
    with caplog.at_level(logging.WARNING, logger=LOGGER_CONTEUDO):
        with pytest.raises(ErroValidacao, match="sinais não permitidos"):
            _validar("sidra_4709_v93", dados)
    assert _avisos(caplog) == []


def test_sidra_zero_nao_esconde_outro_problema():
    dados = _sidra(TODOS, [2022], "93")
    dados[1]["V"] = "0"
    dados.pop()
    with pytest.raises(ErroValidacao, match="esperadas 295 linhas"):
        _validar("sidra_4709_v93", dados)


@pytest.mark.parametrize("valor, esperado", [
    ("0", True), ("0.00", True), ("-0", True), ("100", False), ("0.01", False),
    ("-", False), ("...", False), ("X", False),
])
def test_eh_zero_so_reconhece_zero_numerico(valor, esperado):
    assert conteudo.eh_zero(valor) is esperado


def test_codigo_fora_do_padrao_nao_e_repetido_como_fora_do_cadastro():
    dados = _sidra(TODOS[:-1] + ["4300001"], [2022], "93")
    with pytest.raises(ErroValidacao, match="fora do padrão 42xxxxx") as erro:
        _validar("sidra_4709_v93", dados)
    assert "fora do cadastro" not in str(erro.value)
