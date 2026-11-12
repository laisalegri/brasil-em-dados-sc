# SIDRA 5964: não é uma tabela de setores do PIB

- **Data da consulta:** 2026-11-12

> **Conclusão:** a tabela 5964, listada no CLAUDE.md e no escopo como candidata para "setores", **não tem relação com o PIB**. É uma tabela da Pesquisa Nacional de Saúde do Escolar (PeNSE) 2015. Ela não deve ser usada para a estrutura setorial. Para os setores do PIB municipal, a tabela 5938 basta (ver `sidra_5938.md`, seção "Setores (D10)").

## URLs consultadas

| # | URL | Uso |
|---|-----|-----|
| A | https://servicodados.ibge.gov.br/api/v3/agregados/5964/metadados | Metadados |
| B | https://servicodados.ibge.gov.br/api/v3/agregados/5964/periodos | Períodos |
| C | https://servicodados.ibge.gov.br/api/v3/agregados | Catálogo: tabelas da pesquisa "Produto Interno Bruto dos Municípios" |

## Metadados (fonte: A)

- **Nome:** "Escolares frequentando o 9º ano do ensino fundamental, total e percentual, em escolas que informaram possuir estrutura para assegurar a acessibilidade dos alunos com necessidades especiais, por dependência administrativa da escola"
- **Pesquisa:** "Pesquisa Nacional de Saúde do Escolar"
- **Assunto:** "Características da escola"
- **Periodicidade:** anual, com `inicio` 2015 e `fim` 2015
- **Níveis:**
  - Administrativo: N1, N2, N6, N3
  - IBGE: N130

### Variáveis

| id | Nome resumido | Unidade |
|----|---------------|---------|
| 7371 | Escolares... (total) | Pessoas |
| 7372 | Escolares... (limite inferior do intervalo de confiança de 95%) | Pessoas |
| 7373 | Escolares... (limite superior do intervalo de confiança de 95%) | Pessoas |
| 7374 | Percentual (total) | % |
| 7375 | Percentual (limite inferior) | % |
| 7376 | Percentual (limite superior) | % |

### Classificação

- **556 "Dependência administrativa da escola":**
  - 31050 Total
  - 31052 Pública
  - 31051 Privada

## Períodos (fonte: B)

| Período | Data de modificação |
|---------|---------------------|
| 2015 | 26/08/2016 |

## A 5964 traz algo que a 5938 não tem?

Não. Ela não tem nenhuma variável econômica.

Pelo catálogo (C), a pesquisa "Produto Interno Bruto dos Municípios" tem só quatro tabelas:

| Tabela | Conteúdo | Situação |
|--------|----------|----------|
| 5938 | PIB, impostos e VAB por atividade, Referência 2010 | Em uso |
| 21 | O mesmo conteúdo, Referência 2002 | "Série encerrada" |
| 5939 | Índice de Gini, Referência 2010 | — |
| 599 | Índice de Gini, Referência 2002 | "Série encerrada" |

Nenhuma delas traz setores de 2022–2023. A ausência da abertura setorial nesses anos é da própria publicação (nota técnica 02/2024; ver `sidra_5938.md`).

## Verificado diretamente

- Os metadados e o período da 5964 (A, B).
- A lista de tabelas da pesquisa PIB dos Municípios (C).

## Inferido / não confirmado

- **NÃO CONFIRMADO:** de onde veio o número 5964 como candidato a "setores". Pode ser um engano de digitação ou de memória. Hipótese: confusão com 5938 ou 5939.

## Pendências

- **Decisão da autora:** corrigir a menção à 5964 no CLAUDE.md, no `docs/escopo_mvp.md` e no `docs/decisoes.md` (D01). Não editei esses arquivos.
