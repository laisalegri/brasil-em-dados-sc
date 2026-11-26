# Cronograma — Brasil em Dados SC

Fonte do plano: quadro do Trello. O CSV exportado do quadro, usado para gerar a tabela, fica fora do repositório. Cada cartão prevê 3 horas.

- **Status:** ✅ concluído · ⬜ pendente · ↪️ absorvido por outro cartão.
- **Data realizada:** data do último commit do cartão, no fuso America/Sao_Paulo.
- **Datas não confirmadas:** uma data que o git não confirma aparece como "data não confirmada". Nenhuma até aqui.

| Status | Cartão | Fase | Data prevista | Data realizada | Entrega |
| --- | --- | --- | --- | --- | --- |
| ✅ | **D01** Definir objetivo, escopo e critérios de sucesso | Fundação e organização | 11/11/26 | 11/11/26 | Revisar pergunta central, público-alvo, indicadores e limites do MVP. |
| ✅ | **D02** Criar repositório e estrutura de pastas | Fundação e organização | 12/11/26 | 11/11/26 | Organizar data/raw, data/processed, notebooks, src, sql, dashboards, tests, docs e .claude/agents. |
| ✅ | **D03** Configurar ambiente Python | Fundação e organização | 13/11/26 | 11/11/26 | Criar ambiente virtual e instalar requests, pandas, sqlalchemy, psycopg, jupyter, python-dotenv e pytest. |
| ✅ | **D04** Configurar Claude Code no projeto | Agentes de desenvolvimento | 14/11/26 | 11/11/26 | Autenticar com Claude Pro, testar no terminal e criar CLAUDE.md com contexto, regras, convenções e comandos. |
| ✅ | **D05** Criar subagents pesquisador-de-fontes e revisor-de-codigo | Agentes de desenvolvimento | 16/11/26 | 12/11/26 | Definir prompts, ferramentas permitidas e escopo em .claude/agents/; testar cada um em uma tarefa pequena. |
| ✅ | **D06** Mapear API de Localidades IBGE | Fontes e dicionário | 17/11/26 | 12/11/26 | Com o pesquisador-de-fontes: validar endpoint de municípios de SC, campos e códigos IBGE; salvar amostra. |
| ✅ | **D07** Investigar SIDRA: população | Fontes e dicionário | 18/11/26 | 12/11/26 | Com o pesquisador-de-fontes: validar tabela 6579, variável 9324 e anos disponíveis; distinguir estimativas e censos. |
| ✅ | **D08** Investigar SIDRA: Censo 2010 e 2022 | Fontes e dicionário | 19/11/26 | 12/11/26 | Validar tabelas 1378 e 4709, variáveis e filtros de total; confirmar municípios instalados após 2010. |
| ✅ | **D09** Investigar SIDRA: PIB e PIB per capita | Fontes e dicionário | 20/11/26 | 12/11/26 | Validar tabela 5938, variável 37, período 2010–2023 e unidades; localizar o PIB per capita publicado pelo IBGE. |
| ✅ | **D10** Investigar setores e consolidar dicionário | Fontes e dicionário | 21/11/26 | 12/11/26 | Conferir tabela candidata 5964 e códigos setoriais; consolidar o dicionário de dados em docs/. |
| ✅ | **D11** Desenhar padrão de coleta e rastreabilidade | Extração RAW | 23/11/26 | 14/11/26 | Definir nomes de arquivos, timestamp, URL, parâmetros, logs, erros e reexecução. |
| ✅ | **D12** Criar extrator de municípios | Extração RAW | 24/11/26 | 14/11/26 | Consumir API de Localidades, salvar JSON bruto e validar 295 municípios e códigos únicos. |
| ✅ | **D13** Criar extrator de população | Extração RAW | 25/11/26 | 14/11/26 | Consumir tabelas SIDRA validadas, salvar respostas brutas e metadados. |
| ✅ | **D14** Criar extrator de PIB | Extração RAW | 26/11/26 | 14/11/26 | Consumir a tabela 5938 (PIB, variável 37) e a API de Pesquisas (PIB per capita, indicador 47001) para 2010–2023 e salvar JSON bruto. |
| ↪️ | **D15** Criar controle de execução | Extração RAW | 27/11/26 | Absorvido pelo D11 | **Absorvido pelo D11.** Registrar endpoint, parâmetros, status, quantidade de registros, duração e erros. |
| ✅ | **D16** Criar subagent escritor-de-testes e testar falhas | Extração RAW | 28/11/26 | 14/11/26 | Configurar o subagent; gerar com ele testes de timeout, erro HTTP, resposta vazia e não sobrescrita do RAW. |
| ✅ | **D17** Criar banco e usuário de projeto | PostgreSQL e modelagem | 30/11/26 | 17/11/26 | Criar database, usuário de escrita e usuário somente leitura para os agentes; configurar variáveis de ambiente. |
| ✅ | **D18** Criar dim_municipio e dim_indicador | PostgreSQL e modelagem | 01/12/26 | 17/11/26 | Implementar dimensões, chaves, tipos e restrições. |
| ✅ | **D19** Criar fato_indicador_municipio e controle | PostgreSQL e modelagem | 02/12/26 | 17/11/26 | Criar tabela fato, chave única, tipo de medida, unidade, fonte e a tabela `controle_execucao`. |
| ✅ | **D20** Carregar dimensões | PostgreSQL e modelagem | 03/12/26 | 17/11/26 | Popular municípios e catálogo de indicadores; validar contagem e integridade. |
| ✅ | **D21** Carregar a fato e o controle a partir da RAW | PostgreSQL e modelagem | 04/12/26 | 18/11/26 | Ler JSONs e inserir dados preservando proveniência. Sem tabela de estágio: o parse é em memória e grava direto na fato (decisão D21). Absorve D23, D24 e D25. |
| ✅ | **D22** Criar subagent revisor-de-qualidade-de-dados | SILVER: qualidade e tratamento | 05/12/26 | 18/11/26 | Configurar subagent com acesso SQL somente leitura para revisar nulos, duplicidades, chaves, cobertura e regras. |
| ↪️ | **D23** Normalizar população | SILVER: qualidade e tratamento | 07/12/26 | Absorvido pelo D21 | **Absorvido pelo D21.** Padronizar código IBGE como texto, ano, valor, unidade e tipo de medida. |
| ↪️ | **D24** Normalizar PIB municipal | SILVER: qualidade e tratamento | 08/12/26 | Absorvido pelo D21 | **Absorvido pelo D21.** Padronizar valor monetário, ano e município; identificar ausências e inconsistências. |
| ↪️ | **D25** Tratar população censitária e estimada | SILVER: qualidade e tratamento | 09/12/26 | Absorvido pelo D21 | **Absorvido pelo D21.** Manter censo e estimativa identificados; não preencher lacunas com zero. |
| ✅ | **D26** Validar qualidade e criar testes automatizados | SILVER: qualidade e tratamento | 10/12/26 | 18/11/26 | Rodar o revisor-de-qualidade e transformar os achados em pytest com o escritor-de-testes. |
| ✅ | **D27** Criar subagent documentador e documentar limitações | SILVER: qualidade e tratamento | 11/12/26 | 18/11/26 | Configurar subagent para README, dicionário e metodologia; registrar lacunas, limitações e cautelas com PIB nominal. |
| ✅ | **D28** Estudar ciclo básico do Agent SDK em Python | Claude Agent SDK | 12/12/26 | 20/11/26 | Entender cliente, sessão, prompt, ferramentas e permissões; autenticação pelo plano Pro (sem chave de API). |
| ✅ | **D29** Construir agente de verificação do pipeline | Claude Agent SDK | 14/12/26 | 20/11/26 | Agente que roda pipeline e pytest, executa checagens de qualidade read-only e gera relatório em markdown. |
| ✅ | **D30** Construir camada GOLD | GOLD e análise exploratória | 15/12/26 | 18/11/26 | Criar views/tabelas analíticas para população, PIB e PIB per capita. |
| ✅ | **D31** Analisar população e evolução municipal | GOLD e análise exploratória | 16/12/26 | 23/11/26 | Explorar distribuição, variações e municípios com maior/menor população. |
| ✅ | **D32** Analisar PIB e estrutura econômica | GOLD e análise exploratória | 17/12/26 | 23/11/26 | Comparar PIB corrente e composição setorial apenas em anos comparáveis. |
| ✅ | **D33** Produzir EDA e conclusões | GOLD e análise exploratória | 18/12/26 | 23/11/26 | Criar notebooks reproduzíveis, gráficos, achados e ressalvas. |
| ✅ | **D34** Definir narrativa e KPIs | Dashboards | 19/12/26 | 24/11/26 | Desenhar páginas, filtros, métricas e perguntas respondidas por cada visual. |
| ✅ | **D36** Construir app Streamlit | Dashboards | 22/12/26 | 26/11/26 | **Feito antes do D35** (decisão de 24/11). Criar filtros por município, ano e indicador usando a camada analítica. |
| ✅ | **D35** Construir dashboard Power BI | Dashboards | 21/12/26 | 26/11/26 | Conectar à camada GOLD e criar páginas de visão geral e comparação municipal, com o app Streamlit como referência. |
| ✅ | **D37** Validar consistência entre dashboards | Dashboards | 23/12/26 | 26/11/26 | Comparar amostras e totais entre SQL, Power BI e Streamlit; incluir a checagem no agente de verificação. |
| ✅ | **D38** Revisão final com subagents | Integração e entrega | 24/12/26 | 26/11/26 | Rodar revisor-de-codigo e documentador no repositório inteiro; aplicar correções. |
| ⬜ | **D39** Pipeline do zero, README e portfólio | Integração e entrega | 26/12/26 | — | Executar pipeline do zero com o agente de verificação, rodar testes, revisar README e publicar no GitHub. |
| ⬜ | **D40** Publicar Streamlit (extensão) | Extensão | 28/12/26 | — | Exportar GOLD para Parquet/DuckDB e publicar no Streamlit Community Cloud, sem agente. |
| ⬜ | **D41** Reserva | Reserva | 29/12/26 | — | Dia livre para absorver atrasos. |
| ⬜ | **D42** Reserva | Reserva | 30/12/26 | — | Dia livre para absorver atrasos. |

