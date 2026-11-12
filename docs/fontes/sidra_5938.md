# SIDRA 5938: PIB dos Municípios (Referência 2010)

- **Data da consulta:** 2026-11-12
- **Recorte:** municípios de Santa Catarina (UF 42), 2010–2023

> O PIB é **nominal** (a preços correntes). Variação entre anos não é crescimento econômico real (regra 3). O PIB per capita **não está nesta tabela**; ver `ibge_pesquisas_pib_per_capita.md`. O per capita é sempre o valor publicado e nunca é tratado como renda (regra 4).

## URLs consultadas

| # | URL | Uso |
|---|-----|-----|
| A | https://servicodados.ibge.gov.br/api/v3/agregados/5938/metadados | Metadados |
| B | https://servicodados.ibge.gov.br/api/v3/agregados/5938/periodos | Períodos e datas de modificação |
| C | https://apisidra.ibge.gov.br/values/t/5938/n6/in%20n3%2042/v/37/p/2010-2023 | PIB de todos os municípios de SC (**URL final**) |
| D | https://apisidra.ibge.gov.br/values/t/5938/n3/42/v/37/p/2010-2023 | PIB de SC no nível UF, para a validação de total |
| E | https://apisidra.ibge.gov.br/values/t/5938/n6/4212650,4220000/v/37/p/2010-2013 | Municípios instalados em 2013 |
| F | https://apisidra.ibge.gov.br/values/t/5938/n6/4205407/v/513,498,543/p/2021-2023 | Teste de variáveis setoriais em 2022–2023 |
| G | https://servicodados.ibge.gov.br/api/v3/agregados | Catálogo, para procurar uma tabela SIDRA de PIB per capita municipal |
| H | https://servicodados.ibge.gov.br/api/v3/agregados?nivel=N6 | Catálogo filtrado por nível municipal |
| I | https://ftp.ibge.gov.br/Pib_Municipios/2022_2023/base/base_de_dados_2010_2023_txt.zip | Base oficial 2010–2023, com a nota de layout em PDF dentro do zip (Last-Modified 23/12/2025) |
| J | https://ftp.ibge.gov.br/Pib_Municipios/Notas_Metodologicas_2010/NotaMetodologicaPIB_MunicipiosRef2010.pdf | Nota metodológica da série Referência 2010 |
| K | https://ftp.ibge.gov.br/Pib_Municipios/Notas_Metodologicas_2010/NotaMetodologicaPIB_MunicipiosRetropolacao.pdf | Nota da série retropolada 2002–2009 |
| L | https://biblioteca.ibge.gov.br/visualizacao/livros/liv102094.pdf | Nota técnica 02/2024 do Sistema de Contas Nacionais |
| M | https://sidra.ibge.gov.br/tabela/5938 | **Não consultada.** As notas do SIDRA web estão atrás de Cloudflare (ver `sidra_convencoes.md`). |

## 1. Tabela e pesquisa (fonte: A)

- **Id:** 5938
- **Nome:** "Produto interno bruto a preços correntes, impostos, líquidos de subsídios, sobre produtos a preços correntes e valor adicionado bruto a preços correntes total e por atividade econômica, e respectivas participações - Referência 2010"
- **Pesquisa:** "Produto Interno Bruto dos Municípios"
- **Assunto:** "Contas Nacionais e Regionais"
- **Periodicidade:** anual, com `inicio` 2002 e `fim` 2023
- **Níveis territoriais (Administrativo):** N1, N2, N8, N9, **N6**, N3. Os grupos "Especial" e "IBGE" estão vazios.
- **Classificações:** nenhuma (`"classificacoes": []`). A URL final não precisa de filtro de total.

## 2. Variáveis (fonte: A)

### Variáveis de valor (Mil Reais)

| id | nome | unidade |
|----|------|---------|
| **37** | **Produto Interno Bruto a preços correntes** | **Mil Reais** |
| 543 | Impostos, líquidos de subsídios, sobre produtos a preços correntes | Mil Reais |
| 498 | Valor adicionado bruto a preços correntes total | Mil Reais |
| 513 | Valor adicionado bruto a preços correntes da agropecuária | Mil Reais |
| 517 | Valor adicionado bruto a preços correntes da indústria | Mil Reais |
| 6575 | Valor adicionado bruto a preços correntes dos serviços, exclusive administração, defesa, educação e saúde públicas e seguridade social | Mil Reais |
| 525 | Valor adicionado bruto a preços correntes da administração, defesa, educação e saúde públicas e seguridade social | Mil Reais |

