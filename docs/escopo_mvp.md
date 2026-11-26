# D01 — Escopo do MVP

Versão aprovada em 2026-11-11. Versão viva e comentada: documento "D01 — Escopo do MVP · Brasil em Dados SC".

Revisado em 26/11/2026 (D38): fontes confirmadas, riscos resolvidos e situação dos critérios de sucesso.

## Objetivo e pergunta central

O MVP entrega um pipeline reproduzível (RAW → SILVER → GOLD) com população e PIB dos 295 municípios de SC, de 2010 a 2023. Esses dados alimentam dois dashboards. Agentes de IA entram como apoio ao desenvolvimento (subagents do Claude Code e um agente de verificação com o Agent SDK), não como produto final.

**Pergunta central:** como os municípios de Santa Catarina se diferenciam em população e dimensão econômica, e como esses indicadores evoluíram entre 2010 e 2023?

**Perguntas derivadas que o MVP precisa responder:**

1. Quais municípios concentram população e PIB, e quanto representam do total estadual?
2. Como a população de cada município variou entre os Censos de 2010 e 2022?
3. Como o PIB nominal de cada município evoluiu entre 2010 e 2023?
4. Como os municípios se comparam em PIB per capita em um mesmo ano?
5. Qual é a composição setorial da economia de cada município? (extensão, fora do MVP: decisão D10)

## Público-alvo

| Público | O que procura | O que o MVP precisa mostrar |
| --- | --- | --- |
| Recrutadores e avaliadores técnicos | Competência de ponta a ponta | README claro, pipeline que roda do zero, testes, decisões documentadas |
| Analistas e gestores interessados em SC | Comparar municípios e ver tendências | Dashboards com filtros por região, município e ano, com fonte e unidade visíveis |
| A própria autora (desenvolvimento com agentes) | Entregar mais rápido sem perder qualidade | Subagents e agente de verificação versionados no repositório e usados no fluxo de trabalho |

## Escopo do MVP

**Recorte:** UF 42 (Santa Catarina), todos os municípios do cadastro atual do IBGE (295) e anos de 2010 a 2023.

| Indicador | Tipo de medida | Fonte (confirmada no D07–D10) | Anos esperados | Situação no MVP |
| --- | --- | --- | --- | --- |
| População censitária | Censo | SIDRA 1378 (2010) e 4709, var. 93 (2022) | 2010, 2022 | Incluso |
| População estimada | Estimativa | SIDRA 6579, var. 9324 | 2011–2021 (sem 2010, 2022 e 2023) | Incluso |
| PIB a preços correntes | PIB nominal | SIDRA 5938, var. 37 | 2010–2023 | Incluso |
| PIB per capita | Oficial (IBGE) | API de Pesquisas do IBGE, pesquisa 38, indicador 47001 (decisão D09) | 2010–2023 | Incluso |
| Valor adicionado por setor | VAB nominal | Setores (extensão): tabela 5938, variáveis 498, 513, 517, 6575, 525 e 543; sem abertura em 2022–2023 | Confirmada no D10 | Extensão, fora do MVP (decisão D10) |

**Entregáveis:** extratores com rastreabilidade, banco PostgreSQL (dimensões, fato e controle), camada GOLD, notebooks de EDA, dashboard Power BI, app Streamlit, subagents de desenvolvimento e agente de verificação do pipeline.

O relatório Power BI tem seis páginas, sem a Comparação, que fica só no Streamlit (D35). A publicação no Power BI Service usada para revisão não faz parte do MVP (D35).

## Fora de escopo

- Deflacionar o PIB ou calcular crescimento real (extensão).
- Interpolar ou projetar população para anos sem dado oficial.
- Outros estados ou comparação nacional (extensão).
- Educação, saúde, emprego e outros temas (extensão).
- Recompor séries de municípios criados no período com dados do município de origem.
- Airflow, Spark, Docker, nuvem e agendamento automático.
- Deploy público. Publicar o Streamlit (sem agente) é a primeira extensão.
- Agente de perguntas de negócio para usuários finais (extensão).

