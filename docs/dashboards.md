# Dashboards: narrativa, páginas e KPIs

- **Versão:** 2026-11-24 (cartão D34)
- **Vale para:** o app Streamlit (D36, construído primeiro) e o dashboard Power BI (D35, construído depois, com o Streamlit como referência). Os dois seguem esta especificação; uma diferença entre eles é defeito, e não escolha de design.
- **Base:** `CLAUDE.md` (regras 1–13), `docs/escopo_mvp.md`, `docs/limitacoes.md`, `docs/fontes/alertas_qualidade_2026-11.md` e os notebooks `01_populacao`, `02_pib` e `03_conclusoes` (D31–D33).
- **Fonte dos dados:** só as views do schema `gold`, lidas como `bed_readonly`. Nenhum dashboard lê `silver` ou `raw`.

## 1. Narrativa

### Pergunta central

*Como os municípios de Santa Catarina se diferenciam em população e dimensão econômica, e como esses indicadores evoluíram entre 2010 e 2023?*

Resposta curta, a partir das saídas do `03_conclusoes`: nenhum município passa de 10% da população (máximo: Joinville, 8,1% no Censo 2022) nem do PIB (máximo: Joinville, 9,7% em 2023). Os dez maiores ficam abaixo de metade dos dois totais (40,6% da população e 46,1% do PIB) e estão em 6 das 7 regiões intermediárias.

### Perguntas derivadas

A pergunta 5 do escopo (composição setorial) é extensão (decisão D10) e não entra nos dashboards.

| # | Pergunta | Achado dos notebooks (só números calculados) | Ressalva que acompanha | Páginas |
|---|---|---|---|---|
| P1 | Quais municípios concentram população e PIB, e quanto representam do total estadual? | Os 10 maiores somam 40,6% da população (Censo 2022) e 46,1% do PIB (2023). Metade da população está em 17 municípios; metade do PIB, em 13. Itajaí é o 5º em população e o 2º em PIB. | PIB municipal é distribuição do PIB estadual por indicadores (limitações, seção 6). | Visão geral, População, Economia |
| P2 | Como a população de cada município variou entre os Censos de 2010 e 2022? | SC: +21,8% (6,25 mi → 7,61 mi). Dos 293 comparáveis, 223 cresceram e 70 perderam; mediana de +6,8%. Regiões de Florianópolis (+33,8%) e Blumenau (+30,9%) cresceram mais; 36 das 70 perdas estão na região de Chapecó e 14 na de Lages. | Sem Censo 2010 para os dois municípios instalados em 2013. Queda de Laguna (−17%) por desmembramento é NÃO CONFIRMADA. | População, Perfil, Comparação |
| P3 | Como o PIB nominal de cada município evoluiu entre 2010 e 2023? | PIB nominal de SC: R$ 153,7 bi → R$ 513,4 bi (3,34 vezes, valores correntes). Participação: Itajaí 6,5% → 9,4%; Joinville 11,9% → 9,7%; os 10 maiores de 2023, 48,6% → 46,1%. | Nominal, nunca crescimento real (regra 3). 2021–2023 revisados em 19/12/2025. Saltos acima de 50% em municípios pequenos (alerta A1). | Visão geral, Economia, Perfil, Comparação |
| P4 | Como os municípios se comparam em PIB per capita em um mesmo ano? | 2023: mediana entre os municípios R$ 52.591; maior Araquari (R$ 218.626), menor Pescaria Brava (R$ 16.142), razão de 13,5 vezes. Seis dos dez maiores têm menos de 10 mil habitantes (Censo 2022). | Per capita publicado, não é renda; denominador muda conforme o ano (regra 4; limitações, seção 9). | Economia, Perfil, Comparação |

**Critério de texto (o mesmo da D31):** todo número escrito num dashboard vem de uma consulta à GOLD feita na hora (Streamlit) ou de uma medida sobre a GOLD (Power BI). Nenhum número digitado à mão nos textos. Sem comparação com outros estados, sem rótulos geográficos que o banco não tem ("litoral", "Oeste") e sem adjetivo sem número. O que `docs/limitacoes.md` marca como NÃO CONFIRMADO aparece como hipótese.

