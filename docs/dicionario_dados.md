# Dicionário de dados: Brasil em Dados SC

- **Versão:** 2026-11-12 (cartão D10)
- **Consolidado a partir de:**
  - `docs/fontes/sidra_6579.md`
  - `docs/fontes/sidra_1378.md`
  - `docs/fontes/sidra_4709.md`
  - `docs/fontes/sidra_5938.md`
  - `docs/fontes/sidra_5964.md`
  - `docs/fontes/ibge_pesquisas_pib_per_capita.md`
  - `docs/fontes/ibge_localidades.md`
  - `docs/fontes/sidra_convencoes.md`
  - `docs/decisoes.md` (D01, D02, D06–D10)
  - CLAUDE.md (regras de dados 1–11)

> **Convenção deste documento:** o que não foi verificado diretamente nas respostas das APIs ou em documento oficial está marcado como **NÃO CONFIRMADO**. Os nomes marcados como **(proposta)** (hoje, só os da extensão de setores) ainda não foram decididos.

## 1. Modelo de indicadores do MVP

Decisão D10: o **indicador** (conceito de negócio) fica na `dim_indicador`; a **série** (origem técnica: tabela/variável SIDRA ou pesquisa/indicador da API de Pesquisas) fica na `dim_serie`. Atributos que dependem da fonte (tabela, data de referência, unidade de origem, fator de conversão) ficam na série. Assim, `pop_censo` é um indicador só, com duas séries de origem.

### 1.1 `dim_indicador`

| codigo_indicador | nome | unidade_armazenada | tipo_medida | descricao |
|---|---|---|---|---|
| `pop_estimada` | População residente estimada | Pessoas | `estimativa` | Estimativa anual de população do IBGE. Não se mistura com censo. |
| `pop_censo` | População residente (Censo) | Pessoas | `censo` | População recenseada nos Censos Demográficos 2010 e 2022. |
| `pib_corrente` | PIB a preços correntes | R$ | `nominal` | PIB nominal. Nunca descrever variação como crescimento real (regra 3). |
| `pib_per_capita` | PIB per capita | R$ | `nominal` | Valor publicado pelo IBGE, sem recálculo. Não é renda (regra 4). |

`tipo_medida` nunca é `NULL`.

### 1.2 `dim_serie`

| cod_serie | codigo_indicador | fonte | tabela_ou_pesquisa | variavel_ou_indicador | unidade_origem | fator_conversao | data_referencia | Anos no recorte 2010–2023 |
|---|---|---|---|---|---|---|---|---|
| `sidra_6579_v9324` | `pop_estimada` | `sidra` | 6579 ("Estimativas de População") | 9324 "População residente estimada" | Pessoas (MC 45) | 1 | 1º de julho de cada ano | 2011–2021. **2010, 2022 e 2023 não existem** na tabela. |
| `sidra_1378_v93` | `pop_censo` | `sidra` | 1378 ("Censo Demográfico" 2010) | 93 "População residente" | Pessoas (MC 45) | 1 | noite de 31 de julho para 1º de agosto de 2010 (ver nota ¹) | 2010 |
| `sidra_4709_v93` | `pop_censo` | `sidra` | 4709 ("Censo Demográfico" 2022) | 93 "População residente" | Pessoas (MC 45) | 1 | meia-noite de 31 de julho para 1º de agosto de 2022 (ver nota ²) | 2022 |
| `sidra_5938_v37` | `pib_corrente` | `sidra` | 5938 ("PIB dos Municípios", Referência 2010) | 37 "Produto Interno Bruto a preços correntes" | Mil Reais (MC 40) | 1000 | ano civil | 2010–2023, sem lacunas |
| `pesquisas_38_i47001` | `pib_per_capita` | `api_pesquisas` | Pesquisa 38 (PIB dos Municípios) | Indicador 47001 "PIB per capita" → "Série revisada" | R$ (multiplicador 1) | 1 | ano civil | 2010–2023 |