O MVP fecha no D39 (26/12/26). D40 é extensão (publicar Streamlit) e D41–D42 são reserva.

### Pendências para o D41/D42 (da revisão do D38)

Achados da revisão final que não bloqueiam o MVP. Nenhum muda dados nem números de referência.

1. Centralizar os textos de aviso, hoje em `dashboard/textos.py`, nas medidas `Aviso ...` do `Medidas.tmdl` e no `gerar_pbir.py`. Até lá, `tests/test_powerbi.py` garante que são iguais.
2. Centralizar formatadores, paleta e quebras de base da estimativa, repetidos em `analise/graficos.py`, `dashboard/textos.py`, `dashboard/calculos.py`, `dashboard/figuras.py` e `scripts/powerbi/gerar_pbir.py`.
3. Agrupar e destacar regiões pelo código (`cod_regiao`), usando o nome só como rótulo (`analise/calculos.py`, `dashboard/calculos.py`, página População).
4. Proteger `analise.calculos.variacao_entre_anos` e `participacao_no_total` contra linhas municipais de `pop_estimada` 2012 (regra 13), ou documentar que a entrada vem de `agregado_regiao_ano`.
5. Montar os textos do limite de 50% a partir de `LIMITE_SALTO_PERCENTUAL` (app e nomes das medidas ECO4).
6. Mover para `sql/` o SQL que ainda está em Python (controle de execução, carga da fato, registro do DDL, `aplicar_gold`), ou registrar a exceção em `docs/decisoes.md`.
7. `scripts/estudo_agent_sdk.py`: importar as listas de credenciais de `verificacao/seguranca.py`, em vez de repeti-las.
8. Consulta repetida em `sql/analise/cobertura.sql` e `sql/verificacao/status_grade_gold.sql`: unificar ou testar que são iguais.
9. Testes T19–T28 da GOLD propostos pelo revisor de qualidade (`reports/qualidade_20261126.md`, local).
10. Power BI: o título do PER3b com Censo ausente ainda diz "sem dado pessoas em 2010" (o Streamlit foi corrigido no D38); o aviso do denominador do per capita não cita a relação do TCU de 2023 (`docs/limitacoes.md`, seção 9), no app e no TMDL.
11. Tabela versionada de anos esperados por série (pendência do D30).

