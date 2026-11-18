# Alertas de qualidade A1, A2 e A3: explicação em fontes oficiais do IBGE

- **Data da consulta:** 2026-11-18
- **Insumo para:** cartão D27 (documentação de limitações)
- **Origem dos alertas:** `reports/qualidade_20261118.md`, seções 4.2, 5.1, 5.2 e 7
- **Método:** leitura de documentos oficiais do IBGE (FTP, Biblioteca, API de Metadados, API de Notícias) e conferência numérica com arquivos oficiais e com a API SIDRA. Nenhum acesso ao banco.

> O PIB é **nominal** (preços correntes). Nenhuma variação nominal deste documento é crescimento real. Onde aparece "volume", o número vem das tabelas de volume das Contas Regionais do IBGE, e não de cálculo do projeto.

## Resumo

| Alerta | Conclusão | Explicação em uma linha |
|---|---|---|
| **A3** População estimada 2013 | **CONFIRMADO** | As estimativas de 2013 passaram a usar a nova Projeção da População 2013 (método das componentes por UF) e as populações dos Censos 2000 e 2010 **ajustadas** por um fator de cobertura. As de 2011 e 2012 usavam a base anterior. O IBGE declara que só 2013–2017 são comparáveis entre si. O salto de 2012 para 2013 é quebra de série, não crescimento demográfico. |
| **A2** Soma do PIB nominal de SC em 2021 | **PARCIAL** | Pelas tabelas oficiais das Contas Regionais, os +22,70% nominais de SC em 2021 se dividem em volume de +6,81% e preço implícito de +14,88%, o maior dos dois componentes desde 2010. O Brasil também teve salto nominal (+18,43%). O total de SC de 2021 **não mudou** na revisão de 19/12/2025; mudou só a distribuição entre municípios. Não encontrei nenhum texto oficial que comente SC especificamente. |
| **A1** Variações municipais acima de 50% | **PARCIAL** | A nota metodológica explica o mecanismo: o PIB municipal é a **distribuição** do valor adicionado estadual por indicadores, e a indústria de transformação usa dados de saídas de mercadorias da SEFAZ. A base oficial mostra que os saltos vêm de blocos de indústria e serviços que aparecem e somem. Que Lajeado Grande tenha usina hidrelétrica é **NÃO CONFIRMADO**, e a base oficial não aponta eletricidade entre as 3 maiores atividades do município em 2012. |

---

## A3: estimativa de população em 2013 (prioridade)

### Pergunta

Por que a estimativa da tabela 6579 (variável 9324) sobe em média 2,55% por município de SC de 2012 para 2013, contra 0,1% a 0,6% nos outros anos? Houve mudança de metodologia, de base ou de projeção?

### O que foi encontrado

**1. A nota metodológica das estimativas de 2013 descreve a mudança.**
Fonte: "Estimativas da população residente nos municípios brasileiros com data de referência em 1º de julho de 2013", agosto de 2013. URL: https://biblioteca.ibge.gov.br/visualizacao/livros/liv97742.pdf (a API de Metadados aponta para este link; ver item 3).

> "Este ano, o IBGE divulga a projeção da população para as Unidades da Federação do país, por sexo e idade, pelo método das componentes demográficas, o que representa um aprimoramento metodológico. Dessa forma, as estimativas da população residente para os municípios brasileiros, com data de referência em 1º de julho de 2013, foram elaboradas a partir dessa projeção para cada estado, incorporando os resultados dos parâmetros demográficos calculados com base nos resultados do Censo Demográfico 2010 [...]"

> "Os totais populacionais dos municípios, enumerados pelos Censos Demográficos 2000 e 2010, foram ajustados linearmente, utilizando-se o fator de ajuste aplicado nestes anos em cada Unidade da Federação. Esses totais populacionais municipais, em 2000 e 2010, serviram de base para o estabelecimento da tendência de crescimento de cada município no cálculo das estimativas municipais, com data de referência em 1º de julho de 2013."