A coluna `url_extrator` de cada série é a "URL final" listada nas observações por indicador, abaixo.

**Fontes das datas de referência dos Censos** (documentos oficiais do IBGE, consultados em 2026-11-12):

- ¹ **Censo 2010**
  - Documento: *Metodologia do Censo Demográfico 2010* (Série Relatórios Metodológicos, v. 41, IBGE, 2013), seção 1.3 "Periodicidade e data de referência", p. 44 impressa (p. 45 do PDF).
  - Citação: "teve como data de referência deste Censo Demográfico a noite de 31 de julho para 1º de agosto de 2010".
  - URL: https://ftp.ibge.gov.br/Censos/Censo_Demografico_2010/metodologia/metodologia_censo_dem_2010.pdf
- ² **Censo 2022**
  - Documento: *Censo Demográfico 2022 – Notas metodológicas 05/2026 – Microdados da amostra do Censo Demográfico 2022*, p. 20.
  - Citação: "teve como data de referência a meia-noite do dia 31 de julho para 1° de agosto de 2022".
  - URL: https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Microdados_e_Areas_de_Ponderacao/Documentacao/Notas%20metodol%c3%b3gicas/Notas%20metodol%c3%b3gicas%2005-2026%20-%20Microdados%20da%20amostra%20do%20CD2022.pdf
  - O questionário e o manual de entrevista do Censo 2022 perguntam "Quantas pessoas moravam neste domicílio em 31 de julho de 2022?".

> **Censo e estimativa não são diretamente comparáveis.** As estimativas (`pop_estimada`) têm data de referência em **1º de julho** de cada ano. Os Censos (`pop_censo`) têm data de referência na **noite de 31 de julho para 1º de agosto** de 2010 e de 2022. Além da diferença de método (contagem × estimativa), as datas são diferentes. Por isso, valores de Censo e de estimativa do mesmo ano ou período não devem ser comparados diretamente nem tratados como uma série única (regra 2).

### 1.3 Tabela fato

| Coluna | Tipo | Observações |
|---|---|---|
| `cod_municipio` | texto, 7 dígitos | FK para `dim_municipio` |
| `codigo_indicador` | texto | FK para `dim_indicador` |
| `ano` | inteiro | |
| `cod_serie` | texto | FK para `dim_serie`; atende a regra 8 |
| `valor` | `numeric(18,2)` | Já convertido para a `unidade_armazenada`; `NULL` quando veio sinal de ausência |
| `sinal_origem` | texto | Sinal original da fonte; `NULL` quando o valor veio numérico |
| `data_coleta` | data/hora | Momento da coleta que gerou o arquivo RAW |

Chave única: (`cod_municipio`, `codigo_indicador`, `ano`).

### Regra de sinais por indicador

| Indicador | Sinais | Carga |
|-----------|--------|-------|
| `pop_estimada` | `...` em 2011 para 4212650 e 4220000 | `NULL`, `sinal_origem` = `...` |
| `pop_censo` (1378) | Na consulta por UF, os dois municípios **não têm linha** em 2010. Pelo código, viriam com `...`. | Sem linha (D08) |
| `pop_censo` (4709) | Nenhum | — |
| `pib_corrente` | `...` em 2010–2012 para 4212650 e 4220000 | `NULL`, `sinal_origem` = `...` |
| `pib_per_capita` | `-` em 2010–2012 para os mesmos códigos | `NULL`, `sinal_origem` = `-` (regra 9, parte da API de Pesquisas) |

### Observações por indicador

**`pop_estimada`**

- Data de referência: 1º de julho de cada ano, segundo os PDFs oficiais das estimativas.
- O nome do município muda de formato conforme o filtro. A chave é sempre o código.
- URL final: `https://apisidra.ibge.gov.br/values/t/6579/n6/in%20n3%2042/v/9324/p/2011-2021` (3.245 linhas).

**`pop_censo` (1378)**

