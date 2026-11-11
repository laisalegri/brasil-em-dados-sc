# D01 — Escopo do MVP

Versão aprovada em 2026-11-11. Versão viva e comentada: documento "D01 — Escopo do MVP · Brasil em Dados SC".

## Objetivo e pergunta central

O MVP entrega um pipeline reproduzível (RAW → SILVER → GOLD) com população e PIB dos 295 municípios de SC, de 2010 a 2023. Esses dados alimentam dois dashboards. Agentes de IA entram como apoio ao desenvolvimento (subagents do Claude Code e um agente de verificação com o Agent SDK), não como produto final.

**Pergunta central:** como os municípios de Santa Catarina se diferenciam em população e dimensão econômica, e como esses indicadores evoluíram entre 2010 e 2023?

**Perguntas derivadas que o MVP precisa responder:**

1. Quais municípios concentram população e PIB, e quanto representam do total estadual?
2. Como a população de cada município variou entre os Censos de 2010 e 2022?
3. Como o PIB nominal de cada município evoluiu entre 2010 e 2023?
4. Como os municípios se comparam em PIB per capita em um mesmo ano?
5. Qual é a composição setorial da economia de cada município? (condicionada à validação no D10)

## Público-alvo

| Público | O que procura | O que o MVP precisa mostrar |
| --- | --- | --- |
| Recrutadores e avaliadores técnicos | Competência de ponta a ponta | README claro, pipeline que roda do zero, testes, decisões documentadas |
| Analistas e gestores interessados em SC | Comparar municípios e ver tendências | Dashboards com filtros por município, ano e indicador, com fonte e unidade visíveis |
| A própria autora (desenvolvimento com agentes) | Entregar mais rápido sem perder qualidade | Subagents e agente de verificação versionados no repositório e usados no fluxo de trabalho |

## Escopo do MVP

**Recorte:** UF 42 (Santa Catarina), todos os municípios do cadastro atual do IBGE (295) e anos de 2010 a 2023.

| Indicador | Tipo de medida | Fonte (a validar) | Anos esperados | Situação no MVP |
| --- | --- | --- | --- | --- |
| População censitária | Censo | SIDRA 1378 (2010) e 4709, var. 93 (2022) | 2010, 2022 | Incluso |
| População estimada | Estimativa | SIDRA 6579, var. 9324 | Anos intercensitários disponíveis | Incluso |
| PIB a preços correntes | PIB nominal | SIDRA 5938, var. 37 | 2010–2023 | Incluso |
| PIB per capita | Oficial (IBGE) | Valor publicado pelo IBGE; tabela/variável a confirmar no D09 | Anos com PIB publicado | Incluso |
| Valor adicionado por setor | VAB nominal | Tabela candidata 5964 | A confirmar | Extensão, condicionada ao D10 |

**Entregáveis:** extratores com rastreabilidade, banco PostgreSQL (dimensões, fato e controle), camada GOLD, notebooks de EDA, dashboard Power BI, app Streamlit, subagents de desenvolvimento e agente de verificação do pipeline.

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

**Dados e pipeline**

- [ ] `dim_municipio` com 295 linhas, código IBGE de 7 dígitos, armazenado como texto e único
- [ ] Cada valor da tabela fato ligado a fonte, tabela/variável SIDRA, tipo de medida, unidade e data de coleta
- [ ] Nenhuma duplicidade na chave (município, indicador, ano, tipo de medida)
- [ ] Nenhum dado ausente preenchido com zero; cobertura por indicador e ano documentada
- [ ] Pipeline roda do zero (RAW → GOLD) com um comando documentado no README
- [ ] Reexecutar o pipeline não sobrescreve o RAW nem duplica dados

**Qualidade**

- [ ] Testes do pytest passando para esquema, contagens, chaves, tipos e regras de negócio
- [ ] Totais de SC na GOLD conferidos contra o total publicado pelo IBGE em pelo menos 2 anos

**Visualização e IA**

- [ ] Power BI e Streamlit mostram os mesmos números para uma amostra de municípios e anos
- [ ] Subagents versionados em `.claude/agents/` e usados nas fases de fontes, testes, qualidade e documentação
- [ ] Agente de verificação (Agent SDK) roda pipeline, testes e checagens de qualidade e gera relatório

**Portfólio**

- [ ] README com objetivo, arquitetura, como rodar, fontes, limitações e prints
- [ ] Repositório público no GitHub, sem credenciais versionadas

## Regras metodológicas

1. **Censo e estimativa nunca se misturam sem rótulo.** Toda linha de população carrega o tipo de medida.
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
| Municípios instalados depois de 2010 (provavelmente Balneário Rincão e Pescaria Brava, em 2013) | Testes de "295 por ano" falham em anos antigos | Regra de cobertura por ano; ausência esperada documentada | D06, D08, D26 |
| Anos sem estimativa populacional oficial | PIB per capita oficial pode usar população de referência diferente da série do projeto | Mapear anos disponíveis; documentar a população usada pelo IBGE | D07, D09 |
| Tabela de setores (5964) não confirmada | Pergunta derivada 5 sem resposta | Setores como extensão | D10 |
| PIB de 2023 não publicado ou revisado | Série termina em 2022 | Confirmar último ano; ajustar recorte | D09 |
| Limites ou instabilidade da API SIDRA | Extração falha ou incompleta | Lotes, retry com espera, controle de execução | D11, D16 |
| Cronograma apertado no fim de dezembro (MVP previsto para 26/12) | Entrega final atrasa | Folga dos primeiros dias; dias de reserva | Semanal |
