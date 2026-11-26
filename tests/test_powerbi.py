"""Power BI (D35/D38): textos iguais aos do Streamlit e os scripts de scripts/powerbi/.

- Os avisos (medidas 'Aviso ...' e 'Rodapé' do Medidas.tmdl) e os textos da página Sobre os dados
  no PBIR são idênticos às constantes de dashboard/textos.py; a centralização fica para o D41/D42.
- verificar_pbir roda sobre o PBIP do repositório sem rede (--sem-schema) e pega os erros que deve.
- gerar_pbir recusa apagar as páginas sem --sobrescrever ou com mudanças não commitadas.
- ajustar_medidas_tmdl é idempotente sobre o Medidas.tmdl atual; baixar_schemas sai com 1 em falha.
"""

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

from brasil_em_dados.config import RAIZ_PROJETO
from brasil_em_dados.dashboard import textos as t

PASTA_SCRIPTS = RAIZ_PROJETO / "scripts" / "powerbi"
REPORT = RAIZ_PROJETO / "dashboards" / "powerbi" / "BrasilEmDadosSC.Report"
MODELO = RAIZ_PROJETO / "dashboards" / "powerbi" / "BrasilEmDadosSC.SemanticModel"
PAGINAS = REPORT / "definition" / "pages"

# Medida de aviso do Power BI → constante do Streamlit.
AVISOS = {
    "Rodapé": t.RODAPE,
    "Aviso PIB nominal": t.AVISO_PIB_NOMINAL,
    "Aviso revisão do PIB": t.AVISO_REVISAO_PIB,
    "Aviso distribuição do PIB": t.AVISO_DISTRIBUICAO,
    "Aviso PIB per capita": t.AVISO_PER_CAPITA,
    "Aviso denominador do per capita": t.AVISO_DENOMINADOR,
    "Aviso A1": t.AVISO_A1,
    "Aviso participação": t.AVISO_PARTICIPACAO,
    "Aviso sem per capita regional": t.AVISO_SEM_PER_CAPITA_REGIONAL,
    "Aviso quebras da estimativa": t.AVISO_QUEBRAS,
    "Aviso dupla contagem 2012": t.AVISO_DUPLA_CONTAGEM,
    "Aviso Censo oficial": t.AVISO_CENSO_OFICIAL,
    "Aviso apurações do Censo 2022": t.AVISO_APURACOES,
    "Aviso Laguna": t.AVISO_LAGUNA,
    "Aviso Criciúma": t.AVISO_CRICIUMA,
    "Aviso não instalado": t.AVISO_NAO_INSTALADO,
    "Aviso revisão 2018": t.AVISO_REVISAO_2018,
}