## Detalhes do realizado

As datas realizadas foram reconstruídas em 20/11/2026 a partir do `git log` e de `docs/decisoes.md`.

- **Consulta usada:** `TZ=America/Sao_Paulo git log --date=format-local:'%d/%m/%Y %H:%M'`.
- **Atribuição dos commits:** as mensagens não citam o cartão. Cada commit foi atribuído pelo cartão que ele marcou como ✅ no cronograma e pelos arquivos que alterou.

### Resumo (até 26/11/2026)

| | Previsto | Realizado |
|---|---|---|
| Cartões D01–D30 | 30 cartões em 30 dias de trabalho (11/11 a 15/12) | 26 concluídos e 4 absorvidos, em 6 dias com commits (11, 12, 14, 17, 18 e 20/11) |
| Cartões D31–D33 | 3 cartões em 3 dias (16 a 18/12) | 3 concluídos em 23/11 |
| Cartões D34 a D38 | 5 cartões (19, 21, 22, 23 e 24/12) | Concluídos em 24/11 (D34) e 26/11 (D35 a D38) |
| Cartões pendentes | — | 4 (D39 a D42) |
| Fechamento do MVP | D39, em 26/12 | Em andamento |

Os dias de trabalho realizados contam só os dias com commit; um dia de trabalho sem commit não aparece no git. Cada cartão previa 3 horas.