> "Este ano, as estimativas das populações dos municípios com data de referência em 1º de julho de 2013, utilizou como área maior na aplicação da metodologia, as Unidades da Federação projetadas pelo método das componentes demográficas."

A mesma nota define o método de tendência (Madeira e Simões, 1972), `Pi(t) = ai·P(t) + bi`, o chamado AiBi, e diz que `Pi(t0)` e `Pi(t1)` são as populações de 2000 e 2010 "ajustada[s]". **O método AiBi não mudou. Mudaram a área maior (a nova projeção por UF) e os pontos de partida (Censos ajustados).**

**2. A Projeção da População 2013 introduz o ajuste das populações de partida.**
Fontes: https://ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2013/nota_metodologica_2013.pdf e https://ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2013/srm40_projecao_da_populacao.pdf (Série Relatórios Metodológicos 40).

> "As projeções elaboradas trazem importantes inovações, como: correção da estrutura etária das populações de partida; projeções populacionais das Unidades da Federação pelo método das componentes demográficas [...]" (nota_metodologica_2013, seção 2)

> "O fator de ajuste obtido para a população total do Brasil, em 2000, através da realização da conciliação demográfica, foi utilizado como parâmetro para ajustar as populações de partida das Unidades da Federação. Este fator foi ponderado pelo padrão de omissão censitária observado na Pesquisa de Avaliação de Cobertura da Coleta do Censo Demográfico 2000 [...]" (nota_metodologica_2013, seção 3.3; texto equivalente no srm40)

> "Este ano o IBGE divulga, pela primeira vez, as projeções da população por sexo e idade para as Unidades da Federação pelo método das componentes demográficas [...]" (srm40, Introdução)

**3. A API de Metadados do IBGE registra a quebra de comparabilidade.**
URLs: `https://servicodados.ibge.gov.br/api/v2/metadados/XF/{ano}/0`, com ano de 2011 a 2021 consultados (2011, 2012, 2013, 2014, 2017, 2018, 2019, 2021). O código da pesquisa "Estimativas de População" é `XF`, conforme https://servicodados.ibge.gov.br/api/v2/metadados/pesquisas. Campos `qualidade`:

> `comparabilidade_ao_longo_tempo`: "A comparabilidade temporal é comprometida por ocasião das revisões da projeção de população e por motivo de alteração de limites territoriais."

> `longitude_series_temporais_comparaveis`: "As estimativas de 2013 a 2017 são comparáveis, excetuando-se os municípios que apresentaram alteração nos seus limites territoriais."

> `metodologia` (todos os anos): "As populações das Unidades da Federação são obtidas, a cada ano, da última projeção populacional disponível. [...] Dessa forma, a comparação histórica das estimativas anuais deve ser feita com cautela."

**4. A nota técnica da série TCU separa 2011–2012 de 2013.**
Fonte: https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2013/serie_2001_2013_TCU.pdf

> "6) 2011 e 2012: estimativas das populações residentes municipais calculadas com base na Projeção Populacional para o Brasil [...]"
> "7) 2013: Projeção da população para o Brasil e Unidades da Federação, por sexo e idade, 2013 [...]"

A nota não diz qual revisão da projeção foi usada em 2011–2012, nem como se obteve o total por UF nesses anos: **NÃO CONFIRMADO**. As páginas de metodologia de 2011 e 2012 ficam no portal antigo (`www.ibge.gov.br/home/...`), atrás de Cloudflare.

**5. Conferência numérica (dados oficiais).**

| Série | 2010 | 2011 | 2012 | 2013 | 2014 | Fonte |
|---|---|---|---|---|---|---|
| Censo 2010, SC | 6.248.436 | | | | | SIDRA 1378 (URL R5) |
| Estimativa publicada, SC (N3) | | 6.317.054 | 6.362.734 | 6.634.254 | 6.727.148 | SIDRA 6579 (URL R3) |
| Projeção 2013, SC, 1º de julho | 6.351.418 | 6.446.209 | 6.540.596 | 6.634.254 | 6.727.148 | `PROJECOES_2013_POPULACAO.ods`, aba SC, "POPULAÇÃO TOTAL", linha Total |