- Tem 4 classificações, e todas exigem o filtro de total `0`: c1 (situação), c2 (sexo), c287 (idade) e c455 (condição no domicílio).
- URL final: `https://apisidra.ibge.gov.br/values/t/1378/n6/in%20n3%2042/v/93/p/2010/c1/0/c2/0/c287/0/c455/0` (293 linhas).

**`pop_censo` (4709)**

- Não tem classificações. O período foi modificado em 22/12/2023.
- Os valores são, por inferência forte, os da **2ª apuração**, republicada em 27/10/2023 e 22/12/2023. O que mudou em relação à 1ª apuração (28/06/2023) é **NÃO CONFIRMADO**.
- URL final: `https://apisidra.ibge.gov.br/values/t/4709/n6/in%20n3%2042/v/93/p/2022` (295 linhas).

**`pib_corrente`**

- PIB nominal: nunca descrever variação como crescimento real (regra 3).
- O SIDRA arredonda para inteiro em mil reais.
- 2021–2023 foram modificados em 19/12/2025. 2022 e 2023 estão "sujeitos a revisão" (nota 1 do layout da base oficial).
- Validação de total: a soma dos municípios difere do valor de SC (N3) em até 8 mil reais.
- URL final: `https://apisidra.ibge.gov.br/values/t/5938/n6/in%20n3%2042/v/37/p/2010-2023` (4.130 linhas).

**`pib_per_capita`**

- É o valor publicado, sem recálculo, e **não é renda** (regra 4).
- O código vem com 6 dígitos e precisa da conversão da seção 3.2.
- **Denominador oficial** (nota 3 do layout): estimativa TCU de 1º de julho em 2010–2021, 1ª apuração do Censo 2022 em 2022 e relação TCU 2023 em 2023.
- **Reprodução numérica:**
  - 2011–2021 batem com a 6579, exceto Içara e Laguna em 2012.
  - 2023 bate com a 4709.
  - 2010 não é reproduzível com o SIDRA.
  - 2022 bate em 271 de 295.
- URL final: `https://servicodados.ibge.gov.br/api/v1/pesquisas/38/indicadores/47001/resultados/N6%5BN3%5B42%5D%5D` (295 localidades, série 1999–2023). O recorte 2010–2023 é feito no extrator.
- **Teste de validação (D10):** PIB (R$) / população ≈ per capita publicado, com a 6579 em 2011–2021 e a 4709 em 2023; excluídos 2010, 2022 e Içara e Laguna em 2012.

### Fontes descartadas

- **Tabela 1194:** sem N6.
- **Tabela 6784:** só N1.
- **Tabela 5964:** é da PeNSE 2015 e não tem relação com o PIB (ver `sidra_5964.md`).
- **Tabela 21:** PIB Referência 2002, série encerrada.

## 2. Indicadores setoriais: EXTENSÃO (fora do MVP)

> **Não fazem parte do MVP** (decisão D10 em `docs/decisoes.md`). Os códigos abaixo são **(proposta)** e só entram na `dim_indicador` e na `dim_serie` (como séries `sidra_5938_v<id>`) quando a extensão for implementada. Análise completa em `docs/fontes/sidra_5938.md`, seção "Setores (D10)".

| codigo_indicador (proposta) | Variável 5938 | Nome (literal) | unidade_origem | fator_conversao | unidade_armazenada | Anos com valor |
|---|---|---|---|---|---|---|
| `vab_total` | 498 | Valor adicionado bruto a preços correntes total | Mil Reais | 1000 | R$ | 2010–2021 |
| `vab_agropecuaria` | 513 | Valor adicionado bruto a preços correntes da agropecuária | Mil Reais | 1000 | R$ | 2010–2021 |
| `vab_industria` | 517 | Valor adicionado bruto a preços correntes da indústria | Mil Reais | 1000 | R$ | 2010–2021 |
| `vab_servicos_exc_adm` | 6575 | Valor adicionado bruto a preços correntes dos serviços, exclusive administração, defesa, educação e saúde públicas e seguridade social | Mil Reais | 1000 | R$ | 2010–2021 |
| `vab_adm_publica` | 525 | Valor adicionado bruto a preços correntes da administração, defesa, educação e saúde públicas e seguridade social | Mil Reais | 1000 | R$ | 2010–2021 |
| `impostos_liquidos` | 543 | Impostos, líquidos de subsídios, sobre produtos a preços correntes | Mil Reais | 1000 | R$ | 2010–2021 |