#### Mudanças de escopo relevantes

- **Setores do PIB fora do MVP** (D10, 12/11):
  - o valor adicionado por setor virou extensão, porque a série setorial termina em 2021 e a pergunta central não inclui a estrutura produtiva;
  - a tabela candidata 5964 foi descartada, porque é da PeNSE 2015.
- **Agentes para o desenvolvimento** (D01, 11/11):
  - os agentes de IA apoiam o desenvolvimento: subagents do Claude Code e o agente de verificação com o Agent SDK;
  - o agente de perguntas de negócio para usuários finais virou extensão.
- **`dim_serie` separada da `dim_indicador`** (ajuste na revisão do dicionário, D10, 12/11):
  - a origem técnica (tabela ou variável, unidade de origem, fator de conversão, data de referência) foi para uma dimensão própria, e cada linha da fato aponta para a sua série;
  - isso permite um `pop_censo` único com duas origens (1378 e 4709).
- **GOLD em views** (D30, 18/11): a camada GOLD são views recriadas por `aplicar_gold`, e não tabelas, e fica fora do controle `ddl_aplicado`.
- **Cartões absorvidos:**
  - o controle de execução (D15) entrou no padrão de coleta (D11);
  - as normalizações da SILVER (D23–D25) entraram na carga da fato (D21), que faz o parse em memória, sem tabela de estágio.
- **Ordem diferente do plano:**
  - a GOLD (D30) foi feita antes do Agent SDK (D28–D29);
  - a autenticação do agente passou a ser pelo plano Pro, sem chave de API e sem teto de gasto (decisão de 20/11);
  - o Streamlit (D36) passa a ser feito antes do Power BI (D35), para servir de referência a ele (decisão de 24/11). As datas previstas dos dois não mudam.

### Entregas e commits por cartão