## 2. Regras de construção que valem para todos os visuais

| Código | Regra | Origem |
|---|---|---|
| C1 | Totais de estado e de região vêm de `gold.agregado_regiao_ano`. O dashboard nunca soma municípios para obter um total, porque a soma de `pop_estimada` 2012 teria dupla contagem. | Regra 13 |
| C2 | Participação no total do estado vem de `gold.participacao_estadual.participacao_percentual`. Participação regional (região ÷ estado) é calculada entre duas linhas de `agregado_regiao_ano` do mesmo indicador e ano. | Regra 13 |
| C3 | Valores exibidos como vêm da GOLD (R$, pessoas, %). Abreviar ("R$ 513,4 bi") só na formatação do rótulo; nenhuma medida multiplica ou divide por potência de 10. No Power BI, usar unidades de exibição ou formato, nunca `/ 1e9` numa medida DAX. | Regra 11 |
| C4 | Ausência aparece como "sem dado" (ou o `motivo` da view), nunca como zero nem como barra vazia sem legenda. | Regra 5 |
| C5 | Censo (`pop_censo`) e estimativa (`pop_estimada`) nunca na mesma série, linha ou coluna de tabela sem rótulo. Todo título ou eixo de população diz "Censo" ou "Estimativa". | Regra 2 |
| C6 | Todo visual de PIB tem "nominal" ou "valores correntes" no título ou no eixo. | Regra 3 |
| C7 | Todo visual de per capita tem a nota "PIB per capita publicado pelo IBGE; não é renda". | Regra 4 |
| C8 | Série de `pop_estimada`: uma linha por `base_estimativa`, sem ligar pontos de bases diferentes, com marcações em 2013 ("quebra de série: nova projeção") e 2018 ("revisão da projeção"). | Regra 12 |
| C9 | Rodapé de cada página: "Fonte: IBGE (SIDRA e API de Pesquisas), elaboração própria." | D31 |
| C10 | No Power BI, toda coluna numérica do modelo fica com resumo padrão "Não resumir". Agregação só em medidas explícitas desta especificação. | Regra 4, C1 |

## 3. Filtros globais

Três filtros valem para o app inteiro. No Streamlit, ficam na barra lateral e em `st.session_state`; no Power BI, são segmentações sincronizadas entre as páginas.

| Filtro | Valores | Padrão |
|---|---|---|
| **Região intermediária** | as 7 de `gold.dim_municipio.nome_regiao_intermediaria`, mais "Santa Catarina (todas)" | Santa Catarina |
| **Município** | os 295 de `gold.dim_municipio`, em ordem alfabética; a lista respeita a região escolhida | Florianópolis |
| **Ano** | 2010 a 2023, seleção única | 2023 |

**O filtro de ano nunca troca o indicador de população.** Ele age sobre PIB, PIB per capita, participação no PIB e `pop_estimada`. Os visuais de Censo têm anos fixos (2010 e 2022) e não respondem ao filtro de ano. Num ano sem estimativa publicada (2010, 2022 e 2023), os visuais de `pop_estimada` mostram "sem estimativa publicada em AAAA" e não usam o Censo no lugar (limitações, seção 4). As séries temporais mostram o período inteiro e só destacam o ano escolhido.

Quais visuais cada filtro afeta (os códigos dos visuais estão na seção 4):

| Visual | Região | Município | Ano |
|---|---|---|---|
| VG1 cartões | sim (total da região) | não | só o cartão de PIB |
| VG2 série do PIB | sim (total da região) | não | destaca o ano |
| VG3 concentração | não (é sempre o estado) | não | só a barra de PIB |
| VG4 PIB × população por região | não | não | não (2010 e 2022 fixos) |
| POP1 ranking Censo | sim | destaca | não (Censo 2010 ou 2022, seletor local) |
| POP2 variação entre Censos | sim | destaca | não |
| POP3 variação por região | não | não | não |
| POP4 série da estimativa | sim (total da região) | não | destaca o ano |
| ECO1 ranking PIB | sim | destaca | sim |
| ECO2 participação 2010 × ano | sim | destaca | sim |
| ECO3 ranking per capita | sim | destaca | sim |
| ECO4 saltos acima de 50% | sim | destaca | não |
| PER1–PER5 | não | sim (define a página) | PER1 sim; séries destacam o ano |
| CMP1–CMP4 | não | não (seleção própria) | CMP2 e CMP3 sim; séries destacam o ano |
| SOB1–SOB3 | não | não | não |

