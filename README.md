# Brasil em Dados — Santa Catarina

Pipeline de dados públicos do IBGE para analisar população, PIB e PIB per capita dos 295 municípios de Santa Catarina entre 2010 e 2023, com arquitetura em camadas (RAW → SILVER → GOLD), PostgreSQL, dashboards em Power BI e Streamlit e agentes de IA apoiando o desenvolvimento.

> **Status:** em desenvolvimento (D04 concluído — próximo: D05).

## Pergunta central

Como os municípios de Santa Catarina se diferenciam em população e dimensão econômica, e como esses indicadores evoluíram entre 2010 e 2023?

## Arquitetura

```
IBGE (API de Localidades, SIDRA)
        │  extratores Python
        ▼
   RAW  (JSON bruto + metadados de coleta, imutável)
        │  carga
        ▼
 SILVER (PostgreSQL: dados normalizados e validados)
        │  views / tabelas analíticas
        ▼
  GOLD  (PostgreSQL) ──► Power BI · Streamlit · notebooks de EDA
```

Agentes de desenvolvimento: subagents do Claude Code (`.claude/agents/`) e um agente de verificação do pipeline construído com o Claude Agent SDK.

## Estrutura do repositório

| Pasta | Conteúdo |
| --- | --- |
| `.claude/agents/` | Subagents do Claude Code usados no desenvolvimento |
| `data/raw/` | Respostas brutas das APIs (geradas pelo pipeline, não versionadas) |
| `data/processed/` | Exportações intermediárias (não versionadas) |
| `notebooks/` | Análise exploratória (EDA) |
| `src/brasil_em_dados/` | Código do pipeline: `extract`, `load`, `transform` |
| `sql/` | DDL do banco e scripts das camadas SILVER e GOLD |
| `dashboards/` | Arquivo do Power BI e app Streamlit |
| `tests/` | Testes automatizados (pytest) |
| `reports/` | Relatórios do agente de verificação (não versionados) |
| `docs/` | Escopo, decisões, dicionário de dados e metodologia |

## Como rodar

Em construção. Os passos de ambiente (D03), banco (D17) e pipeline serão documentados aqui.

## Fontes

- [IBGE — API de Localidades](https://servicodados.ibge.gov.br/api/docs/localidades)
- [IBGE — API SIDRA](https://apisidra.ibge.gov.br/)

## Documentação

- [Escopo do MVP](docs/escopo_mvp.md)
- [Registro de decisões](docs/decisoes.md)
- [Cronograma](docs/cronograma.md)