- A estimativa de 2013 e a de 2014 são **idênticas** à Projeção 2013 de SC. Isso confirma que a área maior passou a ser a nova projeção.
- Na nova projeção, SC em 2012 já é 6.540.596, ou **+2,80%** acima da estimativa publicada para 2012 (6.362.734). Na mesma projeção, o crescimento de 2012 para 2013 é de só +1,43%. **O salto de +4,27% na estimativa estadual de 2012 para 2013 é, portanto, sobretudo uma mudança de nível da série**, e não crescimento no ano.
- A população de partida de 2010 na Projeção 2013 (6.351.418) é 1,65% maior que o Censo 2010 (6.248.436). A diferença mistura o fator de ajuste com a mudança de data de referência (1º de agosto para 1º de julho). As fontes lidas não permitem separar as duas partes.
- O Brasil teve o mesmo comportamento: de 193.904.015 em 2012 para 201.032.714 em 2013 (+3,68%), contra +0,79% de 2011 para 2012 (SIDRA 6579, N1). O efeito é nacional, não só de SC.
- Por que o salto médio municipal (+2,55%) é menor que o estadual (+4,27%) **NÃO foi verificado**. Hipótese: o ajuste linear dos Censos combinado com a tendência AiBi pesa mais nos municípios grandes e de crescimento rápido, o que é compatível com o topo da lista do relatório (Araquari, Itapema...).

**6. Achado lateral: a soma municipal de 2012 não fecha com o total de SC.**
Por SIDRA 6579, a soma dos 295 municípios em 2012 é 6.383.286, enquanto o valor N3 de SC é 6.362.734. A diferença, 20.552, é exatamente a soma de Pescaria Brava (9.416) e Balneário Rincão (11.136). Em 2011 e 2013 a soma municipal é igual ao N3. Por isso o relatório (soma municipal) mostra +3,93% em 2013, e o N3 mostra +4,27%. A causa da diferença de 2012 é **NÃO CONFIRMADA**. Ela se liga às observações O3 e O4 do relatório (Içara e Laguna em 2012).

**7. Há outra revisão de projeção em 2018 (não sinalizada pela auditoria).**
Fonte: https://biblioteca.ibge.gov.br/visualizacao/livros/liv101609.pdf (estimativas de 2018).

> "As novas populações dos estados, utilizadas como balizadores na aplicação da metodologia, também impactaram nas estimativas das populações municipais a partir de 2018."

Em SC, a variação estadual de 2017 para 2018 foi +1,06% (7.001.161 para 7.075.494, SIDRA 6579 N3), sem salto visível. Mesmo assim, pelo metadado oficial, a série é comparável só em 2013–2017.

### Conclusão: **CONFIRMADO**

O salto de 2013 é uma quebra metodológica documentada pelo IBGE: nova projeção por UF (método das componentes) e Censos 2000 e 2010 ajustados por fator de cobertura como base da tendência municipal. Não é erro de carga nem crescimento populacional real.

### Implicação para o D27 (limitações)

- Documentar que a série `pop_estimada` (6579) tem **quebras em 2013 e em 2018** por revisão da projeção, e que o IBGE só declara comparáveis 2013–2017.
- Não interpretar a variação de 2012 para 2013 (nem a de 2017 para 2018) como crescimento demográfico. Em gráficos de série, marcar a quebra.
- O PIB per capita de 2011–2012 usa no denominador a estimativa da base antiga, e o de 2013 em diante, a nova (ver `sidra_5938.md`, seção 6). Isso também afeta a comparação do per capita entre esses anos. É inferência, decorrente do fato de o per capita usar a estimativa do mesmo ano.

---

## A2: soma do PIB nominal de SC em 2021

### Pergunta