**Cobertura e sinais:**

- **2010–2012:** `...` para 4212650 e 4220000.
- **2022–2023:** `...` para **todos os 295** municípios (nota técnica 02/2024). Nessas linhas, `MC`/`MN` vêm vazios: a unidade deve sair da `dim_serie`, nunca da linha. Isso conflita com a regra 10, e a extensão precisará de uma regra de cobertura própria.

**Identidades verificadas (2010–2021, SC):**

- VAB + impostos = PIB, com diferença de até 1 mil reais;
- soma dos 4 setores = VAB, com diferença de até 2 mil reais.

**Testes futuros da extensão:** as duas identidades acima viram testes, com tolerância de arredondamento: VAB total + impostos = PIB, e soma dos 4 setores = VAB total.

**URL combinada testada:** `https://apisidra.ibge.gov.br/values/t/5938/n6/in%20n3%2042/v/37,498,513,517,6575,525,543/p/2010-2023` (28.910 linhas).

## 3. Dimensão `dim_municipio`

Origem: `https://servicodados.ibge.gov.br/api/v1/localidades/estados/42/municipios`. São 295 registros, sem nulos e com estrutura idêntica em todos (ver `ibge_localidades.md`).

As colunas regionais seguem a D06; os demais nomes foram aprovados no D10.

| Coluna | Tipo | Origem na API (formato hierárquico) | Observações |
|--------|------|-------------------------------------|-------------|
| `cod_municipio` | texto, 7 dígitos | `id` (vem como **número**) | Chave em todas as camadas (regra 1). Converter com `str(id).zfill(7)`. Todos têm 7 dígitos, começam com 42 e são únicos. |
| `nome_municipio` | texto | `nome` | Nunca é chave. Tem acentos (110 nomes), apóstrofo ("Herval d'Oeste") e hífen ("Grão-Pará"). |
| `cod_regiao_imediata` | texto | `regiao-imediata.id` | Divisão nova. 24 distintas em SC. |
| `nome_regiao_imediata` | texto | `regiao-imediata.nome` | Pode ter hífen e apóstrofo, por exemplo "Joaçaba - Herval d'Oeste". |
| `cod_regiao_intermediaria` | texto | `regiao-imediata.regiao-intermediaria.id` | Divisão nova. 7 distintas. Filtro principal dos dashboards (D06). |
| `nome_regiao_intermediaria` | texto | `regiao-imediata.regiao-intermediaria.nome` | |
| `cod_microrregiao` | texto | `microrregiao.id` | Divisão antiga. 20 distintas. |
| `nome_microrregiao` | texto | `microrregiao.nome` | |
| `cod_mesorregiao` | texto | `microrregiao.mesorregiao.id` | Divisão antiga. 6 distintas. |
| `nome_mesorregiao` | texto | `microrregiao.mesorregiao.nome` | |
| `cod_uf`, `sigla_uf` | texto | `...UF.id`, `...UF.sigla` | Sempre 42 e "SC". Aparece nas duas hierarquias. |

**Cuidados:**

- **Ids que se repetem entre divisões.** Os ids de mesorregião e de região intermediária usam a **mesma faixa** (4201–4207) para entidades diferentes. Por isso as divisões nunca se relacionam pelo id (D06).
- **Erro na documentação da API.** O esquema escreve `regiao-intermediara`, mas a resposta real usa `regiao-intermediaria`.
- **Recorte vigente.** A API devolve o recorte atual: 295 municípios em todos os anos, inclusive os instalados em 1º/01/2013. Que a API não versione por data é **inferência**.
- **Ano da divisão nova.** O ano de 2017 para a divisão em regiões imediatas e intermediárias é **NÃO CONFIRMADO** na documentação lida.
- **Amostra para testes:** `tests/fixtures/localidades_sc_amostra.json`, com 5 municípios.

