# Brasil em Dados — Santa Catarina

Pipeline de dados públicos do IBGE para analisar população, PIB e PIB per capita dos 295 municípios de Santa Catarina entre 2010 e 2023, com arquitetura em camadas (RAW → SILVER → GOLD), PostgreSQL, dashboards em Power BI e Streamlit e agentes de IA apoiando o desenvolvimento.

> **Status:** em desenvolvimento. Concluído: coleta RAW, banco, carga na SILVER, testes de qualidade, documentação de limitações e metodologia, camada GOLD (D30), agente de verificação (D28–D29) e análise exploratória em notebooks (D31–D33). Próximos: dashboards (D34–D37). Cronograma, com datas previstas e realizadas, em [docs/cronograma.md](docs/cronograma.md).

## Pergunta central

Como os municípios de Santa Catarina se diferenciam em população e dimensão econômica, e como esses indicadores evoluíram entre 2010 e 2023?

## O que já funciona

| Etapa | Situação |
|---|---|
| Coleta das APIs do IBGE para a RAW, com validação e controle de execução | Pronto |
| Banco PostgreSQL com schemas `silver` e `gold`, usuários de escrita e somente leitura | Pronto |
| Carga da SILVER: 295 municípios, 4 indicadores, 5 séries, 12.093 linhas na fato | Pronto |
| Testes automatizados (pytest), incluindo testes de qualidade sobre o banco | Pronto |
| Camada GOLD: 7 views (grade, painel, variações, agregados e participação) | Pronto |
| Notebooks de EDA (população, PIB e conclusões), lendo só a GOLD | Pronto |
| Power BI e Streamlit | Planejado (D34–D37) |
| Agente de verificação com o Claude Agent SDK | Pronto |

## Arquitetura

```
IBGE (API de Localidades, API SIDRA, API de Pesquisas)
        │  python -m brasil_em_dados.extract todas
        ▼
   RAW  data/raw/ — resposta original + metadados de coleta, imutável
        │  python -m brasil_em_dados.load tudo
        ▼
 SILVER PostgreSQL (schema silver): dimensões, fato e controle de execução
        │  python -m brasil_em_dados.db.aplicar_gold
        ▼
  GOLD  PostgreSQL (schema gold), views ──► notebooks de EDA · Power BI e Streamlit (planejados)
```

Detalhes do fluxo em [docs/metodologia.md](docs/metodologia.md).