def _script(nome: str) -> ModuleType:
    """Importa um script de scripts/powerbi/ pelo caminho (eles não leem sys.argv no import)."""
    spec = importlib.util.spec_from_file_location(f"powerbi_{nome}", PASTA_SCRIPTS / f"{nome}.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo  # dataclasses com anotações adiadas procuram o módulo aqui
    spec.loader.exec_module(modulo)
    return modulo


def _paragrafos(visual: str, pagina: str = "sobre") -> list[str]:
    dado = json.loads((PAGINAS / pagina / "visuals" / visual / "visual.json").read_text(encoding="utf-8"))
    paragrafos = dado["visual"]["objects"]["general"][0]["properties"]["paragraphs"]
    return ["".join(r["value"] for r in p["textRuns"]) for p in paragrafos]


# -- textos iguais nos dois dashboards ------------------------------------------------------------

def test_avisos_do_power_bi_sao_iguais_aos_do_streamlit():
    no_tmdl = _script("gerar_pbir").textos_aviso(MODELO)
    medidas_de_aviso = {n for n in no_tmdl if n.startswith("Aviso ") or n == "Rodapé"}
    assert medidas_de_aviso == set(AVISOS), "medida de aviso nova ou removida: atualize o mapa"
    for medida, texto in AVISOS.items():
        assert no_tmdl[medida] == texto, f"{medida} difere de textos.py"


def test_regras_do_sobre_no_power_bi_sao_iguais_as_do_streamlit():
    esperado = [f"• {titulo} {texto}" for titulo, texto in t.REGRAS_DE_LEITURA]
    esperado.append(f"• {t.DETALHES_REGRAS}")
    assert _paragrafos("sobre_sob3") == esperado


def test_legenda_da_cobertura_no_power_bi_e_igual_a_do_streamlit():
    assert _paragrafos("sobre_sob2_legenda") == [t.LEGENDA_COBERTURA]


# -- verificar_pbir -------------------------------------------------------------------------------

def test_pbip_do_repositorio_passa_no_verificador_sem_rede():
    verificar = _script("verificar_pbir")
    res = verificar.verificar(REPORT, MODELO, None)
    assert res.erros == []
    assert res.arquivos > 100 and res.referencias > 200 and res.medidas > 100
    assert "validação de schema pulada" in verificar.resumo(res)


def test_pasta_de_schemas_vazia_e_erro_e_nao_ok(tmp_path):
    verificar = _script("verificar_pbir")
    res = verificar.verificar(REPORT, MODELO, tmp_path / "schemas")
    assert any("pasta de schemas inexistente ou vazia" in e for e in res.erros)
    assert verificar.main([str(REPORT), str(MODELO), str(tmp_path / "schemas")]) == 1


def _copia_do_report(tmp_path: Path) -> Path:
    destino = tmp_path / "Report"
    shutil.copytree(REPORT, destino)
    return destino


def test_cartao_com_medida_numerica_e_erro(tmp_path):
    verificar = _script("verificar_pbir")
    report = _copia_do_report(tmp_path)
    arquivo = report / "definition/pages/economia/visuals/economia_eco4_k1/visual.json"
    dado = json.loads(arquivo.read_text(encoding="utf-8"))
    proj = dado["visual"]["query"]["queryState"]["Values"]["projections"][0]
    proj["field"]["Measure"]["Property"] = "ECO4 Variações acima de 50% em módulo"  # numérica
    arquivo.write_text(json.dumps(dado, ensure_ascii=False), encoding="utf-8")
    res = verificar.verificar(report, MODELO, None)
    assert any(e.startswith("cartão com medida numérica") for e in res.erros)


def test_medida_inexistente_e_erro(tmp_path):
    verificar = _script("verificar_pbir")
    report = _copia_do_report(tmp_path)
    arquivo = report / "definition/pages/economia/visuals/economia_eco4_k1/visual.json"
    arquivo.write_text(arquivo.read_text(encoding="utf-8").replace(
        "ECO4 Variações acima de 50% em módulo (exibição)", "Medida que não existe"), encoding="utf-8")
    assert any("medida inexistente" in e for e in verificar.verificar(report, MODELO, None).erros)


def test_verificador_sem_argumentos_mostra_o_uso(capsys):
    assert _script("verificar_pbir").main([]) == 2
    assert "Uso" in capsys.readouterr().out


# -- gerar_pbir: trava contra sobrescrita ---------------------------------------------------------

def test_gerador_recusa_sem_sobrescrever(capsys):
    gerar = _script("gerar_pbir")
    assert gerar.main([str(REPORT), str(MODELO)]) == 2
    assert "Passe --sobrescrever" in capsys.readouterr().out


def test_gerador_recusa_com_mudancas_nao_commitadas(monkeypatch, capsys):
    gerar = _script("gerar_pbir")
    monkeypatch.setattr(gerar, "pasta_limpa_no_git", lambda pasta: False)
    monkeypatch.setattr(gerar.shutil, "rmtree", lambda *a, **k: pytest.fail("apagou páginas"))
    assert gerar.main([str(REPORT), str(MODELO), "--sobrescrever"]) == 2
    assert "mudanças não commitadas" in capsys.readouterr().out


# -- ajustar_medidas_tmdl e baixar_schemas --------------------------------------------------------

def test_ajuste_de_medidas_e_idempotente_sobre_o_tmdl_atual(tmp_path):
    ajustar = _script("ajustar_medidas_tmdl")
    modelo = tmp_path / "Modelo"
    (modelo / "definition" / "tables").mkdir(parents=True)
    original = MODELO / "definition" / "tables" / "Medidas.tmdl"
    copia = modelo / "definition" / "tables" / "Medidas.tmdl"
    shutil.copyfile(original, copia)
    assert ajustar.main([str(modelo)]) == 0
    assert copia.read_bytes() == original.read_bytes()


def test_ajuste_sem_argumentos_mostra_o_uso():
    assert _script("ajustar_medidas_tmdl").main([]) == 2


def test_baixar_schemas_sai_com_1_quando_um_download_falha(monkeypatch, tmp_path, capsys):
    baixar = _script("baixar_schemas")

    def falhar(url, timeout):
        raise OSError("HTTP Error 404: Not Found")

    monkeypatch.setattr(baixar.urllib.request, "urlopen", falhar)
    assert baixar.main([str(tmp_path), "fabric/x/2.15.0/schema.json"]) == 1
    assert "FALHOU fabric/x/2.15.0/schema.json" in capsys.readouterr().out


def test_baixar_schemas_resolve_refs_relativos_e_absolutos():
    baixar = _script("baixar_schemas")
    base = "fabric/item/report/definition/page/2.1.0/schema.json"
    assert baixar.relativo("../../a/1.0.0/schema.json", base) == \
        "fabric/item/report/definition/a/1.0.0/schema.json"
    assert baixar.relativo(baixar.BASE_ID + "fabric/b.json", base) == "fabric/b.json"
    assert list(baixar.refs({"x": {"$ref": "y.json#/d"}, "z": [{"$ref": "#/local"}]})) == ["y.json"]
