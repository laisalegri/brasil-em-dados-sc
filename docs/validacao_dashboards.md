# Validação entre dashboards: SQL × Streamlit × Power BI (D37)

Confere se os 15 números de referência de [docs/dashboards.md](dashboards.md) (seção 6, R01–R15) são iguais nas três fontes: a consulta SQL na GOLD, o app Streamlit e o relatório Power BI.

## Resultado

**As 15 referências conferem nas três fontes:** 44 componentes, sem nenhuma divergência.

- **Data:** 26/11/2026.
- **Versões:**
  - código: commit `6766243` (D37), que traz a checagem `referencias`;
  - Power BI: o `BrasilEmDadosSC.pbip` do commit `2845e7b`, aberto no Desktop sem alterações (o `git status` de `dashboards/powerbi/` estava limpo);
  - PostgreSQL 15.5, Python 3.12.0, Streamlit 1.67.0, pandas 3.1.1, SQLAlchemy 2.1.8 e Power BI Modeling MCP 1.0.1. As ferramentas do MCP não informam a versão do Power BI Desktop.

## Como os valores foram comparados

**Comparação pelo valor, nunca pelo texto formatado do app ou do relatório.** Inteiros exatos, reais em centavos, participações com 4 casas e a variação entre os Censos com 2 casas, que são as casas da seção 6. Ausência nunca vira zero (regra 5) e nunca confere, nem com outra ausência: nenhuma referência admite falta de dado, então `NULL` dos dois lados é tratado como divergência.

| Fonte | Como foi lida |
|---|---|
| SQL | As 15 consultas da seção 6, copiadas sem mudança para `sql/referencias/r01.sql` a `r15.sql` (um teste garante que continuam iguais às do documento), como `bed_readonly`, numa transação `READ ONLY`. |
| Streamlit | O mesmo caminho de dados das páginas, com o filtro padrão (Santa Catarina, 2023, Florianópolis): as funções de `analise.consultas`, os tipos de `dashboard.dados.normalizar_tipos` e os cálculos de `dashboard.calculos`, sem o cache do Streamlit. Os testes AppTest conferem o texto que aparece na tela, abaixo. |
| Power BI | As 29 medidas da pasta "R Referências" do modelo, lidas por consultas DAX (`EVALUATE ROW`, sem `FORMAT`) pelo Power BI Modeling MCP, conectado ao Desktop aberto, só leitura. R06 e R07 também foram lidos por uma consulta `TOPN` sobre `'gold participacao_estadual'`, porque as medidas devolvem texto; os valores brutos batem com o texto. |

Os valores abaixo estão no formato da comparação: ponto decimal e sem separador de milhar.

| # | O que é | SQL | Streamlit | Power BI | Confere? |
|---|---|---|---|---|---|
| R01 | População de SC, Censo 2022 | 7610361 | 7610361 | 7610361 | sim |
| R02 | População de SC, Censo 2010 | 6248436 | 6248436 | 6248436 | sim |
| R03 | PIB nominal de SC, 2023 (R$) | 513392972000.00 | 513392972000.00 | 513392972000.00 | sim |
| R04 | PIB nominal de SC, 2010 (R$) | 153726009000.00 | 153726009000.00 | 153726009000.00 | sim |
| R05 | Estimativa de SC, 2012: valor; somados; excluídos | 6362734; 293; 2 | 6362734; 293; 2 | 6362734; 293; 2 | sim |
| R06 | 3 maiores em população, Censo 2022: município, pessoas, participação (%) | Joinville 616317 8.0984; Florianópolis 537211 7.0589; Blumenau 361261 4.7470 | idem | idem | sim |
| R07 | 3 maiores em PIB nominal, 2023: município, R$, participação (%) | Joinville 49815877000.00 9.7033; Itajaí 48195909000.00 9.3877; Florianópolis 31190132000.00 6.0753 | idem | idem | sim |
| R08 | Florianópolis: Censo 2010; Censo 2022; variação (%) | 421240; 537211; 27.53 | 421240; 537211; 27.53 | 421240; 537211; 27.53 | sim |
| R09 | Itajaí, participação no PIB nominal (%): 2010; 2023 | 6.5444; 9.3877 | 6.5444; 9.3877 | 6.5444; 9.3877 | sim |
| R10 | Municípios comparáveis entre os Censos; que perderam população | 293; 70 | 293; 70 | 293; 70 | sim |
| R11 | Maior PIB per capita, 2023 (R$) | Araquari 218625.97 | Araquari 218625.97 | Araquari 218625.97 | sim |
| R12 | PIB per capita 2023: mediana entre os municípios (R$); municípios com valor | 52591.20; 295 | 52591.20; 295 | 52591.20; 295 | sim |
| R13 | Saltos anuais de PIB nominal acima de 50%: variações; municípios | 61; 51 | 61; 51 | 61; 51 | sim |
| R14 | Estimativa 2012→2013: pares; com variação; algum comparável | 295; 0; não | 295; 0; não | 295; 0; não | sim |
| R15 | Estimativa 2017→2018: pares; com variação; algum comparável | 295; 295; não | 295; 295; não | 295; 295; não | sim |

Notas sobre as linhas:

- **R14 e R15 no Power BI:** "algum comparável" é a medida de contagem de pares comparáveis, que deu 0 nos dois casos.
- **R02:** a consulta SQL da seção 6 traz só o valor. Os 293 municípios somados também conferem no Power BI (medida "R02 Municípios somados Censo 2010"), mas não fazem parte da comparação automática.
- **"idem" em R06 e R07:** os mesmos 9 componentes, comparados um a um. A tabela completa, componente por componente, sai do comando de reprodução abaixo.

## Testes do app (AppTest)

Os testes que conferem R01–R15 na tela do app passaram em 26/11/2026: 5 testes. Eles comparam o texto formatado mostrado pelo app, como "7.610.361" e "R$ 513.392.972.000,00", nas páginas Visão geral, População, Economia, Perfil e Comparação, com os valores da seção 6.

```powershell
pytest tests/test_dashboard_app.py -k referencias -v
```

## Como reproduzir

1. **SQL × Streamlit,** comparação automática por componente, que sai com código 1 se algo divergir:

   ```powershell
   python -m brasil_em_dados.verificacao.referencias
   ```

   Se o banco não estiver acessível, o comando sai com código 2 e registra só o tipo do erro e o SQLSTATE, sem host, usuário ou banco. O mesmo teste roda no pytest (`tests/test_verificacao_referencias.py`, marcado como integração). O agente de verificação também faz essa checagem a cada execução, pela ferramenta `referencias_dashboards`.
2. **Tela do app:** `pytest tests/test_dashboard_app.py -k referencias -v`.
3. **Power BI:**
   - abra o `BrasilEmDadosSC.pbip` no Power BI Desktop;
   - peça ao subagent `especialista-power-bi` para ler pelo MCP, só lendo, as medidas da pasta "R Referências", com `EVALUATE ROW` e sem `FORMAT`;
   - compare com a tabela acima;
   - não salve o arquivo.

## Por que o Power BI fica fora da checagem automática

Ler as medidas exige o Power BI Desktop aberto, com o modelo carregado, e o MCP conectado a ele. O agente de verificação e o pytest rodam sem interface e sem o Desktop, então comparam só SQL × Streamlit. A conferência do Power BI é manual, pelo passo 3, e deve ser refeita quando o modelo ou a GOLD mudarem, por exemplo numa recarga após revisão do PIB pelo IBGE.
