# Cronograma — Brasil em Dados SC

Fonte da verdade: quadro do Trello (importado de `trello_brasil_em_dados_sc_v2.csv`). Cada cartão prevê 3 horas. Status: ✅ concluído · ⬜ pendente.

| Status | Data | Cartão | Fase | Entrega |
| --- | --- | --- | --- | --- |
| ✅ | 11/11 | **D01** Definir objetivo, escopo e critérios de sucesso | Fundação e organização | Revisar pergunta central, público-alvo, indicadores e limites do MVP. |
| ✅ | 12/11 | **D02** Criar repositório e estrutura de pastas | Fundação e organização | Organizar data/raw, data/processed, notebooks, src, sql, dashboards, tests, docs e .claude/agents. |
| ✅ | 13/11 | **D03** Configurar ambiente Python | Fundação e organização | Criar ambiente virtual e instalar requests, pandas, sqlalchemy, psycopg, jupyter, python-dotenv e pytest. |
| ✅ | 14/11 | **D04** Configurar Claude Code no projeto | Agentes de desenvolvimento | Autenticar com Claude Pro, testar no terminal e criar CLAUDE.md com contexto, regras, convenções e comandos. |
| ⬜ | 16/11 | **D05** Criar subagents pesquisador-de-fontes e revisor-de-codigo | Agentes de desenvolvimento | Definir prompts, ferramentas permitidas e escopo em .claude/agents/; testar cada um em uma tarefa pequena. |
| ⬜ | 17/11 | **D06** Mapear API de Localidades IBGE | Fontes e dicionário | Com o pesquisador-de-fontes: validar endpoint de municípios de SC, campos e códigos IBGE; salvar amostra. |
| ⬜ | 18/11 | **D07** Investigar SIDRA: população | Fontes e dicionário | Com o pesquisador-de-fontes: validar tabela 6579, variável 9324 e anos disponíveis; distinguir estimativas e censos. |
| ⬜ | 19/11 | **D08** Investigar SIDRA: Censo 2010 e 2022 | Fontes e dicionário | Validar tabelas 1378 e 4709, variáveis e filtros de total; confirmar municípios instalados após 2010. |
| ⬜ | 20/11 | **D09** Investigar SIDRA: PIB e PIB per capita | Fontes e dicionário | Validar tabela 5938, variável 37, período 2010–2023 e unidades; localizar o PIB per capita publicado pelo IBGE. |
| ⬜ | 21/11 | **D10** Investigar setores e consolidar dicionário | Fontes e dicionário | Conferir tabela candidata 5964 e códigos setoriais; consolidar o dicionário de dados em docs/. |
| ⬜ | 23/11 | **D11** Desenhar padrão de coleta e rastreabilidade | Extração RAW | Definir nomes de arquivos, timestamp, URL, parâmetros, logs, erros e reexecução. |
| ⬜ | 24/11 | **D12** Criar extrator de municípios | Extração RAW | Consumir API de Localidades, salvar JSON bruto e validar 295 municípios e códigos únicos. |
| ⬜ | 25/11 | **D13** Criar extrator de população | Extração RAW | Consumir tabelas SIDRA validadas, salvar respostas brutas e metadados. |
| ⬜ | 26/11 | **D14** Criar extrator de PIB | Extração RAW | Consumir tabela 5938 (PIB e PIB per capita) para 2010–2023 e salvar JSON bruto. |
| ⬜ | 27/11 | **D15** Criar controle de execução | Extração RAW | Registrar endpoint, parâmetros, status, quantidade de registros, duração e erros. |
| ⬜ | 28/11 | **D16** Criar subagent escritor-de-testes e testar falhas | Extração RAW | Configurar o subagent; gerar com ele testes de timeout, erro HTTP, resposta vazia e não sobrescrita do RAW. |
| ⬜ | 30/11 | **D17** Criar banco e usuário de projeto | PostgreSQL e modelagem | Criar database, usuário de escrita e usuário somente leitura para os agentes; configurar variáveis de ambiente. |
| ⬜ | 01/12 | **D18** Criar dim_municipio e dim_indicador | PostgreSQL e modelagem | Implementar dimensões, chaves, tipos e restrições. |
| ⬜ | 02/12 | **D19** Criar fato_indicador_municipio e controle | PostgreSQL e modelagem | Criar tabela fato, chave única, tipo de medida, unidade, fonte e controle de execução. |
| ⬜ | 03/12 | **D20** Carregar dimensões | PostgreSQL e modelagem | Popular municípios e catálogo de indicadores; validar contagem e integridade. |
| ⬜ | 04/12 | **D21** Carregar dados RAW no estágio de trabalho | PostgreSQL e modelagem | Ler JSONs e inserir dados preservando proveniência. |
| ⬜ | 05/12 | **D22** Criar subagent revisor-de-qualidade-de-dados | SILVER: qualidade e tratamento | Configurar subagent com acesso SQL somente leitura para revisar nulos, duplicidades, chaves, cobertura e regras. |
| ⬜ | 07/12 | **D23** Normalizar população | SILVER: qualidade e tratamento | Padronizar código IBGE como texto, ano, valor, unidade e tipo de medida. |
| ⬜ | 08/12 | **D24** Normalizar PIB municipal | SILVER: qualidade e tratamento | Padronizar valor monetário, ano e município; identificar ausências e inconsistências. |
| ⬜ | 09/12 | **D25** Tratar população censitária e estimada | SILVER: qualidade e tratamento | Manter censo e estimativa identificados; não preencher lacunas com zero. |
| ⬜ | 10/12 | **D26** Validar qualidade e criar testes automatizados | SILVER: qualidade e tratamento | Rodar o revisor-de-qualidade e transformar os achados em pytest com o escritor-de-testes. |
| ⬜ | 11/12 | **D27** Criar subagent documentador e documentar limitações | SILVER: qualidade e tratamento | Configurar subagent para README, dicionário e metodologia; registrar lacunas, limitações e cautelas com PIB nominal. |
| ⬜ | 12/12 | **D28** Estudar ciclo básico do Agent SDK em Python | Claude Agent SDK | Entender cliente, sessão, prompt, ferramentas, permissões e autenticação por chave de API; definir teto de gasto. |
| ⬜ | 14/12 | **D29** Construir agente de verificação do pipeline | Claude Agent SDK | Agente que roda pipeline e pytest, executa checagens de qualidade read-only e gera relatório em markdown. |
| ⬜ | 15/12 | **D30** Construir camada GOLD | GOLD e análise exploratória | Criar views/tabelas analíticas para população, PIB e PIB per capita. |
| ⬜ | 16/12 | **D31** Analisar população e evolução municipal | GOLD e análise exploratória | Explorar distribuição, variações e municípios com maior/menor população. |
| ⬜ | 17/12 | **D32** Analisar PIB e estrutura econômica | GOLD e análise exploratória | Comparar PIB corrente e composição setorial apenas em anos comparáveis. |
| ⬜ | 18/12 | **D33** Produzir EDA e conclusões | GOLD e análise exploratória | Criar notebooks reproduzíveis, gráficos, achados e ressalvas. |
| ⬜ | 19/12 | **D34** Definir narrativa e KPIs | Dashboards | Desenhar páginas, filtros, métricas e perguntas respondidas por cada visual. |
| ⬜ | 21/12 | **D35** Construir dashboard Power BI | Dashboards | Conectar à camada GOLD e criar páginas de visão geral e comparação municipal. |
| ⬜ | 22/12 | **D36** Construir app Streamlit | Dashboards | Criar filtros por município, ano e indicador usando a camada analítica. |
| ⬜ | 23/12 | **D37** Validar consistência entre dashboards | Dashboards | Comparar amostras e totais entre SQL, Power BI e Streamlit; incluir a checagem no agente de verificação. |
| ⬜ | 24/12 | **D38** Revisão final com subagents | Integração e entrega | Rodar revisor-de-codigo e documentador no repositório inteiro; aplicar correções. |
| ⬜ | 26/12 | **D39** Pipeline do zero, README e portfólio | Integração e entrega | Executar pipeline do zero com o agente de verificação, rodar testes, revisar README e publicar no GitHub. |
| ⬜ | 28/12 | **D40** Publicar Streamlit (extensão) | Extensão | Exportar GOLD para Parquet/DuckDB e publicar no Streamlit Community Cloud, sem agente. |
| ⬜ | 29/12 | **D41** Reserva | Reserva | Dia livre para absorver atrasos. |
| ⬜ | 30/12 | **D42** Reserva | Reserva | Dia livre para absorver atrasos. |

O MVP fecha no D39 (26/12). D40 é extensão (publicar Streamlit) e D41–D42 são reserva.