## Critérios de sucesso (checklist do D39)

Situação conferida em 26/11/2026, na auditoria do D38. `[x]` = atendido, com a evidência; `[ ]` = pendente, com o que falta.

**Dados e pipeline**

- [x] `dim_municipio` com 295 linhas, código IBGE de 7 dígitos, armazenado como texto e único. Evidência: chave primária `text` com `CHECK (cod_municipio ~ '^42[0-9]{5}$')` em `sql/ddl/02_dimensoes.sql`; primeira carga com 295 municípios (D20); teste T5 (`tests/test_qualidade_dados.py`).
- [x] Cada valor da tabela fato ligado à sua série de origem (`dim_serie`: fonte, tabela/variável ou pesquisa/indicador, unidade), ao tipo de medida (pela `dim_indicador`) e à data de coleta. Evidência: FK composta (`cod_serie`, `codigo_indicador`) e `data_coleta` `NOT NULL` em `sql/ddl/03_fato_e_controle.sql`; `tipo_medida` `NOT NULL` na `dim_indicador` (D18/D19); testes T4 e T13.
- [x] Nenhuma duplicidade na chave (município, indicador, ano). Evidência: chave primária em `sql/ddl/03_fato_e_controle.sql`; teste T3.
- [x] Nenhum dado ausente preenchido com zero; cobertura por indicador e ano documentada. Evidência: `CHECK (valor IS NOT NULL OR sinal_origem IS NOT NULL)`; testes T5 e T6 (os 14 `NULL` são de 4212650 e 4220000 antes de 2013, D21); `docs/dicionario_dados.md`, seção 5; coluna `status` de `gold.grade_indicador_municipio_ano`.
- [ ] Pipeline roda do zero (RAW → GOLD) com um comando documentado no README. Parcial: `python -m brasil_em_dados.verificacao --coleta --carga --gold` roda coleta, carga, GOLD e pytest num comando, mas pressupõe banco, usuários e DDL criados (passos 2 a 4 do README). Execução do zero no D39.
- [x] Reexecutar o pipeline não sobrescreve o RAW nem duplica dados. Evidência: gravação com `os.link` (D11) e testes em `tests/test_raw.py` e `tests/test_falhas_coleta.py`; upsert idempotente, com `test_segunda_carga_nao_muda_nada` em `tests/test_carga_integracao.py` e `tests/test_fato_integracao.py`; segunda carga real sem alterações (D20, D21).

**Qualidade**

- [x] Testes do pytest passando para esquema, contagens, chaves, tipos e regras de negócio. Evidência: suítes em `tests/` (`test_ddl_integracao.py`, T1–T16 em `test_qualidade_dados.py`, `test_gold_integracao.py`, entre outras); execução do agente de verificação em 26/11/2026 com 1032 testes passando (relatório local `reports/verificacao_20261126T195611.md`, não versionado). A suíte completa roda de novo no fechamento do D38.
- [x] Totais de SC na GOLD conferidos contra o total publicado pelo IBGE em pelo menos 2 anos. Evidência: estimativa 2012 igual ao total publicado, 6.362.734 (teste em `tests/test_gold_integracao.py`, D30); Censo 2010 igual ao total de SC na 1378, 6.248.436 (`docs/fontes/alertas_qualidade_2026-11.md`, consulta R5); PIB nominal 2010 e 2023 com diferença de +2 e −1 mil reais em relação ao total de SC, por arredondamento (`docs/fontes/sidra_5938.md`, seção 5). Só 2012 é conferido por teste automático.

**Visualização e IA**