Por que a soma do PIB nominal dos municípios de SC (5938, variável 37) sobe 22,70% em 2021, contra 2,69% a 13,23% nos demais anos? Há explicação oficial? O que mudou na revisão de 19/12/2025?

### O que foi encontrado

**1. Decomposição oficial em volume e preço (Contas Regionais, edição 2023).**
Fontes:
- https://ftp.ibge.gov.br/Contas_Regionais/2023/ods/Especiais_2010_2023_ods.zip: `tab01.ods` (PIB a valores correntes) e `tab03.ods` ("Série encadeada do volume do Produto Interno Bruto [...] base: 2010 = 100").

O valor corrente de SC na Tabela 1 é igual à soma municipal do relatório: 428.570,89 milhões de reais em 2021.

| Ano | SC nominal | SC volume | SC preço implícito | BR nominal | BR volume | BR preço implícito |
|---|---|---|---|---|---|---|
| 2019 | +8,40% | +3,79% | +4,43% | +5,50% | +1,22% | +4,22% |
| 2020 | +8,05% | −2,86% | +11,23% | +2,98% | −3,28% | +6,47% |
| **2021** | **+22,70%** | **+6,81%** | **+14,88%** | **+18,43%** | **+4,76%** | **+13,05%** |
| 2022 | +8,80% | +1,84% | +6,84% | +11,85% | +3,02% | +8,57% |

O preço implícito foi calculado pelo projeto como (1 + nominal) / (1 + volume) − 1. Os insumos (valor corrente e índice de volume) são oficiais. O volume do Brasil em 2021 (+4,76%) bate com o release oficial "PIB cresce 4,8% e totaliza R$ 9 trilhões em 2021" (ver item 4).

**2. Abertura por atividade em SC, 2021.**
Fonte: https://ftp.ibge.gov.br/Contas_Regionais/2023/ods/Conta_da_Producao_2010_2023_ods.zip, `Tabela26.ods` ("Conta de produção por atividade econômica – Santa Catarina"), bloco "Valor Adicionado Bruto". As colunas usadas foram índice de volume e índice de preço.

| Atividade (SC, 2021) | VAB nominal | Volume | Preço |
|---|---|---|---|
| Total das atividades | +20,14% | +6,25% | +13,07% |
| Indústrias de transformação | +31,03% | +8,37% | +20,91% |
| Comércio e reparação de veículos | +28,69% | +4,30% | +23,38% |
| Transporte, armazenagem e correio | +33,57% | +9,80% | +21,66% |
| Agropecuária | +20,77% | +0,55% | +20,11% |
| Outros serviços | +22,24% | +13,40% | +7,80% |
| Eletricidade e gás, água, esgoto... | −16,66% | +1,35% | −17,78% |

O nível do imposto é derivado (PIB − VAB): de 59.990 para 81.036 milhões de reais, +35%. Cálculo do projeto com os valores das Tabelas 1 (Especiais) e 26.1 (VAB). Isso explica por que o PIB (+22,70%) sobe mais que o VAB (+20,14%).