## 4. Regras de carga por fonte

### 4.1 API SIDRA (6579, 1378, 4709, 5938)

- **Filtro:** sempre `n6/in%20n3%2042` (D08). A fato guarda só o que a fonte devolveu. Combinações ausentes não geram linha, e a grade completa é montada na GOLD.
- **Filtros de total:** explícitos quando há classificação. Hoje só a 1378 tem: `c1/0/c2/0/c287/0/c455/0`.
- **Campos pelo cabeçalho (D10):** a primeira linha da resposta é o cabeçalho e mapeia cada chave (`D1C`, `D2C`, `D3C`...) para um rótulo, como "Município (Código)", "Variável (Código)" ou "Ano (Código)". O extrator localiza código do município, variável e ano **pelo rótulo do cabeçalho, nunca pela posição** das colunas `D*`, porque a ordem das dimensões varia por tabela. Depois de lido, o cabeçalho é descartado.
  - `V`: valor, como texto.
  - `MN`: unidade de origem, só para conferência. Nas linhas de sinal da 5938 em 2022–2023, vem vazia.
  - A **unidade vem da `dim_serie`**, não da linha.
- **Sinais (regra 9 e D07):**

| Sinal | Valor carregado | `sinal_origem` |
|-------|-----------------|----------------|
| `-` | 0 | `-` |
| `0` | 0 | `NULL` (veio numérico) |
| `...`, `..`, `X`, letras de faixa | `NULL` | o sinal original |

  Legenda oficial em `docs/fontes/sidra_convencoes.md`.
- **Nome do município:** muda de formato ("Florianópolis (SC)" ou "Abdon Batista - SC") e nunca é usado.

### 4.2 API de Pesquisas (indicador 47001)

- **Filtro:** `resultados/N6[N3[42]]`, codificado na URL. A sintaxe foi validada só na prática; a documentação da API de Pesquisas **não foi lida**.
- **Código 6 → 7 dígitos (D09):**
  - A `localidade` vem sem dígito verificador e é convertida pelo cadastro da `dim_municipio`, casando com os 6 primeiros dígitos.
  - **Teste 1:1 obrigatório:** cada código de 6 dígitos corresponde a exatamente um código de 7 do cadastro, e nenhum fica sem par. Hoje: 295 ↔ 295, sem colisões.
- **Período:** a resposta traz 1999–2023. O extrator recorta 2010–2023. Os anos de 1999 a 2009 vêm `null`.
- **Sinais:** `-` carrega como `NULL`, com `sinal_origem` = `-` (regra 9, parte da API de Pesquisas). Diferente do SIDRA, aqui o `-` não é zero.
- **Notas:** o campo `notas` veio todo `null` para SC.

### 4.3 Unidades e tipos (regra 11 e D09)

- **RAW:** resposta original, sem conversão (regra 7).
- **Conversão de unidade:** acontece **só na carga para a SILVER**, com `valor_silver = valor_origem × fator_conversao` da `dim_serie`.
  - PIB: × 1000.
  - Per capita e população: × 1.
- **Tipos:**
  - Valores monetários a partir da SILVER: R$ em `numeric(18,2)`, nunca `float`.
  - Coluna `valor` única em `numeric(18,2)` para todos os indicadores, inclusive população (D10).
- **Proibido converter** na GOLD, nos dashboards ou em notebooks.

## 5. Teste de cobertura (regra 10)

Ausência de valor (linha ausente, `NULL` ou sinal) só é aceita para **4212650 (Pescaria Brava)** e **4220000 (Balneário Rincão)**, **antes de 2013**. Qualquer outra ausência faz o teste falhar.