| Cartão | Principais entregas | Commits |
| --- | --- | --- |
| D01 | `docs/escopo_mvp.md` e decisão D01 | `b2af207` |
| D02 | Estrutura de pastas, `.gitignore` e decisão D02 (dados brutos fora do git) | `b2af207` |
| D03 | `requirements.txt`, `pyproject.toml` e teste do ambiente | `ef5bafc` |
| D04 | `CLAUDE.md`, `.claude/settings.json` (negação de leitura do `.env`) e cronograma | `80b0ea5` |
| D05 | Os dois subagents, testados numa primeira investigação da 6579 | `560e5c9` |
| D06 | `docs/fontes/ibge_localidades.md`, amostra em `tests/fixtures/` e decisão D06 | `36f2b73` |
| D07 | `docs/fontes/sidra_6579.md`, convenções de sinais do SIDRA e decisão D07 (`sinal_origem`) | `560e5c9`, `0770138`, `0e3cd36` |
| D08 | `sidra_1378.md`, `sidra_4709.md`, datas de referência dos censos e decisão D08 | `b2603dc`, `3e43009` |
| D09 | `sidra_5938.md`, per capita pela API de Pesquisas, conversão para reais e decisão D09 | `be729fc`, `e77134e` |
| D10 | `docs/dicionario_dados.md`, setores fora do MVP, `dim_serie` e decisão D10 | `2f389cd` |
| D11 | `docs/padrao_coleta.md` (RAW imutável, metadados, controle de execução) e decisão D11 | `fca6017`, `f0705bd` |
| D12 | Módulos comuns de coleta (HTTP, RAW, controle, catálogo) e extrator da API de Localidades | `b52240f`, `df7b4b2` |
| D13 | Extratores SIDRA com validação de conteúdo e linha de comando `extract` | `b52240f`, `df7b4b2` |
| D14 | Extrator da 5938 e da API de Pesquisas (indicador 47001) | `b52240f`, `df7b4b2` |
| D15 | Controle de execução definido no padrão de coleta e implementado nos módulos comuns | `fca6017`, `b52240f` |
| D16 | Subagent escritor-de-testes, testes de falhas de coleta e HTTP, códigos conferidos no cadastro e decisão D16 | `776c49d` |
| D17 | `00_banco_e_usuarios.sql`, conexões `bed_app` e `bed_readonly` e decisão D17 | `b93bca1` |
| D18 | Schemas e dimensões com restrições, `aplicar_ddl` com `ddl_aplicado` e decisão D18/D19 | `7927d9b` |
| D19 | Fato com FK composta para a série, `controle_execucao` e regras de dados no banco | `7927d9b` |
| D20 | Carga idempotente das dimensões (RAW e catálogo), atributos imutáveis e decisão D20 | `ae9a70c` |
| D21 | Carga da fato com conversão em `Decimal`, carga do controle e decisão D21 | `2a942eb` |
| D22 | Subagent somente leitura (`bed_readonly`, `SET TRANSACTION READ ONLY`) | `310b5d1`, `1a9e7a5` |
| D23 | Normalização feita na carga da fato | `2a942eb` |
| D24 | Normalização feita na carga da fato | `2a942eb` |
| D25 | Censo e estimativa separados pelo `tipo_medida` desde a carga | `2a942eb` |
| D26 | 14 testes de qualidade (T1 a T16, sem T9 e T12), alertas investigados em fontes oficiais, regras 12 e 13 e decisão D26 | `310b5d1`, `1a9e7a5`, `4fe3c4f`, `08539dc` |
| D27 | Subagent documentador, `docs/limitacoes.md`, `docs/metodologia.md` e README | `79e09ae` |
| D28 | Autenticação pelo plano Pro, `scripts/estudo_agent_sdk.py` com a trava de credenciais e `docs/estudo_agent_sdk.md` | `bc87853`, `769081d` |
| D29 | `python -m brasil_em_dados.verificacao`: executor determinístico, agente Sonnet com ferramentas de leitura, relatório em `reports/` e decisão D29 | `a76cd5b` |
| D30 | Sete views em `sql/gold/`, `aplicar_gold` e decisão D30 | `f4eb2bd` |
| D31 | Pacote `brasil_em_dados.analise` (consultas em `sql/analise/`, cálculos e gráficos), `notebooks/01_populacao.ipynb`, correção da variação do PIB em `gold.variacao_anual` e decisão D31 | `1d5f587` |
| D32 | `notebooks/02_pib.ipynb`: PIB nominal, concentração, participação 2010 × 2023, PIB per capita 2023 e regiões | `1d5f587` |
| D33 | `notebooks/03_conclusoes.ipynb` e teste que executa os três notebooks | `1d5f587` |
| D34 | `docs/dashboards.md`: narrativa, seis páginas com 24 visuais, filtros globais, proibições e 15 números de referência para o D37; D36 antes do D35 e decisão D34 | `bb582ae` |
| D36 | App Streamlit em `dashboards/streamlit/` (Início e seis páginas, filtros globais com `st.navigation`), pacote `brasil_em_dados.dashboard`, cinco consultas novas em `sql/analise/`, testes com AppTest (R01–R15, Censo fixo, erro de conexão sem detalhes), streamlit e plotly fixados e decisão D36 | `929556f` |
| D35 | Relatório Power BI em `dashboards/powerbi/` (PBIP: modelo em TMDL e relatório em PBIR), com seis páginas (Início, Visão geral, População, Economia, Perfil e Sobre os dados); modelo pelo Power BI Modeling MCP (relacionamentos só por `cod_municipio`, 189 medidas, R01–R15 conferidos em DAX); gerador e verificador em `scripts/powerbi/`; `.mcp.json`, `.gitignore` dos arquivos locais do PBIP e decisão D35 | `2845e7b` |
| D37 | `docs/validacao_dashboards.md`: R01–R15 iguais em SQL, Streamlit e Power BI (44 componentes, comparados pelo valor); consultas em `sql/referencias/`; checagem SQL × Streamlit no agente de verificação (`referencias_dashboards`) e em `python -m brasil_em_dados.verificacao.referencias`; decisão D37 | `6766243` |
| D38 | Revisão final: revisor-de-codigo (nenhum bloqueante; importantes corrigidos: verificador do PBIR sem falso OK, trava no `gerar_pbir.py`, teste de igualdade dos avisos e do Sobre entre Streamlit e Power BI, testes dos scripts e das figuras e títulos sem teste), documentador (metodologia, limitações, dicionário, escopo com os critérios de sucesso marcados, CLAUDE.md, dashboards.md), varredura do histórico do git sem credenciais, agente de verificação e revisor de qualidade sem ERRO; `lock_timeout` no teste da GOLD; versões das dependências diretas fixadas; pendências para o D41/D42 | — |

Commit fora de cartão: `12d0db4` (12/11/2026), um ajuste do texto do cronograma (fonte do quadro e datas previstas).

### Como registrar um cartão concluído

No commit que conclui o cartão:

- troque ⬜ por ✅ e preencha a "Data realizada" (DD/MM/AA, a data do commit);
- acrescente em "Entregas e commits por cartão" uma linha com as principais entregas.

Um commit não sabe o próprio hash, então os hashes entram no commit seguinte. As datas previstas não mudam.
