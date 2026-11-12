# PIB per capita dos municípios: API de Pesquisas do IBGE (indicador 47001)

- **Data da consulta:** 2026-11-12
- **Recorte:** municípios de Santa Catarina (UF 42), 2010–2023

> O PIB per capita é o **valor publicado pelo IBGE**, sem recálculo no projeto (regra 4). Ele **não é renda**. As contas da seção 4 servem só para documentar o denominador usado pelo IBGE.

## Por que não é SIDRA

O catálogo da API de Agregados não tem tabela SIDRA com PIB per capita em nível municipal. Fontes:

- https://servicodados.ibge.gov.br/api/v3/agregados
- https://servicodados.ibge.gov.br/api/v3/agregados?nivel=N6

**O que o catálogo mostra:**

- A pesquisa "Produto Interno Bruto dos Municípios" tem só as tabelas 21, 5938, 5939 e 599. Nenhuma tem variável de PIB per capita (ver `sidra_5938.md`).
- **Tabela 1194:** "Produto Interno Bruto per capita", da pesquisa Indicadores de Desenvolvimento Sustentável. Tem só os níveis N1, N2 e N3, e período de 2006 a 2013.
- **Tabela 6784:** da pesquisa Contas Nacionais Anuais. Tem só o nível N1.

O valor oficial municipal está publicado em duas fontes oficiais, que coincidem:

- a API de Pesquisas do IBGE (IBGE Cidades), pesquisa 38, indicador 47001;
- a base de dados do PIB dos Municípios no FTP.

## URLs consultadas

| # | URL | Uso |
|---|-----|-----|
| A | https://servicodados.ibge.gov.br/api/v1/pesquisas/38/indicadores | Árvore de indicadores da pesquisa 38 |
| B | https://servicodados.ibge.gov.br/api/v1/pesquisas/38/indicadores/47001 | Metadados do indicador 47001 |
| C | https://servicodados.ibge.gov.br/api/v1/pesquisas/38/indicadores/47001/resultados/4205407\|4212650 | Teste com 2 municípios |
| D | https://servicodados.ibge.gov.br/api/v1/pesquisas/38/indicadores/47001/resultados/N6%5BN3%5B42%5D%5D | Todos os municípios de SC (**URL final**) |
| E | https://servicodados.ibge.gov.br/api/v1/pesquisas/38/periodos | Períodos, fonte e nota da pesquisa |
| F | https://ftp.ibge.gov.br/Pib_Municipios/2022_2023/base/base_de_dados_2010_2023_txt.zip | Base oficial 2010–2023, com o PDF de layout e as notas |

## 1. Indicador (fontes: A, B)

| id | Caminho na árvore | Unidade |
|----|-------------------|---------|
| **47001** | "PIB per capita" (47000) → "Série revisada" | `{"id": "R$", "classe": "$", "multiplicador": 1}`, ou seja, reais |
| 47002 | "PIB per capita" → "Série encerrada" | R$, multiplicador 1. Não usar. |

- **Fonte declarada (B):** "IBGE, em parceria com os Órgãos Estaduais de Estatística, Secretarias Estaduais de Governo e Superintendência da Zona Franca de Manaus - SUFRAMA".
- **Campo `nota` (B):** vazio.

**Na base oficial (F):**

- **Nome da coluna:** "Produto Interno Bruto per capita, a preços correntes".
- **Unidade:** "R$ 1,00", em "Unidades utilizadas" no PDF de layout.

## 2. Formato da resposta (fontes: C, D)

A resposta tem esta forma:

```text
[ { "id": 47001, "res": [ { "localidade": "420540", "res": {"1999": null, ..., "2023": "58059.37"}, "notas": {...} } ] } ]
```

- **Código da localidade:** vem com **6 dígitos**, **sem o dígito verificador**. Por exemplo, `420540` para Florianópolis (4205407).
- **Conversão para 7 dígitos:** os 295 prefixos de 6 dígitos de SC são únicos e batem com a API de Localidades. A conversão é feita pelo cadastro: casar `localidade` com os 6 primeiros dígitos do código da `dim_municipio`.
- **Valores:** vêm como texto com ponto decimal. Anos sem série vêm `null` (1999–2009).
- **Notas:** o campo `notas` veio todo `null` para SC.

## 3. Cobertura em SC (fonte: D)

| Ano | Valores numéricos | Valores não numéricos |
|-----|-------------------|-----------------------|
| 2010–2012 | 293 por ano | `"-"` em 421265 (Pescaria Brava) e 422000 (Balneário Rincão) |
| 2013–2023 | 295 por ano | 0 |

### ⚠ Atenção ao sinal `-`

Nesta API, o `-` aparece onde o SIDRA usa `...` (os dois municípios antes de 2013). Pela legenda do SIDRA, `-` significa "zero absoluto". A regra 9 manda carregar `-` como 0, o que aqui seria **errado**: o município não existia.