"Destaca" quer dizer: o município escolhido aparece em outra cor ou com marcador, sem filtrar os outros.

## 4. Páginas e visuais

Em cada visual: a pergunta, a view, a medida exata, o tipo de gráfico, os filtros e o aviso que tem de aparecer junto. "Região" e "Ano" nas medidas são os valores dos filtros globais.

### 4.1 Visão geral

Responde à pergunta central em uma tela.

| ID | Pergunta | View | Medida | Gráfico | Filtros | Aviso junto |
|---|---|---|---|---|---|---|
| VG1 | Qual o tamanho de SC (ou da região)? | `agregado_regiao_ano`, `dim_municipio` | Três cartões: (a) `valor` de `pop_censo`, ano 2022, rótulo "População (Censo 2022)"; (b) `valor` de `pib_corrente` no Ano, rótulo "PIB nominal AAAA"; (c) contagem de `cod_municipio` em `dim_municipio`. Nível `estado` ou `regiao_intermediaria` conforme a Região. | Cartões | Região; Ano só em (b) | "PIB nominal, valores correntes" (regra 3) |
| VG2 | Como o PIB nominal evoluiu de 2010 a 2023? | `agregado_regiao_ano` | `valor` de `pib_corrente` por `ano`, nível conforme a Região | Colunas por ano, ano escolhido destacado | Região; Ano (destaque) | "Valores correntes: a variação inclui inflação e não é crescimento real" (regra 3); "2021–2023 revisados pelo IBGE em 19/12/2025; 2022–2023 sujeitos a revisão" (limitações, seção 5) |
| VG3 | Quanto os 10 maiores concentram? | `participacao_estadual` | Soma de `participacao_percentual` dos 10 maiores por `valor`: (a) `pop_censo` 2022; (b) `pib_corrente` no Ano. Texto auxiliar: menor N de municípios cuja soma ordenada passa de 50%. | Duas barras horizontais (0–100%) | Ano só em (b) | Rótulos "Censo 2022" e "PIB nominal AAAA"; "PIB municipal é distribuição do PIB estadual" (limitações, seção 6) |
| VG4 | Quais regiões pesam mais no PIB que na população? | `agregado_regiao_ano` | Por região intermediária: `valor` da região ÷ `valor` do estado, para `pib_corrente` e para `pop_censo`, no mesmo ano (2010 ou 2022, seletor local; padrão 2022) | Barras agrupadas por região (PIB × população) | nenhum global | "Comparação entre participações; não é PIB per capita regional" (regra 4) |

### 4.2 População

Responde a P1 (população) e P2.

| ID | Pergunta | View | Medida | Gráfico | Filtros | Aviso junto |
|---|---|---|---|---|---|---|
| POP1 | Quais municípios têm mais moradores? | `participacao_estadual` | `valor` e `participacao_percentual` de `pop_censo` no ano do seletor local (2010 ou 2022), os 15 maiores dentro da Região | Barras horizontais com rótulo de % do estado | Região; Município (destaque) | "Censo AAAA"; em 2010, os 2 municípios instalados em 2013 aparecem como "não instalado" (regra 6) |
| POP2 | Quem mais ganhou e perdeu população entre os Censos? | `variacao_populacao_censo` | `variacao_absoluta` e `variacao_percentual`; seletor local entre absoluta e percentual; 10 maiores ganhos e 10 maiores perdas dentro da Região. Cartão auxiliar: municípios com `variacao_absoluta` > 0 e < 0 e mediana de `variacao_percentual` | Barras divergentes | Região; Município (destaque) | `motivo` dos 2 sem Censo 2010; Laguna: "queda pode vir do desmembramento de Pescaria Brava (NÃO CONFIRMADO)"; "Censo 2022 tem duas apurações" (limitações, seção 8) |
| POP3 | Que regiões cresceram mais entre os Censos? | `agregado_regiao_ano` | Por região intermediária: (`valor` 2022 − `valor` 2010) ÷ `valor` 2010 de `pop_censo` | Barras horizontais ordenadas | nenhum global | Região de Criciúma: "inclui os 2 municípios instalados em 2013; mesmo território só se a população deles estava em Laguna e Içara em 2010 (NÃO CONFIRMADO)" |
| POP4 | Como a estimativa anual evoluiu? | `agregado_regiao_ano` | `valor` de `pop_estimada` por `ano` (2011–2021) e `base_estimativa`, nível conforme a Região | Linhas, uma por base, sem ligar bases; linhas verticais em 2013 e 2018 | Região; Ano (destaque) | Regra 12 (C8); em 2012, o `aviso` da view (regra 13: total sem 4212650 e 4220000); "a variação oficial é Censo 2010 × 2022" |