As variáveis setoriais (543, 498, 513, 517, 6575, 525) ficam só listadas aqui; o aprofundamento é do cartão D10. Em 2022 e 2023 elas vêm com `...` (consulta F; ver seção 7).

### Variáveis de participação (%)

Todas em "%". Não fazem parte do MVP.

| Grupo | ids |
|-------|-----|
| PIB | 553 (microrregião), 552 (mesorregião), 497 (UF), 530 (grande região), 496 (Brasil) |
| Impostos | 571, 570, 545, 551, 544 |
| VAB total | 555, 554, 500, 546, 499 |
| Agropecuária | 516 (no VAB total), 557, 556, 515, 547, 514 |
| Indústria | 520 (no VAB total), 559, 558, 519, 548, 518 |
| Serviços exceto adm. pública | 6574 (no VAB total), 6571, 6570, 6572, 6569, 6573 |
| Administração pública | 528 (no VAB total), 563, 562, 527, 550, 526 |

### Unidade da variável 37 (fontes: A e C)

- **Texto literal na API de Agregados (A):** "Mil Reais".
- **Na API SIDRA (C):** `MC` = `40` e `MN` = `Mil Reais`, em todas as linhas.
- **Na carga:** reais = V × 1000. Na base oficial (I), a mesma unidade aparece como "R$ 1 000".
- **Arredondamento:** o SIDRA devolve o valor arredondado para inteiro em mil reais. A base oficial (I) traz 3 casas decimais, e em 2010–2023 nenhuma diferença passa de 0,5 mil reais.

## 3. Períodos (fonte: B)

| Período | Data de modificação |
|---------|---------------------|
| 2002–2013 | 14/12/2016 |
| 2014 | 14/12/2017 |
| 2015 | 10/01/2019 |
| 2016 | 13/12/2019 |
| 2017 | 17/12/2021 |
| 2018 | 16/12/2022 |
| 2019–2020 | 15/12/2023 |
| **2021, 2022, 2023** | **19/12/2025** |

- **2010–2023 estão todos presentes**, sem lacunas.
- **2023 está publicado.**

## 4. Cobertura e sinais por ano na URL final (fontes: C, E)

| Ano | Linhas | Valores numéricos | Com sinal | Ausentes da consulta por UF |
|-----|--------|-------------------|-----------|-----------------------------|
| 2010 | 295 | 293 | 2 (`...`) | 0 |
| 2011 | 295 | 293 | 2 (`...`) | 0 |
| 2012 | 295 | 293 | 2 (`...`) | 0 |
| 2013 a 2023 (cada ano) | 295 | 295 | 0 | 0 |

- **Total:** 4.130 linhas (295 × 14).
- **Códigos:** são os mesmos 295 da API de Localidades, sem extras nem duplicados.
- **Sinais:** os 6 sinais são todos `...` e todos em 4212650 e 4220000.

### Pescaria Brava e Balneário Rincão

| Código | Município | 2010 | 2011 | 2012 | 2013 |
|--------|-----------|------|------|------|------|
| 4212650 | Pescaria Brava | `...` | `...` | `...` | 44993 |
| 4220000 | Balneário Rincão | `...` | `...` | `...` | 129061 |

Diferente da tabela 1378, aqui as linhas **aparecem** na consulta por UF, com o sinal `...`.

**Carga (regra 9 e `sidra_convencoes.md`):** `...` → valor `NULL`, `sinal_origem` = `...`.

### ⚠ Divergência em relação à D08

A decisão D08 (`docs/decisoes.md`) aceita ausência ou `...` só para 4212650 e 4220000 **em anos anteriores a 2012**. Na tabela 5938 os dois vêm com `...` **também em 2012**. Um teste de cobertura que siga a D08 ao pé da letra falha em 2012 para esta tabela.

Não há divergência para outros municípios. O PIB começa em 2013, o ano de instalação (ver `sidra_convencoes.md`). A tabela 6579, por outro lado, já traz estimativa de 2012. **Decisão da autora:** ajustar a D08 por tabela (por exemplo, "antes de 2013" para a 5938) ou tratar isso como exceção documentada.