O significado de `-` nesta API **não está documentado** nas fontes lidas. Recomendação: para esta fonte, carregar `-` como `NULL` com `sinal_origem` = `-`. Essa é uma decisão da autora e deve ir para `docs/decisoes.md`.

## 4. Denominador (fontes: D, F e tabelas SIDRA 6579, 1378 e 4709)

### Nota oficial

Fonte: F, PDF `layout_da_base_de_dados_2010_2023_em_formato_txt.pdf`, nota 3. Citação literal:

> "O cálculo do Produto Interno Bruto per capita dos anos de 2010 a 2021 considerou a população residente da Estatística Estimativa da População, estimativa por município, com data de referência em 1º de julho de cada ano, enviada ao Tribunal de Contas da União - TCU. Em virtude da indisponibilidade da Estatística Estimativa da População para os anos de 2022 e 2023, foi utilizada a população do Censo Demográfico 2022. Para o ano de 2022, foi utilizada a primeira apuração do Censo Demográfico 2022; e para 2023, a Relação da População dos Municípios enviada ao TCU em 2023 com atualizações de limites territoriais que tenham sido comunicadas ao IBGE entre 1 de agosto de 2022 e 30 de abril de 2023 [...]"

### Contas por município

- **PIB:** da base F, em R$ 1 000, com 3 casas decimais. O SIDRA 5938 traz o mesmo valor arredondado.
- **Per capita calculado:** PIB × 1000 ÷ população, arredondado a 2 casas.
- **"Publicado":** o valor da API (D), que é idêntico ao da base F nas 4.124 linhas de SC.
- **Candidatos testados:** estimativa 6579 do mesmo ano, estimativa 6579 do ano anterior, Censo 2010 (1378) e Censo 2022 (4709).

| Município | Ano | PIB (mil R$) | População candidata | Per capita calculado | Est. ano anterior → calculado | Publicado |
|-----------|-----|-------------:|---------------------|---------------------:|-------------------------------|----------:|
| Florianópolis 4205407 | 2010 | 11276679.727 | Censo 2010: 421240 | 26770.20 | — | **26772.55** |
| | 2012 | 13946621.257 | Est. 2012: 433158 | **32197.54** | 427298 → 32639.10 | 32197.54 |
| | 2021 | 23559946.530 | Est. 2021: 516524 | **45612.49** | 508826 → 46302.56 | 45612.49 |
| | 2022 | 26552426.154 | Censo 2022 (4709): 537211 | 49426.44 | 516524 → 51405.99 | **49426.25** |
| | 2023 | 31190132.216 | Censo 2022 (4709): 537211 | **58059.37** | — | 58059.37 |
| Joinville 4209102 | 2010 | 18252540.307 | Censo 2010: 515288 | 35422.02 | — | **35424.63** |
| | 2012 | 20472880.778 | Est. 2012: 526338 | **38896.83** | 520905 → 39302.52 | 38896.83 |
| | 2021 | 45074734.617 | Est. 2021: 604708 | **74539.67** | 597658 → 75418.94 | 74539.67 |
| | 2022 | 45511050.608 | Censo 2022 (4709): 616317 | 73843.57 | 604708 → 75261.20 | **73842.86** |
| | 2023 | 49815876.840 | Censo 2022 (4709): 616317 | **80828.33** | — | 80828.33 |
| Abdon Batista 4200051 | 2010 | 36435.832 | Censo 2010: 2653 | **13733.82** | — | 13733.82 |
| | 2012 | 62605.282 | Est. 2012: 2635 | **23759.12** | 2644 → 23678.25 | 23759.12 |
| | 2021 | 75130.849 | Est. 2021: 2534 | **29649.11** | 2548 → 29486.20 | 29649.11 |
| | 2022 | 110319.136 | Censo 2022 (4709): 2598 | **42463.10** | 2534 → 43535.57 | 42463.10 |
| | 2023 | 115985.219 | Censo 2022 (4709): 2598 | **44644.04** | — | 44644.04 |
| Pescaria Brava 4212650 | 2010–2012 | `...` (SIDRA) | — | — | — | `-` |
| | 2013 | 44993.175 | Est. 2013: 9687 | **4644.70** | 9416 → 4778.37 | 4644.70 |
| | 2021 | 119467.627 | Est. 2021: 10225 | **11683.88** | 10159 → 11759.78 | 11683.88 |
| | 2022 | 138525.255 | Censo 2022 (4709): 10190 | **13594.24** | 10225 → 13547.70 | 13594.24 |
| | 2023 | 164482.919 | Censo 2022 (4709): 10190 | **16141.60** | — | 16141.60 |
| Balneário Rincão 4220000 | 2010–2012 | `...` (SIDRA) | — | — | — | `-` |
| | 2013 | 129061.267 | Est. 2013: 11628 | **11099.18** | 11136 → 11589.55 | 11099.18 |
| | 2021 | 294751.343 | Est. 2021: 13129 | **22450.40** | 12946 → 22767.75 | 22450.40 |
| | 2022 | 354556.830 | Censo 2022 (4709): 15981 | **22186.15** | 13129 → 27005.62 | 22186.15 |
| | 2023 | 420207.739 | Censo 2022 (4709): 15981 | **26294.21** | — | 26294.21 |