### 4.3 Economia

Responde a P1 (PIB), P3 e P4.

| ID | Pergunta | View | Medida | Gráfico | Filtros | Aviso junto |
|---|---|---|---|---|---|---|
| ECO1 | Quais municípios concentram o PIB? | `participacao_estadual` | `valor` e `participacao_percentual` de `pib_corrente` no Ano, os 15 maiores dentro da Região | Barras horizontais com % do estado | Região; Ano; Município (destaque) | "PIB nominal AAAA" (regra 3); limitações, seção 6 |
| ECO2 | Quem ganhou e perdeu participação no PIB? | `participacao_estadual` | Para os 10 maiores do Ano: `participacao_percentual` em 2010 e no Ano, e a diferença em pontos percentuais | Halteres (dois pontos por município) | Região; Ano; Município (destaque) | "A participação é uma razão no mesmo ano e não depende da inflação geral, mas reflete diferenças de preços entre atividades"; PIB nominal (regra 3) |
| ECO3 | Como os municípios se comparam em PIB per capita? | `painel_municipio_ano` | `pib_per_capita_reais` no Ano, sem agregação; 10 maiores e 10 menores dentro da Região. Linha de referência rotulada "mediana entre os municípios": mediana de `pib_per_capita_reais` no Ano entre os municípios da Região (295 valores no estado) | Barras horizontais (duas listas) com linha da mediana | Região; Ano; Município (destaque) | C7 (regra 4); "o denominador muda conforme o ano" (limitações, seção 9); A1 para municípios pequenos no topo |
| ECO4 | Onde houve saltos anuais de PIB acima de 50%? | `variacao_anual` | Linhas com `codigo_indicador = 'pib_corrente'` e `abs(variacao_percentual) > 50`: município, `ano_anterior`, `ano`, `variacao_percentual`; cartão com a contagem de variações e de municípios | Tabela ordenada por módulo da variação | Região; Município (destaque) | Alerta A1: "em municípios pequenos, a entrada ou saída de um estabelecimento pode multiplicar o PIB de um ano para outro; a causa de cada caso é NÃO CONFIRMADA"; variação nominal (regra 3) |

### 4.4 Perfil do município

Uma página por município, definida pelo filtro Município. Junta P1 a P4 para um município só.