## 5. Validação de total (fontes: C, D)

Soma dos valores numéricos de 37 nos municípios (C) comparada com o valor de SC no nível N3 (D). Valores em mil reais.

| Ano | Soma dos municípios | SC (N3) | Diferença absoluta | Diferença % |
|-----|---------------------|---------|--------------------|-------------|
| 2010 | 153726009 | 153726007 | +2 | +0,000001% |
| 2012 | 191794656 | 191794652 | +4 | +0,000002% |
| 2021 | 428570897 | 428570889 | +8 | +0,000002% |
| 2023 | 513392972 | 513392973 | −1 | −0,0000002% |

As diferenças são de poucos mil reais. São compatíveis com o arredondamento de cada valor municipal para inteiro em mil reais (inferência).

## 6. Denominador do PIB per capita

Resumo aqui; o detalhe está em `ibge_pesquisas_pib_per_capita.md`.

O PIB per capita municipal **não existe em nenhuma tabela SIDRA** com nível municipal, segundo o catálogo da API de Agregados (G, H):

- A pesquisa "Produto Interno Bruto dos Municípios" tem apenas as tabelas 21, 5938, 5939 e 599.
- As tabelas com "per capita" e PIB no nome (1194 e 6784) não têm N6.

O valor oficial está no indicador 47001 da API de Pesquisas do IBGE e na base oficial do FTP (I).

**Nota oficial (I, PDF de layout, nota 3, citação literal):**

> "O cálculo do Produto Interno Bruto per capita dos anos de 2010 a 2021 considerou a população residente da Estatística Estimativa da População, estimativa por município, com data de referência em 1º de julho de cada ano, enviada ao Tribunal de Contas da União - TCU. Em virtude da indisponibilidade da Estatística Estimativa da População para os anos de 2022 e 2023, foi utilizada a população do Censo Demográfico 2022. Para o ano de 2022, foi utilizada a primeira apuração do Censo Demográfico 2022; e para 2023, a Relação da População dos Municípios enviada ao TCU em 2023 com atualizações de limites territoriais [...]"

**Conferência numérica para todos os municípios de SC.** Um candidato "reproduz" o valor quando PIB (I, em R$ 1 000) × 1000 ÷ população, arredondado a 2 casas, é igual ao per capita publicado.

| Ano | Municípios com PIB | Candidato que reproduz o publicado |
|-----|--------------------|------------------------------------|
| 2010 | 293 | Nenhum reproduz todos. O Censo 2010 (1378) reproduz só 113 de 293. A nota cita a estimativa TCU 2010, que **não existe** na 6579. |
| 2011 | 293 | Estimativa 6579 do mesmo ano: 293 de 293 |
| 2012 | 293 | Estimativa 6579 do mesmo ano: 291 de 293. As exceções são Içara (4207007) e Laguna (4209409). |
| 2013–2021 | 295 | Estimativa 6579 do mesmo ano: 295 de 295 em todos os anos |
| 2022 | 295 | Censo 2022 (4709): 271 de 295. As 24 diferenças são pequenas, de algumas pessoas a algumas centenas. |
| 2023 | 295 | Censo 2022 (4709): 295 de 295 |

**Exceções de 2012.** A população implícita de Içara (60374) é igual à estimativa 2012 de Içara mais a de Balneário Rincão (49238 + 11136). A de Laguna (52166) é igual à de Laguna mais a de Pescaria Brava (42750 + 9416). Isso indica que o per capita de 2012 dos municípios de origem usou a população incluindo os territórios desmembrados em 2013. É uma inferência numérica, não citada em nota.

## 7. Notas de revisão da série (fontes: I, J, K, L)

- **Referência 2010 (J).** "O ano de 2010 passa a ser o ano referência da série reformulada", com adoção do SNA 2008, da CNAE 2.0, do Censo Demográfico 2010 e de outras fontes. A série Referência 2002 é a tabela 21, "Série encerrada" segundo o catálogo G.
- **Retropolação 2002–2009 (K).** A série municipal de 2002 a 2009 foi retropolada para a Referência 2010.
- **Nota técnica 02/2024 (L, de 17/06/2024).** Por causa da "mudança de ano base do Sistema de Contas de 2010 para 2021", a divulgação de 2022 foi adiada para 2025, junto com 2023. Nessa divulgação, o PIB é apresentado "sem a abertura do valor adicionado bruto pelas atividades econômicas".
  - Isso é coerente com o `...` das variáveis 513, 498 e 543 em 2022–2023 para Florianópolis (F).