| Indicador (fonte) | Esperado para 4212650 e 4220000 | Esperado para os outros 293 |
|-------------------|---------------------------------|-----------------------------|
| `pop_estimada` (6579) | 2011: linha com `...`. 2012–2021: valor numérico (o IBGE já estimou 2012). | 2011–2021: numérico |
| `pop_censo` (1378) | 2010: **sem linha** na consulta por UF | 2010: numérico (293 linhas) |
| `pop_censo` (4709) | 2022: numérico (10190 e 15981) | 2022: numérico |
| `pib_corrente` (5938 v. 37) | 2010–2012: linha com `...`. 2013–2023: numérico. | 2010–2023: numérico |
| `pib_per_capita` (47001) | 2010–2012: `-`, carregado como `NULL`. 2013–2023: numérico. | 2010–2023: numérico |
| Setores (5938): EXTENSÃO, fora do MVP | 2010–2012: `...` | 2022–2023: `...` para **todos**. **Conflita com a regra 10.** |

**Anos que não existem na fonte:** os anos que a tabela não publica não são "ausência" de município. Por exemplo, 2010, 2022 e 2023 não existem na 6579. O teste deve verificar a grade só nos anos publicados por série, listados na seção 1.2.

**Testes de modelo previstos para o D26:**

- cada indicador tem exatamente uma `unidade_armazenada` na tabela fato (D09);
- cada combinação (`codigo_indicador`, `ano`) vem de exatamente uma série (D10);
- PIB (R$) / população usada pelo IBGE ≈ PIB per capita publicado, dentro de uma tolerância de arredondamento, com as exclusões da seção 1 (D10).

## 6. Verificado diretamente

- Todos os ids, nomes e unidades de tabelas, variáveis e indicador das seções 1 e 2, e as contagens de linhas das URLs finais. Testes de 2026-11-12, com as fontes em `docs/fontes/`.
- A legenda de sinais do SIDRA, no modal "Símbolos especiais" da página da tabela.
- A cobertura e os sinais por indicador da seção 5.
- A estrutura da API de Localidades e as contagens da seção 3.
- O texto oficial sobre o denominador do per capita e a nota técnica 02/2024.
- As datas de referência dos Censos 2010 e 2022, em documentos metodológicos do IBGE (notas ¹ e ² da seção 1.2).

## 7. NÃO CONFIRMADO

- **Notas do SIDRA web:** as notas das tabelas 6579, 1378, 4709 e 5938 estão atrás de Cloudflare, e não tentei contornar.
- **Lacunas da 6579:** o motivo de não haver estimativa em 2010, 2022 e 2023, e o motivo da revisão de 2017–2020 (modificação em 05/09/2022).
- **Censo 2022:** o que mudou entre a 1ª e a 2ª apuração, e se SC foi afetado. *(A data de referência foi confirmada em 2026-11-12; ver as notas da seção 1.2.)*
- **Denominador do per capita:** os valores exatos de população usados pelo IBGE em 2010 (estimativa TCU 2010) e em 2022 (1ª apuração). O motivo das exceções de Içara e Laguna em 2012; a hipótese é a inclusão da população desmembrada.
- **Revisão do PIB:** o que mudou em 2021 na revisão de 19/12/2025. Quando sairá a nova base 2021 e se ela altera a série.
- **Instalação dos municípios:** a data de 1º/01/2013 vem de nota do PDF de 2012, associada aos dois municípios por coincidência de valores. A página do PDF não foi conferida visualmente.
- **Filtro por UF:** o motivo de a consulta por UF omitir linhas sem valor na 1378, mas não na 6579 nem na 5938.
- **Documentação da API de Pesquisas:** a sintaxe `N6[N3[42]]`, o significado oficial de `-` e os filtros de período.
- **API de Localidades:** o ano da divisão em regiões imediatas e intermediárias (2017) e o fato de a API não versionar o recorte por data.

## 8. Sugestões para o D11+

As sugestões anteriores foram decididas no D10 e incorporadas às seções 1, 3, 4 e 5 (ver `docs/decisoes.md`). Não há sugestões pendentes.