| ID | Pergunta | View | Medida | Gráfico | Filtros | Aviso junto |
|---|---|---|---|---|---|---|
| PER1 | Qual o retrato do município? | `variacao_populacao_censo`, `participacao_estadual`, `painel_municipio_ano`, `dim_municipio` | Cartões: `pop_censo_2010`, `pop_censo_2022`, `variacao_percentual` (ou `motivo`); `pib_corrente_reais` e `pib_per_capita_reais` no Ano; posição no ranking de `pib_corrente` do Ano e de `pop_censo` 2022 (ordem de `valor` em `participacao_estadual`); regiões intermediária e imediata | Cartões | Município; Ano | C5, C6, C7; para 4212650 e 4220000: "instalado em 2013; sem dado antes disso" (regras 6 e 10) |
| PER2 | Como o PIB nominal do município evoluiu? | `variacao_anual`, `painel_municipio_ano` | `pib_corrente_reais` por ano; rótulo com `variacao_percentual` de `variacao_anual` | Colunas por ano | Município; Ano (destaque) | Regra 3; se houver `abs(variacao_percentual) > 50`, a nota do alerta A1 aparece no visual |
| PER3 | Como a população do município evoluiu? | `painel_municipio_ano` | Dois gráficos lado a lado: (a) `pop_estimada` por ano, uma linha por `base_estimativa`; (b) `pop_censo` 2010 e 2022 | (a) linhas com quebras; (b) duas colunas | Município; Ano (destaque em a) | Regra 12 (C8) em (a); regra 2: títulos "Estimativa" e "Censo", gráficos separados; `aviso` de 2012 nos 2 municípios novos (regra 13) |
| PER4 | Como o PIB per capita evoluiu? | `painel_municipio_ano` | `pib_per_capita_reais` por ano | Linha | Município; Ano (destaque) | C7 (regra 4); "o denominador muda conforme o ano: estimativa até 2021, 1ª apuração do Censo em 2022" (limitações, seção 9) |
| PER5 | O município ganhou ou perdeu peso no PIB do estado? | `participacao_estadual` | `participacao_percentual` de `pib_corrente` por ano | Linha | Município; Ano (destaque) | "Razão no mesmo ano; não depende da inflação geral" |

### 4.5 Comparação

Compara de 2 a 5 municípios, escolhidos num seletor próprio da página (padrão: Joinville, Florianópolis, Itajaí). O filtro global Município não age aqui.

| ID | Pergunta | View | Medida | Gráfico | Filtros | Aviso junto |
|---|---|---|---|---|---|---|
| CMP1 | Como evoluiu o peso de cada um no PIB do estado? | `participacao_estadual` | `participacao_percentual` de `pib_corrente` por ano; seletor local para trocar por `valor` (PIB nominal em R$) | Linhas, uma por município | seleção da página; Ano (destaque) | Com R$: "PIB nominal, valores correntes" (regra 3) |
| CMP2 | Como se comparam em PIB per capita? | `painel_municipio_ano` | `pib_per_capita_reais` no Ano | Barras | seleção da página; Ano | C7 (regra 4) |
| CMP3 | Como variou a população entre os Censos? | `variacao_populacao_censo` | `pop_censo_2010`, `pop_censo_2022` e `variacao_percentual` | Barras agrupadas (2010 × 2022) com rótulo da variação | seleção da página | `motivo` quando não há variação; "Censo" no título (regra 2) |
| CMP4 | Tabela de valores do ano | `painel_municipio_ano` | `pop_estimada` (com `base_estimativa`), `pop_censo`, `pib_corrente_reais`, `pib_per_capita_reais` no Ano | Tabela | seleção da página; Ano | Colunas separadas para estimativa e Censo (regra 2); célula vazia mostra "sem dado" (regra 5); `aviso` quando houver |

### 4.6 Sobre os dados

Para quem quer saber de onde vêm os números e o que eles não dizem.

| ID | Conteúdo | View | Medida | Formato |
|---|---|---|---|---|
| SOB1 | Fontes e séries | `grade_indicador_municipio_ano` | Por `cod_serie`: `fonte`, `codigo_indicador`, `tipo_medida`, `unidade`, anos (mín. e máx.) e `max(data_coleta)` | Tabela |
| SOB2 | Cobertura | `grade_indicador_municipio_ano` | Contagem por `codigo_indicador` e `status` (`com_valor`, `municipio_nao_instalado`, `sem_dado`) | Tabela |
| SOB3 | Regras de leitura | — | Texto fixo com as regras 2, 3, 4, 5, 12 e 13, o alerta A1 e o link para `docs/limitacoes.md` | Texto |

O texto de SOB3 é o único texto fixo do app, porque não traz números.

## 5. Proibições