- **Nota 1 do layout (I).** "Os dados de 2022 e 2023 estarão sujeitos a revisão na próxima publicação."
- **Nota 2 do layout (I).** "Para os anos de 2022 e 2023 foram divulgados apenas o Produto Interno Bruto e o Produto Interno Bruto per capita".
- **Datas de modificação (B).** 2021, 2022 e 2023 foram modificados em 19/12/2025, perto da data do arquivo da base (I: 23/12/2025). O que mudou em 2021 é **NÃO CONFIRMADO**.

## 8. Formato da resposta (fonte: C)

- **Campos:** `NC`, `NN`, `MC`, `MN`, `V`, `D1C`, `D1N`, `D2C`, `D2N`, `D3C`, `D3N`.
- **Chave:** `D1C`, como texto de 7 dígitos.

## URL final para o extrator (PIB)

```
https://apisidra.ibge.gov.br/values/t/5938/n6/in%20n3%2042/v/37/p/2010-2023
```

Testada em 2026-11-12. Devolveu **4.130 linhas de dados** (295 × 14), mais o cabeçalho:

- 4.124 numéricas;
- 6 com `...` (4212650 e 4220000, em 2010–2012).

A unidade é "Mil Reais" (MC=40). Não há filtros de classificação, porque a tabela não tem classificações.

A URL do per capita está em `ibge_pesquisas_pib_per_capita.md`.

## Verificado diretamente

- Metadados, as 52 variáveis com id, nome e unidade, níveis com N6 e `classificacoes: []` (A).
- Períodos 2002–2023 com datas de modificação; 2023 publicado (B).
- Unidade "Mil Reais", com MC=40 e MN="Mil Reais" (A, C).
- Cobertura por ano e os 6 `...` de 4212650 e 4220000 em 2010–2012, inclusive em 2012 (C, E).
- Validação de total em 4 anos (C, D).
- PIB do SIDRA igual ao da base oficial dentro de 0,5 mil reais, em todas as 4.124 linhas (C, I).
- Ausência de tabela SIDRA com PIB per capita municipal (G, H).
- Texto literal das notas 1, 2 e 3 do layout (I), da nota técnica 02/2024 (L) e das notas metodológicas (J, K).
- Reprodução numérica do per capita: estimativa do mesmo ano em 2011–2021, com as exceções de 2012 citadas; Censo 2022 em 2023 (295 de 295) e em 2022 (271 de 295).
- Variáveis setoriais com `...` em 2022–2023 para Florianópolis (F).

## Inferido / não confirmado

- **Per capita de 2010.** Que o denominador seja a estimativa TCU de 2010, que não está na 6579, vem da nota 3 de I. Os valores não foram reproduzidos com nenhuma tabela SIDRA. A população implícita de Florianópolis em 2010 é 421203, contra 421240 no Censo.
- **Per capita de 2022.** Que as 24 diferenças venham do uso da **1ª apuração** do Censo 2022, enquanto a 4709 traz a 2ª, é inferência coerente com a nota 3 de I. Não comparei com os valores da 1ª apuração.
- **Exceções de 2012 (Içara e Laguna).** A explicação pela inclusão da população desmembrada é inferência numérica.
- **Validação de total.** Que as diferenças venham de arredondamento é inferência.
- **Revisão de 2021.** O que mudou em 2021 na revisão de 19/12/2025 é **NÃO CONFIRMADO**.
- **Notas da tabela 5938.** As notas no SIDRA web **não foram lidas** (Cloudflare).

## Pendências

- **Decisão da autora sobre a D08:** a 5938 tem `...` em 2012 para 4212650 e 4220000.
- **Decisão da autora sobre a fonte do per capita:** a fonte não é o SIDRA. Ver `ibge_pesquisas_pib_per_capita.md`.
- Ler as notas da tabela em https://sidra.ibge.gov.br/tabela/5938, pelo navegador.
- Aprofundar as variáveis setoriais (cartão D10).
