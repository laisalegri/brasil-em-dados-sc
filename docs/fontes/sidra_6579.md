# SIDRA 6579: População residente estimada

- **Data da consulta:** 2026-11-12
- **Recorte:** municípios de Santa Catarina (UF 42), 2010–2023

## URLs consultadas

| # | URL | Uso |
|---|-----|-----|
| A | https://servicodados.ibge.gov.br/api/v3/agregados/6579/metadados | Nome da tabela, pesquisa, periodicidade, níveis, variáveis e classificações |
| B | https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos | Períodos disponíveis e data de modificação |
| C | https://apisidra.ibge.gov.br/values/t/6579/n6/4205407/v/9324/p/2011,2021 | Teste pontual em Florianópolis |
| D | https://apisidra.ibge.gov.br/values/t/6579/n6/4205407/v/9324/p/2010 | Confirmação de ausência em 2010 |
| E | https://apisidra.ibge.gov.br/values/t/6579/n6/4205407/v/9324/p/2022,2023 | Confirmação de ausência em 2022 e 2023 |
| F | https://apisidra.ibge.gov.br/values/t/6579/n6/4205407/v/9324/p/2024 | Teste de um período posterior ao recorte |
| G | https://apisidra.ibge.gov.br/values/t/6579/n6/in%20n3%2042/v/9324/p/2021 | Todos os municípios de SC em 2021 |
| H | https://apisidra.ibge.gov.br/values/t/6579/n6/in%20n3%2042/v/9324/p/2011-2021 | Contagem de municípios de SC por ano |
| I | https://servicodados.ibge.gov.br/api/v1/localidades/estados/42/municipios | Cadastro de municípios de SC, usado para comparação |

## 1. Tabela e pesquisa (fonte: A)

- **Id:** 6579
- **Nome:** "População residente estimada"
- **Pesquisa:** "Estimativas de População"
- **Assunto:** "Geral"
- **Periodicidade:** anual, com `inicio` 2001 e `fim` 2026
- **Página SIDRA:** https://sidra.ibge.gov.br/tabela/6579

## 2. Variáveis (fonte: A; código da unidade em C, G e H)

| id | nome | unidade | código da unidade na API SIDRA (MC) |
|----|------|---------|-------------------------------------|
| 9324 | População residente estimada | Pessoas | 45 |

A única variável da tabela é a 9324.

## 3. Períodos (fonte: B; ausências confirmadas em D e E)

| Período | Data de modificação |
|---------|---------------------|
| 2001–2006 | 30/08/2017 |
| 2008–2009 | 30/08/2017 |
| 2011–2016 | 30/08/2017 |
| 2017–2020 | 05/09/2022 |
| 2021 | 24/06/2024 |
| 2024 | 30/12/2024 |
| 2025–2026 | 28/08/2026 |

**Dentro de 2010–2023:**

- **Presentes (11 anos):** 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021
- **Ausentes (3 anos):** **2010, 2022 e 2023**. Os três estão dentro do recorte. Para eles, as consultas D e E devolveram só a linha de cabeçalho.

Fora do recorte, também falta o ano de 2007.

> Correção do relatório anterior, que dizia que 2023 estava fora do recorte: 2023 está **dentro** de 2010–2023 e não tem estimativa na tabela 6579.

## 4. Níveis territoriais (fonte: A)

- **Administrativo:** N1 (Brasil), N2 (Grande Região), N3 (Unidade da Federação), N6 (Município)
- **Especial:** nenhum
- **IBGE:** nenhum

O nível municipal (N6) existe e retorna valores (consultas C, G e H).

## 5. Classificações (fonte: A)

A tabela não tem classificações (`"classificacoes": []`), portanto não há categoria de total a escolher.

## 6. Contagem de municípios de SC por ano (fonte: H, comparada com I)

A consulta H trouxe 3.245 linhas de dados, sem contar o cabeçalho. Isso equivale a 11 anos × 295 municípios. A API de Localidades (I) lista 295 municípios em SC.

| Ano | Linhas | Valores numéricos | Valores não numéricos | Códigos ausentes em relação a I |
|-----|--------|-------------------|-----------------------|---------------------------------|
| 2011 | 295 | 293 | 2 (`...`) | nenhum |
| 2012 | 295 | 295 | 0 | nenhum |
| 2013 | 295 | 295 | 0 | nenhum |
| 2014 | 295 | 295 | 0 | nenhum |
| 2015 | 295 | 295 | 0 | nenhum |
| 2016 | 295 | 295 | 0 | nenhum |
| 2017 | 295 | 295 | 0 | nenhum |
| 2018 | 295 | 295 | 0 | nenhum |
| 2019 | 295 | 295 | 0 | nenhum |
| 2020 | 295 | 295 | 0 | nenhum |
| 2021 | 295 | 295 | 0 | nenhum |