1. **Nenhum per capita agregado** (regra 4): nem soma, nem média, nem média ponderada de `pib_per_capita_reais`, nem PIB regional dividido por população regional. A única estatística permitida sobre o per capita é a mediana de um mesmo ano (ECO3), sempre com o rótulo **"mediana entre os municípios"** em todo lugar onde aparecer (título, legenda, cartão, dica de ferramenta), e nunca apresentada como per capita do estado ou da região.
2. **PIB sempre rotulado como nominal** (regra 3). Variação de PIB entre anos é "variação nominal", nunca "crescimento", "crescimento econômico" ou "crescimento real".
3. **PIB per capita nunca como renda** (regra 4): nada de "renda", "renda média" ou "riqueza dos moradores".
4. **Variação de `pop_estimada` entre bases** (regra 12): a de 2012 para 2013 **não é exibida** (a view devolve `NULL`; o visual mostra o `motivo`). A de 2017 para 2018 só aparece **com o aviso** "revisão da projeção: o IBGE declara comparáveis só 2013–2017". Nenhuma linha liga pontos de bases diferentes.
5. **Censo e estimativa nunca na mesma série** (regra 2): nada de série "população 2010–2023" que use Censo em 2010 e 2022 e estimativa no resto, nem filtro de ano que troque de um para o outro.
6. **Nada de total somado no dashboard** (C1): somar `pop_estimada` 2012 por município daria a dupla contagem da regra 13.
7. **Ausência não vira zero** (regra 5), e nenhum valor é interpolado (2010, 2022 e 2023 não têm estimativa).
8. **Nenhuma conversão de unidade** nas medidas (regra 11).
9. **Sem comparação com outros estados ou com o Brasil**: o projeto não tem esses dados (D01).

## 6. Números de referência para o D37

Valores consultados em 2026-11-24 nas views aplicadas, como `bed_readonly`, numa transação `READ ONLY`. No D37, cada um deve aparecer igual no Streamlit, no Power BI e nesta consulta. Se a GOLD for recarregada (por exemplo, numa revisão do PIB pelo IBGE), os valores atuais mudam e a tabela é atualizada junto com a recarga.

| # | O que é | Consulta na GOLD | Valor atual | Onde aparece |
|---|---|---|---|---|
| R01 | População de SC, Censo 2022 | `SELECT valor FROM gold.agregado_regiao_ano WHERE nivel = 'estado' AND codigo_indicador = 'pop_censo' AND ano = 2022;` | 7.610.361 | VG1 |
| R02 | População de SC, Censo 2010 | `SELECT valor FROM gold.agregado_regiao_ano WHERE nivel = 'estado' AND codigo_indicador = 'pop_censo' AND ano = 2010;` | 6.248.436 (293 municípios) | POP3 |
| R03 | PIB nominal de SC, 2023 | `SELECT valor FROM gold.agregado_regiao_ano WHERE nivel = 'estado' AND codigo_indicador = 'pib_corrente' AND ano = 2023;` | R$ 513.392.972.000,00 | VG1, VG2 |
| R04 | PIB nominal de SC, 2010 | `SELECT valor FROM gold.agregado_regiao_ano WHERE nivel = 'estado' AND codigo_indicador = 'pib_corrente' AND ano = 2010;` | R$ 153.726.009.000,00 | VG2 |
| R05 | Estimativa de SC, 2012 (regra 13) | `SELECT valor, municipios_somados, municipios_excluidos FROM gold.agregado_regiao_ano WHERE nivel = 'estado' AND codigo_indicador = 'pop_estimada' AND ano = 2012;` | 6.362.734 (293 somados, 2 excluídos) | POP4 |
| R06 | 3 maiores em população, Censo 2022 | `SELECT nome_municipio, valor, participacao_percentual FROM gold.participacao_estadual WHERE codigo_indicador = 'pop_censo' AND ano = 2022 ORDER BY valor DESC LIMIT 3;` | Joinville 616.317 (8,0984%); Florianópolis 537.211 (7,0589%); Blumenau 361.261 (4,7470%) | POP1 |
| R07 | 3 maiores em PIB nominal, 2023 | `SELECT nome_municipio, valor, participacao_percentual FROM gold.participacao_estadual WHERE codigo_indicador = 'pib_corrente' AND ano = 2023 ORDER BY valor DESC LIMIT 3;` | Joinville R$ 49.815.877.000,00 (9,7033%); Itajaí R$ 48.195.909.000,00 (9,3877%); Florianópolis R$ 31.190.132.000,00 (6,0753%) | ECO1 |
| R08 | Florianópolis nos Censos 2010 e 2022 | `SELECT pop_censo_2010, pop_censo_2022, variacao_percentual FROM gold.variacao_populacao_censo WHERE cod_municipio = '4205407';` | 421.240 → 537.211 (+27,53%) | PER1, CMP3 |
| R09 | Participação de Itajaí no PIB, 2010 e 2023 | `SELECT ano, participacao_percentual FROM gold.participacao_estadual WHERE cod_municipio = '4208203' AND codigo_indicador = 'pib_corrente' AND ano IN (2010, 2023) ORDER BY ano;` | 6,5444% (2010) → 9,3877% (2023) | ECO2, PER5, CMP1 |
| R10 | Municípios comparáveis e que perderam população entre os Censos | `SELECT count(variacao_percentual) AS comparaveis, count(*) FILTER (WHERE variacao_absoluta < 0) AS perderam FROM gold.variacao_populacao_censo;` | 293 comparáveis; 70 perderam | POP2 |
| R11 | Maior PIB per capita, 2023 | `SELECT nome_municipio, pib_per_capita_reais FROM gold.painel_municipio_ano WHERE ano = 2023 ORDER BY pib_per_capita_reais DESC LIMIT 1;` | Araquari, R$ 218.625,97 | ECO3 |
| R12 | PIB per capita 2023: mediana entre os municípios | `SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY pib_per_capita_reais) AS mediana, count(pib_per_capita_reais) AS municipios FROM gold.painel_municipio_ano WHERE ano = 2023;` | R$ 52.591,20 (295 municípios) | ECO3 |
| R13 | Saltos anuais de PIB nominal acima de 50% (alerta A1) | `SELECT count(*) AS variacoes, count(DISTINCT cod_municipio) AS municipios FROM gold.variacao_anual WHERE codigo_indicador = 'pib_corrente' AND abs(variacao_percentual) > 50;` | 61 variações em 51 municípios | ECO4 |
| R14 | Variação da estimativa 2012→2013 (regra 12) | `SELECT count(*) AS pares, count(variacao_percentual) AS com_variacao, bool_or(comparavel) AS algum_comparavel FROM gold.variacao_anual WHERE codigo_indicador = 'pop_estimada' AND ano = 2013;` | 295 pares; 0 com variação; nenhum comparável | POP4, PER3 |
| R15 | Variação da estimativa 2017→2018 (regra 12) | `SELECT count(*) AS pares, count(variacao_percentual) AS com_variacao, bool_or(comparavel) AS algum_comparavel FROM gold.variacao_anual WHERE codigo_indicador = 'pop_estimada' AND ano = 2018;` | 295 pares; 295 com variação; nenhum comparável | POP4, PER3 |