- [x] Power BI e Streamlit mostram os mesmos números para uma amostra de municípios e anos. Evidência: `docs/validacao_dashboards.md` (R01–R15, 44 componentes iguais em SQL, Streamlit e Power BI em 26/11/2026; D37).
- [x] Subagents versionados em `.claude/agents/` e usados nas fases de fontes, testes, qualidade e documentação. Evidência: seis subagents versionados; pesquisador-de-fontes (D05–D10), escritor-de-testes (D16), revisor-de-qualidade-de-dados (D22, D26) e documentador (D27), conforme `docs/cronograma.md`.
- [ ] Agente de verificação (Agent SDK) roda pipeline, testes e checagens de qualidade e gera relatório. Parcial: implementado (`python -m brasil_em_dados.verificacao`, D29; checagem R01–R15, D37) e testado (`tests/test_verificacao_*.py`); as execuções reais até 26/11 rodaram só o pytest. Execução com `--coleta --carga --gold` no D39.

**Portfólio**

- [ ] README com objetivo, arquitetura, como rodar, fontes, limitações e prints. Faltam os prints.
- [ ] Repositório público no GitHub, sem credenciais versionadas. Sem credenciais: `.env` fora do histórico, `.env.example` sem senhas, PBIP sem usuário nem senha (D35). Visibilidade pública a confirmar no D39.

## Regras metodológicas

1. **Censo e estimativa nunca se misturam sem rótulo.** O tipo de medida é atributo do indicador (`dim_indicador`), e toda linha herda o tipo pelo indicador.
2. **O PIB é sempre nominal.** Variações entre anos são variação nominal, nunca crescimento econômico.
3. **PIB per capita não é renda.** Nunca tratado como renda média dos moradores.
4. **Ausência é nulo, não zero.** Ausente fica `NULL` e aparece como "sem dado".
5. **O código IBGE é texto de 7 dígitos** e serve de chave em todas as camadas.
6. **O RAW é imutável.** Cada coleta gera arquivo novo com timestamp, URL e parâmetros.
7. **Agentes não alteram dados por conta própria.** Acesso ao banco somente leitura; toda mudança de código passa pela revisão da autora.
8. **Comparações só entre anos comparáveis.** Mudança de metodologia ou cobertura é sinalizada.

## Riscos e pendências

| Risco | Impacto | Mitigação | Verificar em |
| --- | --- | --- | --- |
| Municípios instalados depois de 2010: Pescaria Brava (4212650) e Balneário Rincão (4220000) vêm sem valor (`...`) em 2011 na tabela 6579 e com estimativa a partir de 2012 (ver `docs/fontes/sidra_6579.md`); instalação provavelmente em 1º/01/2013, segundo nota do PDF oficial da estimativa de 2012 | Testes de "295 valores por ano" falham em anos antigos; risco de carregar `...` como zero | Carregar como NULL; regra de cobertura por ano; ausência esperada documentada. **Resolvido (D08, D09, D16, D26):** `NULL` com `sinal_origem`; testes T5 e T6 | D06, D08, D26 |
| Anos sem estimativa populacional oficial | PIB per capita oficial pode usar população de referência diferente da série do projeto | Mapear anos disponíveis; documentar a população usada pelo IBGE. **Resolvido no D09:** denominador oficial em `docs/fontes/ibge_pesquisas_pib_per_capita.md`; exclusões na validação T11 | D07, D09 |
| Setores fora do MVP. Setores (extensão): tabela 5938, variáveis 498, 513, 517, 6575, 525 e 543; sem abertura em 2022–2023 | Pergunta derivada 5 sem resposta no MVP | Setores como extensão, com a mesma URL do PIB (decisão D10) | D10 |
| PIB de 2023 revisado | Valores de 2021–2023 mudam numa revisão do IBGE | **Publicação resolvida no D09:** a tabela 5938 tem 2010–2023. 2021–2023 foram modificados em 19/12/2025, e 2022–2023 seguem sujeitos a revisão; uma nova coleta é carregada como valor revisado e registrada no log (D21). Ver `docs/limitacoes.md` | D09, D21 |
| Limites ou instabilidade da API SIDRA | Extração falha ou incompleta | Lotes, retry com espera, controle de execução | D11, D16 |
| Cronograma apertado no fim de dezembro (MVP previsto para 26/12) | Entrega final atrasa | Folga dos primeiros dias; dias de reserva | Semanal |
