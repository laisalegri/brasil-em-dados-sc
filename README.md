# Brasil em Dados — Santa Catarina

Pipeline de dados públicos do IBGE para analisar população, PIB e PIB per capita dos 295 municípios de Santa Catarina entre 2010 e 2023, com arquitetura em camadas (RAW → SILVER → GOLD), PostgreSQL, dashboards em Power BI e Streamlit e agentes de IA apoiando o desenvolvimento.

> **Status:** em desenvolvimento. Concluído até o D27: coleta RAW, banco, carga na SILVER, testes de qualidade e documentação de limitações e metodologia. Próximos: agente de verificação (D28–D29), camada GOLD (D30), EDA (D31–D33) e dashboards (D34–D37). Cronograma em [docs/cronograma.md](docs/cronograma.md).

## Pergunta central

Como os municípios de Santa Catarina se diferenciam em população e dimensão econômica, e como esses indicadores evoluíram entre 2010 e 2023?

## O que já funciona

| Etapa | Situação |
|---|---|
| Coleta das APIs do IBGE para a RAW, com validação e controle de execução | Pronto |
| Banco PostgreSQL com schemas `silver` e `gold`, usuários de escrita e somente leitura | Pronto |
| Carga da SILVER: 295 municípios, 4 indicadores, 5 séries, 12.093 linhas na fato | Pronto |
| Testes automatizados (pytest), incluindo testes de qualidade sobre o banco | Pronto |
| Camada GOLD | Planejado (D30); o schema existe, sem tabelas |
| Notebooks de EDA, Power BI e Streamlit | Planejado (D31–D37) |
| Agente de verificação com o Claude Agent SDK | Planejado (D28–D29) |

## Arquitetura

```
IBGE (API de Localidades, API SIDRA, API de Pesquisas)
        │  python -m brasil_em_dados.extract todas
        ▼
   RAW  data/raw/ — resposta original + metadados de coleta, imutável
        │  python -m brasil_em_dados.load tudo
        ▼
 SILVER PostgreSQL (schema silver): dimensões, fato e controle de execução
        │  (D30, planejado)
        ▼
  GOLD  PostgreSQL (schema gold) ──► Power BI · Streamlit · notebooks de EDA (planejados)
```

Detalhes do fluxo em [docs/metodologia.md](docs/metodologia.md).

Agentes de desenvolvimento: subagents do Claude Code em `.claude/agents/` (pesquisador de fontes, revisor de código, escritor de testes, revisor de qualidade de dados e documentador). O agente de verificação do pipeline, com o Claude Agent SDK, ainda será construído (D28–D29).

## Estrutura do repositório

| Pasta | Conteúdo |
| --- | --- |
| `.claude/agents/` | Subagents do Claude Code usados no desenvolvimento |
| `src/brasil_em_dados/` | Código do pipeline: `extract` (coleta), `transform` (interpretação e conversão, sem I/O), `load` (carga), `db` (conexões e aplicador de DDL) |
| `sql/ddl/` | Criação do banco, dos usuários, dos schemas e das tabelas |
| `sql/silver/`, `sql/gold/` | Scripts das camadas (vazios por enquanto) |
| `tests/` | Testes automatizados (pytest) |
| `docs/` | Escopo, decisões, dicionário de dados, padrão de coleta, metodologia, limitações e fontes |
| `data/raw/`, `data/controle/`, `data/processed/` | Gerados pelo pipeline (não versionados) |
| `logs/`, `reports/` | Logs do pipeline e relatórios de qualidade (não versionados) |
| `notebooks/`, `dashboards/` | EDA, Power BI e Streamlit (vazios por enquanto) |

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