- **Negrito:** o calculado coincide com o publicado. Quando nenhum coincide, o publicado está em negrito.
- **2013:** usado para Pescaria Brava e Balneário Rincão, porque não têm PIB em 2010–2012.

### Resumo para os 295 municípios

| Ano | Coincidências por candidato |
|-----|-----------------------------|
| 2010 | Censo 2010: 113 de 293. Nenhum outro candidato existe (a 6579 não tem 2010). |
| 2011 | Estimativa do mesmo ano: 293 de 293 |
| 2012 | Estimativa do mesmo ano: 291 de 293 (exceções: Içara 4207007 e Laguna 4209409) |
| 2013–2021 | Estimativa do mesmo ano: 295 de 295 em cada ano |
| 2022 | Censo 2022 (4709): 271 de 295 |
| 2023 | Censo 2022 (4709): 295 de 295 |

### Conclusão sobre o denominador

**Verificado (documento oficial F, nota 3):** a regra oficial é estimativa TCU de 1º de julho para 2010–2021, Censo 2022 (1ª apuração) para 2022 e a relação TCU 2023 para 2023.

**Verificado (numericamente):**

- 2011–2021 são reproduzidos pela estimativa 6579 do mesmo ano, com as duas exceções de 2012.
- 2023 é reproduzido pelo Censo 2022 da 4709.

**Inferido:**

- **2010:** não é reproduzido por nenhuma tabela SIDRA. Coerente com a nota, que cita a estimativa TCU 2010, ausente da 6579.
- **2022:** as 24 diferenças são coerentes com o uso da 1ª apuração, enquanto a 4709 traz a 2ª. Não comparei com os valores da 1ª apuração.
- **2023:** a relação TCU 2023 coincide com a 4709 para todos os municípios de SC.
- **2012:** em Içara e Laguna, a população implícita é igual à soma com o município desmembrado em 2013 (49238 + 11136 = 60374; 42750 + 9416 = 52166).

**Consequência para o projeto:** o per capita publicado **não** é igual a PIB ÷ população de nenhuma tabela do projeto em 2010 e em parte de 2012 e 2022. Mais um motivo para nunca recalcular (regra 4).

## URL final para o extrator (per capita)

```
https://servicodados.ibge.gov.br/api/v1/pesquisas/38/indicadores/47001/resultados/N6%5BN3%5B42%5D%5D
```

O trecho `N6%5BN3%5B42%5D%5D` é `N6[N3[42]]` codificado.

Testada em 2026-11-12. Devolveu **1 indicador** com **295 localidades**. Cada uma traz a série de 1999 a 2023, com valores de 2010 a 2023. São 4.130 pares município × ano no intervalo 2010–2023: 4.124 numéricos e 6 com `-`.

A API não filtra período na URL testada; o extrator deve recortar 2010–2023.

## Verificado diretamente

- Inexistência de tabela SIDRA municipal com PIB per capita (catálogo de agregados).
- Indicador 47001, "Série revisada" de "PIB per capita", unidade R$ com multiplicador 1, e a fonte declarada (A, B).
- Código de localidade com 6 dígitos; os prefixos de SC são únicos e batem com o cadastro (D).
- Cobertura por ano e o `-` em 421265 e 422000 em 2010–2012 (D).
- Igualdade exata com a coluna da base oficial F em 4.124 de 4.124 linhas.
- Texto da nota 3 e das unidades no layout (F).
- As coincidências numéricas da seção 4.

## Inferido / não confirmado

- **Significado de `-`.** O sentido de `-` nesta API é **NÃO CONFIRMADO**. Pelo contexto, equivale à ausência (`...` no SIDRA), e não a zero.
- **Denominador de 2010 e diferenças de 2022.** São inferências coerentes com a nota oficial, sem os valores populacionais exatos usados pelo IBGE.
- **Exceções de 2012.** A explicação para Içara e Laguna é inferência.
- **Documentação da API.** A documentação da API de Pesquisas, incluindo a sintaxe `N6[N3[42]]` e o filtro de período, **não foi lida**. A sintaxe foi validada só na prática.

## Pendências

- **Decisão da autora:** adotar esta API (ou a base do FTP) como fonte do per capita. Registrar em `docs/decisoes.md`.
- **Decisão da autora:** como carregar o `-` desta API, dado o conflito com a regra 9.
- Ler a documentação oficial da API de Pesquisas (servicodados.ibge.gov.br/api/docs).
- Obter os valores da 1ª apuração do Censo 2022, para confirmar o denominador de 2022.