Agentes de desenvolvimento: subagents do Claude Code em `.claude/agents/` (pesquisador de fontes, revisor de código, escritor de testes, revisor de qualidade de dados e documentador). O agente de verificação do pipeline, feito com o Claude Agent SDK, está descrito em [Agente de verificação](#agente-de-verificação).

## Estrutura do repositório

| Pasta | Conteúdo |
| --- | --- |
| `.claude/agents/` | Subagents do Claude Code usados no desenvolvimento |
| `src/brasil_em_dados/` | Código do pipeline: `extract` (coleta), `transform` (interpretação e conversão, sem I/O), `load` (carga), `db` (conexões e aplicadores de DDL e da GOLD), `verificacao` (agente de verificação), `analise` (consultas, cálculos e gráficos da EDA) |
| `sql/ddl/` | Criação do banco, dos usuários, dos schemas e das tabelas |
| `sql/gold/` | Views da camada GOLD |
| `sql/verificacao/` | Catálogo fechado de consultas de qualidade do agente de verificação |
| `sql/analise/` | Consultas da EDA, só sobre views da GOLD |
| `scripts/` | Estudos fora do pipeline (exemplo mínimo do Agent SDK) |
| `tests/` | Testes automatizados (pytest) |
| `docs/` | Escopo, decisões, dicionário de dados, padrão de coleta, metodologia, limitações e fontes |
| `data/raw/`, `data/controle/`, `data/processed/` | Gerados pelo pipeline (não versionados) |
| `logs/`, `reports/` | Logs do pipeline e relatórios de qualidade e de verificação (não versionados) |
| `notebooks/` | EDA: população, PIB e conclusões, versionados com as saídas |
| `dashboards/` | Power BI e Streamlit (vazios por enquanto) |

## Como rodar

Pré-requisitos: Windows com PowerShell, Python 3.11+ e PostgreSQL local. Os comandos rodam na raiz do repositório.

**1. Ambiente Python**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

**2. Banco e usuários** (uma vez, como superusuário do PostgreSQL)

```powershell
psql -U postgres -f sql/ddl/00_banco_e_usuarios.sql
psql -U postgres
```

No psql, defina as senhas dos dois usuários:

```
\password bed_app
\password bed_readonly
```

**3. Credenciais**

```powershell
Copy-Item .env.example .env
```

Preencha `PG_PASSWORD` (`bed_app`) e `PG_READONLY_PASSWORD` (`bed_readonly`) no `.env`. O `.env` nunca é versionado.

**4. Schemas e tabelas**

```powershell
python -m brasil_em_dados.db.aplicar_ddl
```

Aplica `sql/ddl/01_*.sql` em diante, uma vez cada, numa transação só. Rodar de novo não reaplica nada.

**5. Coleta e carga**

```powershell
python -m brasil_em_dados.extract todas   # coleta todas as fontes para data/raw/
python -m brasil_em_dados.load tudo       # carrega dimensões, fato e controle na SILVER
```

Também é possível coletar uma série (`python -m brasil_em_dados.extract sidra_5938_v37`) ou carregar só uma parte (`python -m brasil_em_dados.load dimensoes` ou `fato`).

**6. Testes**

```powershell
pytest                          # todos os testes
pytest -m "not integracao"      # só os testes que não precisam do banco
```

Os testes marcados `integracao` são pulados quando o banco não aceita conexão. Os testes de qualidade também são pulados se a fato estiver vazia.

**7. GOLD**

```powershell
python -m brasil_em_dados.db.aplicar_gold   # recria as views de sql/gold/ numa transação
```

## Agente de verificação

Um executor determinístico roda os passos e guarda as saídas; depois, um agente feito com o [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview) lê os resultados e escreve a análise.

```powershell
python -m brasil_em_dados.verificacao                          # só o pytest
python -m brasil_em_dados.verificacao --coleta --carga --gold  # roda também coleta, carga e GOLD
```

- **Executor:** roda sempre o pytest. Coleta, carga e GOLD só rodam com a flag correspondente, e o agente nunca dispara um passo. Se um passo do pipeline falhar, os seguintes não rodam, mas o pytest roda.
- **Agente:** usa o modelo Sonnet, com limite de turnos. Só tem ferramentas próprias de leitura:
  - resultado dos testes;
  - saída dos passos;
  - controle de execução;
  - consultas do catálogo fechado em `sql/verificacao/`;
  - relatório anterior.

  O banco é lido como `bed_readonly`, com `SET TRANSACTION READ ONLY`. O agente não tem Bash nem edição de arquivos, e os conectores da conta do claude.ai são negados. Se a sessão não usar o login do plano, usar outro modelo ou receber qualquer ferramenta além das próprias, o agente é interrompido.
- **Relatório:** `reports/verificacao_AAAAMMDDTHHMMSS.md` (UTC), que nunca é sobrescrito. A parte de execução é escrita pelo código: flags recebidas, usuário do banco de cada passo e consumo do agente (turnos, tokens e custo estimado). A origem da chave da sessão também é registrada. Só a análise vem do modelo. Nenhuma URL de conexão ou senha entra no texto nem nos logs.
- **Autenticação:** pelo login do plano Claude Pro, sem chave de API. Se `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` ou uma variável de provedor de nuvem estiver definida, o agente para antes de rodar qualquer passo.
- **Códigos de saída:**
  - 0: tudo certo;
  - 1: um passo falhou ou não houve análise;
  - 2: a trava de credenciais parou a execução, ou a sessão não usou o login do plano;
  - 3: o agente recebeu ferramentas inesperadas ou outro modelo.

Desenho e motivos: decisão D29 em [docs/decisoes.md](docs/decisoes.md) e estudo em [docs/estudo_agent_sdk.md](docs/estudo_agent_sdk.md).

## Fontes de dados

| Fonte | Uso | Séries |
|---|---|---|
| [IBGE — API de Localidades](https://servicodados.ibge.gov.br/api/docs/localidades) | Cadastro dos 295 municípios e divisões regionais | `ibge_localidades_sc` |
| [IBGE — API SIDRA](https://apisidra.ibge.gov.br/) | População estimada (tabela 6579), Censo 2010 (1378), Censo 2022 (4709) e PIB (5938) | `sidra_6579_v9324`, `sidra_1378_v93`, `sidra_4709_v93`, `sidra_5938_v37` |
| IBGE — API de Pesquisas (`servicodados.ibge.gov.br/api/v1/pesquisas`) | PIB per capita oficial (pesquisa 38, indicador 47001) | `pesquisas_38_i47001` |

URLs completas, unidades e cobertura: [docs/dicionario_dados.md](docs/dicionario_dados.md) e [docs/fontes/](docs/fontes/).

## Validação: PIB / população × PIB per capita

O PIB em reais dividido pela população reproduz o PIB per capita publicado pelo IBGE em todos os pares comparados (auditoria de 2026-11-18; teste T11).

| Pares comparados | Dentro da tolerância | Mediana da diferença relativa |
|---|---|---|
| 3.534 | 3.534 | ≈ 8,4e-7 |

- **Tolerância:** `500 / população + R$ 0,01`. Ela vem do arredondamento do PIB no SIDRA, publicado em inteiros de mil reais.
- **Base:** estimativa (6579) em 2011–2021 e Censo 2022 (4709) em 2023.
- **Exclusões:** 2010 e 2022, cujo denominador oficial não está nas tabelas do projeto, e Içara e Laguna em 2012.

O projeto não recalcula o per capita: a validação só confere a coerência entre as fontes. Detalhes em [docs/metodologia.md](docs/metodologia.md#62-validação-pib--população--per-capita).

## Regras centrais de leitura dos dados

- **PIB é nominal.** Variação de PIB entre anos não é crescimento econômico real.
- **PIB per capita não é renda.** É o valor publicado pelo IBGE, sem recálculo, e o denominador muda conforme o ano.
- **Censo e estimativa não são uma série única.** Métodos e datas de referência são diferentes; cada valor é rotulado pelo tipo de medida.
- **A estimativa tem quebra de série entre 2012 e 2013**, e a soma municipal de 2012 conta duas vezes a população de dois municípios.
- **Ausência não é zero.** Valor ausente fica `NULL`; Pescaria Brava e Balneário Rincão não têm dados antes de 2013, ano de instalação.

Limitações completas, com evidência e tratamento: [docs/limitacoes.md](docs/limitacoes.md).

## Documentação

- [Escopo do MVP](docs/escopo_mvp.md)
- [Metodologia](docs/metodologia.md)
- [Limitações](docs/limitacoes.md)
- [Dicionário de dados](docs/dicionario_dados.md)
- [Padrão de coleta](docs/padrao_coleta.md)
- [Registro de decisões](docs/decisoes.md)
- [Cronograma](docs/cronograma.md)