Em todos os anos, cada código da API de Localidades aparece na resposta e não há códigos a mais.

**Valores não numéricos em 2011** (todos `...`):

| Código IBGE | Município | 2011 | 2012 |
|-------------|-----------|------|------|
| 4212650 | Pescaria Brava | `...` | 9416 |
| 4220000 | Balneário Rincão | `...` | 11136 |

Na carga, `...` deve virar `NULL`, nunca zero (regra 5 do CLAUDE.md).

## 7. Formato da resposta da API SIDRA (fontes: C, G, H)

- **Formato:** JSON, com a primeira linha de cabeçalho seguida das linhas de dados.
- **Campos:** `NC`, `NN`, `MC`, `MN`, `V`, `D1C`, `D1N`, `D2C`, `D2N`, `D3C`, `D3N`
  - `D1C`: código do município
  - `D2C`: código da variável
  - `D3C`: ano
  - `V`: valor, como texto
- **Exemplos:**

| Consulta | Município | Ano | V |
|----------|-----------|-----|---|
| C | Florianópolis (4205407) | 2011 | 427298 |
| C | Florianópolis (4205407) | 2021 | 516524 |
| F | Florianópolis (4205407) | 2024 | 576361 |

**Nome do município muda de formato conforme o filtro.** Filtrando por código (C), vem "Florianópolis (SC)". Filtrando pela UF (G, H), vem "Abdon Batista - SC". Por isso a chave é sempre o código IBGE de 7 dígitos (`D1C`, tratado como texto), nunca o nome.

## Verificado diretamente

- Nome da tabela, pesquisa, assunto, periodicidade e níveis N1, N2, N3 e N6 (A).
- Ausência de classificações (A).
- Variável 9324, "População residente estimada", em "Pessoas" (A), com MC=45 (C, G, H).
- Lista de períodos e datas de modificação (B).
- Ausência de 2010, 2022 e 2023 (B, D, E).
- 295 linhas por ano para SC entre 2011 e 2021, sem códigos ausentes nem extras em relação à API de Localidades (H, I).
- Valor `...` em 2011 para 4212650 Pescaria Brava e 4220000 Balneário Rincão, e valores numéricos para os dois a partir de 2012 (H).
- Mudança do formato do nome do município conforme o filtro (C, G).

## Inferido / não confirmado

- **Anos ausentes.** A ausência de 2010 e 2022 coincide com anos de Censo; nenhuma nota da API diz isso. A população desses anos deverá vir das tabelas 1378 (Censo 2010) e 4709 (Censo 2022), com `tipo_medida` distinto. Para 2023, a tabela não tem valor e ele fica `NULL`; o motivo da ausência é **NÃO CONFIRMADO**.
- **Revisão de 2017–2020.** A data de modificação desses anos (05/09/2022) sugere uma revisão posterior à publicação original. **NÃO CONFIRMADO**: a API não traz nota que explique a alteração.
- **Instalação de municípios.** O `...` de 2011 para Pescaria Brava e Balneário Rincão é compatível com municípios instalados depois de 2010. O `docs/escopo_mvp.md` registra a hipótese de instalação em 2013. **NÃO CONFIRMADO**: a API de Localidades não traz data de instalação, e não consultei outra fonte. Também chama atenção haver estimativa já em 2012, antes da data provável de instalação; a explicação também é **NÃO CONFIRMADA**.
- **Significado do `...`.** O sentido exato do símbolo nesta tabela é **NÃO CONFIRMADO**: a legenda de sinais do SIDRA não foi lida.

## Pendências

- Ler as notas metodológicas e a legenda de sinais em https://sidra.ibge.gov.br/tabela/6579 (não lidas).
- Confirmar a data de instalação de Pescaria Brava (4212650) e Balneário Rincão (4220000) em fonte oficial. Isso está previsto no cartão D08.
- Entender por que 2012 já tem estimativa para esses dois municípios.

## Situação para o extrator

A tabela está pronta para os anos 2011–2021, no nível N6, com a variável 9324 em "Pessoas". O extrator precisa:

- tratar `...` como `NULL`;
- registrar que 2010, 2022 e 2023 não existem nesta tabela;
- usar `D1C` (texto de 7 dígitos) como chave.