Códigos usados: Florianópolis `4205407`, Itajaí `4208203`.

## 7. Implementação (para o D36 e o D35)

- **Ordem:** Streamlit primeiro (D36), Power BI depois (D35), com o Streamlit como referência de layout, textos e números (decisão de 2026-11-24).
- **Streamlit:** consultas em arquivos `.sql` que só leem `gold`, como em `sql/analise/`, pela conexão `bed_readonly` em transação `READ ONLY`. A lógica de cálculo (rankings, medianas, participação regional) fica em funções testáveis, separada da interface. O pacote `streamlit` (e a biblioteca de gráficos) ainda não está no `requirements.txt` e precisa de aprovação no D36.
- **Power BI:** conexão ao PostgreSQL com `bed_readonly`, importando só as views desta especificação. Medidas DAX nomeadas como os códigos das seções 4 e 6, para facilitar o D37.

## 8. Extensões (fora do MVP)

- **Mapa municipal (coroplético):** exige a malha municipal do IBGE (API de Malhas ou arquivos de geometria), que é uma fonte nova. Antes de entrar, precisa de validação pelo pesquisador-de-fontes, registro em `docs/fontes/`, extrator com RAW imutável e decisão sobre a versão da malha, que tem de conter os 295 municípios atuais, inclusive 4212650 e 4220000. Os mesmos avisos dos visuais acima valeriam para o mapa (per capita não agregado, PIB nominal, Censo separado da estimativa).
- As demais extensões do projeto (composição setorial, PIB deflacionado, outros estados) estão em `docs/escopo_mvp.md` e não têm visual previsto aqui.