**3. A revisão de 19/12/2025 não mudou o total de SC em 2021.**
- A Tabela 1 das Especiais na edição de 2021 (https://ftp.ibge.gov.br/Contas_Regionais/2021/ods/Especiais_2010_2021_ods.zip, publicada em 17/11/2023) e na edição de 2023 (17/11/2025) traz **o mesmo valor** de SC em 2021: 428.570,88874870387 milhões. O índice de volume de 2021 também é o mesmo (121,568...).
- Base municipal da edição de 2021 (https://ftp.ibge.gov.br/Pib_Municipios/2021/base/base_de_dados_2010_2021_txt.zip, de 19/12/2023) comparada com a SIDRA 5938 atual (URL R7): a soma de SC em 2021 é a mesma (428.570.889 mil reais), mas **os 295 municípios tiveram o valor alterado**. A variação relativa vai de −1,38% (Xanxerê) a +0,55% (Nova Erechim), com média absoluta de 0,04%: 287 subiram e 8 caíram. Em 2020, os 295 valores são iguais aos da SIDRA (diferença ≤ 0,5 mil reais).
- O layout da edição de 2021 já avisava: "1. Os dados de 2021 estarão sujeitos a revisão na próxima publicação." (PDF dentro do zip acima.)
- **Conclusão sobre a revisão:** ela redistribuiu o PIB de 2021 entre os municípios e manteve o total da UF. Isso responde, para SC, à pendência "o que mudou em 2021" de `sidra_5938.md`. O motivo metodológico da redistribuição continua **NÃO CONFIRMADO**.

**4. Textos de divulgação (só título e lide; texto integral bloqueado).**
API de Notícias: `https://servicodados.ibge.gov.br/api/v3/noticias/?busca=pib&de=11-01-2023&ate=12-31-2023&qtd=40`.
- 17/11/2023, "Em 2021, PIB cresce em todas as 27 unidades da federação" (Contas Regionais 2021). Lide: "A Agropecuária, principalmente o cultivo de soja, contribuiu para o resultado de 2021 dos estados de maior expansão: Rio Grande do Sul (9,3%), Tocantins (9,2%), Roraima (8,4%)." Os números do lide são de volume. O lide não cita SC.
- 15/12/2023, "PIB dos municípios mostra que economia do país continuou a se desconcentrar em 2021". O lide não cita SC.
- 08/11/2023 (release), "PIB cresce 4,8% e totaliza R$ 9 trilhões em 2021".
- O texto integral (agenciadenoticias.ibge.gov.br) devolveu 403 (Cloudflare). **Não li nenhuma explicação textual oficial específica para SC.**

### Conclusão: **PARCIAL**

- **Confirmado com dados oficiais:** o salto nominal de 2021 em SC combina volume de +6,81% com preço implícito de +14,88%, o maior componente de preço da série desde 2010. Há fortes altas de preço na indústria de transformação, no comércio, no transporte e na agropecuária. O Brasil teve o mesmo padrão (+18,43% nominal). A revisão de 19/12/2025 não alterou o total de SC em 2021.
- **NÃO CONFIRMADO:** a explicação textual do IBGE para SC (por exemplo, quais produtos ou preços). Atribuir o salto a "commodities" ou "inflação de 2021" é **hipótese**: os índices de preço por atividade são compatíveis com isso, mas nenhum texto oficial lido o afirma para SC.

### Implicação para o D27 (limitações)

- Registrar que a variação nominal de 2021 inclui forte efeito de preços. Pelas Contas Regionais, o volume de SC cresceu 6,81%. Nunca descrever os 22,70% como crescimento econômico (regra 3).
- Registrar que os valores municipais de 2021 foram revisados em 19/12/2025 (|Δ| até 1,38%) com total estadual inalterado. Coletas anteriores a essa data têm 2021 diferente.
- Os dados de 2022 e 2023 também estão "sujeitos a revisão" (`sidra_5938.md`, seção 7).

---

## A1: variações anuais de PIB nominal municipal acima de 50%

### Pergunta

Há nota metodológica sobre volatilidade em municípios pequenos? Lajeado Grande (4209458, +215,2% em 2012) tem atividade, como usina hidrelétrica, que explique o salto?

### O que foi encontrado

**1. A nota metodológica do PIB dos Municípios, Referência 2010, descreve o mecanismo de distribuição.**
Fonte: https://ftp.ibge.gov.br/Pib_Municipios/Notas_Metodologicas_2010/NotaMetodologicaPIB_MunicipiosRef2010.pdf

> "No que se refere ao cálculo do PIB dos Municípios, este se baseia na distribuição, entre os municípios, do valor adicionado bruto – a preços básicos –, em valores correntes das atividades econômicas, obtido pelas Contas Regionais do Brasil. O trabalho fundamenta-se na identificação de variáveis que permitam distribuir o valor adicionado bruto das atividades econômicas de cada Unidade da Federação entre seus respectivos municípios."

> "O valor adicionado bruto das atividades industriais concentradas no território da Unidade da Federação passa a ser alocado nos municípios com a presença da referida atividade industrial."

> "Revisão da alocação do valor adicionado da atividade Geração de Energia Elétrica, observando o aspecto conceitual da localização da casa de força das usinas hidrelétricas."

Anexo (indicadores de distribuição): a indústria de transformação usa "Valor das saídas de mercadorias" da **SEFAZ**. Partes de transporte de carga, armazenagem e atividades profissionais usam como indicador o "Valor adicionado municipal das atividades [...] indústria de transformação [...]" do próprio PIB dos Municípios. **Assim, um salto na indústria de transformação de um município se propaga para os serviços dele.**

A nota **não** fala em "volatilidade" de municípios pequenos. Não encontrei nenhum texto oficial que trate disso diretamente: **NÃO CONFIRMADO**.

**2. A base oficial mostra de onde vêm os saltos.**
Fonte: base da edição de 2021 (https://ftp.ibge.gov.br/Pib_Municipios/2021/base/base_de_dados_2010_2021_txt.zip), com VAB por setor e as 3 atividades de maior VAB. Para 2010–2020, os valores de PIB de SC são iguais aos da SIDRA atual (URL R6, 2020 conferido). Classificando os 56 casos de |variação| > 50% entre 2011 e 2021 pelo componente de maior variação absoluta: **indústria em 30, serviços (exceto adm. pública) em 17, agropecuária em 9**. Os outros 5 dos 61 casos (2022–2023) não têm abertura setorial.

**Lajeado Grande (4209458), mil reais correntes, base oficial:**

| Ano | Agro | Indústria | Serviços exc. adm. | Adm. pública | PIB | 1ª atividade | 2ª atividade | 3ª atividade |
|---|---|---|---|---|---|---|---|---|
| 2011 | 12.060 | 1.838 | 3.778 | 7.042 | 25.539 | Adm. pública | Pecuária | Agricultura |
| 2012 | 9.530 | **23.838** | **28.629** | 7.804 | 80.509 | Demais serviços | **Indústrias de transformação** | Adm. pública |
| 2013 | 14.706 | 25.153 | 31.078 | 8.495 | 91.100 | Demais serviços | Indústrias de transformação | Pecuária |
| 2014 | 15.384 | 8.450 | 7.332 | 8.640 | 41.947 | Pecuária | Adm. pública | Indústrias de transformação |
| 2015 | 15.548 | 1.789 | 7.086 | 9.567 | 35.116 | Adm. pública | Pecuária | Demais serviços |

- O salto de 2012 vem da indústria (cerca de +22 mil) e dos serviços (cerca de +25 mil), com a **indústria de transformação** como 2ª maior atividade. "Eletricidade e gás, água, esgoto..." é uma categoria própria na lista de maiores atividades (nota 3 do layout) e **não aparece entre as 3 maiores** em 2012–2013. Os dados oficiais, portanto, **não apoiam** a hipótese de usina hidrelétrica como causa. Pela base, o bloco é de indústria de transformação.
- O mesmo padrão (indústria e serviços de cerca de 20–25 mil cada, que surgem e somem em 1 a 3 anos) aparece em vários municípios pequenos do Oeste de SC, em anos diferentes. Exemplos: Entre Rios e Paial em 2011–2013; Saltinho e São Bernardino em 2010 e 2012; Águas Frias em 2012–2013; Bom Jesus do Oeste e União do Oeste em 2010–2013, com queda em 2014; Lajeado Grande em 2012–2013. Em todos, "Indústrias de transformação" entra no top 3 nesses anos e sai depois.
- **Hipótese (NÃO CONFIRMADA):** um ou mais estabelecimentos industriais, ou registros de saídas de mercadorias na SEFAZ, mudaram de município de registro, o que deslocou o VAB de transformação e, pelos indicadores derivados, também o de serviços. Nenhum documento oficial lido trata desses municípios.
- Casos de grande porte em que a indústria domina a variação: São Francisco do Sul em 2021 (indústria +1,66 bi; serviços +1,17 bi), Capivari de Baixo em 2018 (indústria +416 mi) e Araquari em 2015 (indústria +596 mi). As causas desses casos **não foram pesquisadas**.

**3. Nada do que foi encontrado sugere erro de carga.** O relatório já mostrou coerência com o per capita (seção 4.1), e os valores da SIDRA batem com a base oficial.

### Conclusão: **PARCIAL**

- **Confirmado:** o mecanismo oficial que torna o PIB de municípios pequenos sensível a deslocamentos de atividade (distribuição do VAB estadual por indicadores; indústria de transformação pela SEFAZ; serviços derivados da indústria). Também está confirmado, na base oficial, qual setor puxou cada salto.
- **NÃO CONFIRMADO:** a causa econômica concreta em Lajeado Grande, e se ele tem usina hidrelétrica. A base oficial não aponta eletricidade entre as maiores atividades em 2012–2013. Também não encontrei texto oficial sobre "volatilidade de municípios pequenos".

### Implicação para o D27 (limitações)

- Documentar que o PIB municipal é uma **distribuição** do PIB estadual por indicadores administrativos (SEFAZ, ANEEL, CEMPRE etc.), e não uma medição direta. Em municípios pequenos, a entrada ou saída de um único estabelecimento pode multiplicar ou dividir o PIB de um ano para outro.
- Recomendar cautela com variações municipais e com rankings de crescimento nominal. Para municípios pequenos, preferir médias de vários anos ou mostrar a série inteira.
- Sugestão (decisão da autora): o T17 continua só como ALERTA, e a lista de 61 casos fica como "conhecidos", com o setor dominante de cada um.

---

## Fontes consultadas

### Lidas com sucesso

| # | URL | O que forneceu |
|---|---|---|
| R1 | https://biblioteca.ibge.gov.br/visualizacao/livros/liv97742.pdf | Nota metodológica das estimativas 2013 (A3) |
| R2 | https://ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2013/nota_metodologica_2013.pdf | Nota da Projeção 2013 (A3) |
| R2b | https://ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2013/srm40_projecao_da_populacao.pdf | Relatório metodológico 40, Projeção 2013 (A3) |
| R2c | https://ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2013/projecoes_2013_populacao_ods.zip | Projeção 2013 de SC por ano (A3) |
| R3 | https://apisidra.ibge.gov.br/values/t/6579/n3/42/v/9324/p/2011-2015, `.../p/2015-2021` e `.../t/6579/n1/all/v/9324/p/2011-2014` | Estimativas de SC e do Brasil (A3) |
| R4 | https://apisidra.ibge.gov.br/values/t/6579/n6/in%20n3%2042/v/9324/p/2011, `/p/2012` e `/p/2013` | Soma municipal por ano (A3, achado 6) |
| R5 | https://apisidra.ibge.gov.br/values/t/1378/n3/42/v/93/p/2010/c1/0/c2/0/c287/0/c455/0 | Censo 2010 de SC: 6.248.436 (A3) |
| R6 | https://apisidra.ibge.gov.br/values/t/5938/n6/in%20n3%2042/v/37/p/2020 | Conferência da base de 2020 (A1) |
| R7 | https://apisidra.ibge.gov.br/values/t/5938/n6/in%20n3%2042/v/37/p/2021 | PIB municipal 2021 atual (A2) |
| R8 | https://servicodados.ibge.gov.br/api/v2/metadados/pesquisas e `.../api/v2/metadados/XF/{2011,2012,2013,2014,2017,2018,2019,2021}/0` | Metadados das estimativas: comparabilidade e links de metodologia (A3) |
| R9 | https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2013/serie_2001_2013_TCU.pdf (e a de 2012) | Nota técnica da série TCU (A3) |
| R10 | https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2013/estimativa_2013_dou.pdf e retificacao_estimativa_2013_dou.pdf | Sem nota metodológica; só a nota de decisão judicial e retificações de arredondamento (A3) |
| R11 | https://biblioteca.ibge.gov.br/visualizacao/livros/liv101609.pdf | Estimativas 2018: Revisão 2018 da projeção (A3) |
| R12 | https://ftp.ibge.gov.br/Contas_Regionais/2023/ods/Especiais_2010_2023_ods.zip | PIB corrente e volume por UF (A2) |
| R13 | https://ftp.ibge.gov.br/Contas_Regionais/2021/ods/Especiais_2010_2021_ods.zip | Mesmo dado na edição de 2021, para comparar com a revisão (A2) |
| R14 | https://ftp.ibge.gov.br/Contas_Regionais/2023/ods/Conta_da_Producao_2010_2023_ods.zip | Conta de produção de SC por atividade (A2) |
| R15 | https://ftp.ibge.gov.br/Pib_Municipios/2021/base/base_de_dados_2010_2021_txt.zip | Base municipal da edição de 2021, com setores e maiores atividades (A1, A2) |
| R16 | https://ftp.ibge.gov.br/Pib_Municipios/Notas_Metodologicas_2010/NotaMetodologicaPIB_MunicipiosRef2010.pdf | Mecanismo de distribuição do PIB municipal (A1) |
| R17 | https://servicodados.ibge.gov.br/api/v3/noticias/?busca=pib&de=11-01-2023&ate=12-31-2023&qtd=40 e `...&de=12-01-2025&ate=12-31-2025...` | Títulos e lides das divulgações (A2) |

### Falharam ou não foram lidas

| URL | Resultado |
|---|---|
| https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-populacao.html?=&t=notas-tecnicas | 403 (Cloudflare, `Cf-Mitigated: challenge`), via WebFetch e curl |
| https://agenciadenoticias.ibge.gov.br/ (raiz e release 38712, Contas Regionais 2021) | 403 (Cloudflare). Texto integral das notícias não lido |
| https://apisidra.ibge.gov.br/desctabapi.aspx?c=6579 e `?c=5938` | 403. Notas das tabelas no SIDRA não lidas |
| https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2014/nota_metodologica_2014.pdf (link da API de Metadados para 2014) | 404 |
| API de Notícias com `busca` contendo espaço e acento ("PIB dos Municípios 2021") | "Request Rejected" (WAF). Com `busca=pib` e filtro de datas, funcionou |
| API de Notícias, `busca=estimativas`, agosto–setembro de 2013 | 0 resultados |
| Páginas de metodologia de 2011 e 2012 (`www.ibge.gov.br/home/estatistica/populacao/estimativa2011/` e `estimativa2012/`, indicadas pelos metadados) | Não testadas: domínio atrás de Cloudflare (ver primeira linha) |
| Pastas `Pib_Municipios/2021/` e `2022_2023/` do FTP | Sem publicação ou release em PDF, só bases e tabelas |
| Pastas `Contas_Regionais/2021/` e `2023/` do FTP | Sem publicação em PDF, só tabelas |

## Pendências

- Ler, pelo navegador, o texto integral das notícias de 17/11/2023 (Contas Regionais 2021) e 15/12/2023 (PIB dos Municípios 2021), em busca de menção a SC.
- Ler a metodologia das estimativas de 2011 e 2012 (portal antigo) para confirmar qual projeção e qual total de UF foram usados.
- Investigar a diferença de 20.552 pessoas entre a soma municipal e o N3 de SC em 2012 (achado 6 do A3), junto com O3 e O4 do relatório.
- Lajeado Grande e o bloco industrial do Oeste: consultar fonte oficial de geração de energia (ANEEL) e o Cadastro Central de Empresas (CEMPRE/SIDRA) por município, se a autora quiser fechar a causa. Isso foge do escopo IBGE-only deste levantamento.
