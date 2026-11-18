# Limitações dos dados

- **Versão:** 2026-11-18 (cartão D27)
- **Vale para:** a camada SILVER carregada em 2026-11-18 e as camadas que vierem dela (GOLD, EDA, dashboards).
- **Base:** CLAUDE.md (regras 1–13), `docs/decisoes.md` (D01–D26), `docs/dicionario_dados.md`, `docs/fontes/` e o relatório de qualidade `reports/qualidade_20261118.md` (não versionado; os números citados dele estão reproduzidos aqui).

Cada seção traz: o que é, a evidência, o impacto na análise e o que o projeto faz a respeito. O que não tem fonte está marcado como **NÃO CONFIRMADO**.

## Resumo

| # | Limitação | Indicador | Tratamento no projeto |
|---|---|---|---|
| 1 | Quebras de série nas estimativas (2013 e 2018) | `pop_estimada` | Regra 12: sem variação entre ≤2012 e ≥2013 sem aviso |
| 2 | Dupla contagem na soma de 2012 | `pop_estimada` | Regra 13: excluir 2 municípios ou avisar (escolha no D30); teste T16 |
| 3 | Censo e estimativa não se comparam diretamente | `pop_censo`, `pop_estimada` | Regra 2: `tipo_medida` separa os dois |
| 4 | Sem estimativa em 2010, 2022 e 2023 | `pop_estimada` | Ausência fica ausente; sem interpolação (regra 5) |
| 5 | PIB nominal e sujeito a revisão | `pib_corrente` | Regra 3; RAW guarda cada versão |
| 6 | PIB municipal é distribuição do PIB estadual | `pib_corrente` | Valor publicado, sem ajuste; cautela com variações |
| 7 | Setores sem abertura em 2022–2023 | extensão | Fora do MVP (D10) |
| 8 | Censo 2022: 1ª × 2ª apuração | `pop_censo`, `pib_per_capita` | Documentado; diferença NÃO CONFIRMADA |
| 9 | Per capita com denominador diferente por ano | `pib_per_capita` | Valor publicado, sem recálculo (regra 4) |
| 10 | Municípios instalados em 2013 e recorte vigente | todos | Ausência esperada (regras 6 e 10) |
| 11 | Documentação de origem não lida | todos | Itens listados como NÃO CONFIRMADO |

---

## 1. Quebras de série na estimativa de população (2013 e 2018)

**O que é.** A partir de 2013, as estimativas municipais da tabela 6579 passaram a usar a nova Projeção da População por UF (método das componentes) e os Censos 2000 e 2010 ajustados por um fator de cobertura. As de 2011 e 2012 usavam a base anterior. O IBGE declara comparáveis só as estimativas de 2013 a 2017. Em 2018 houve outra revisão da projeção.

**Evidência.**
- `docs/fontes/alertas_qualidade_2026-11.md`, alerta A3 (conclusão: CONFIRMADO).
- Nota das estimativas de 2013: https://biblioteca.ibge.gov.br/visualizacao/livros/liv97742.pdf
- Metadados da pesquisa (campo `longitude_series_temporais_comparaveis`): `https://servicodados.ibge.gov.br/api/v2/metadados/XF/{ano}/0`
- Estimativas de 2018: https://biblioteca.ibge.gov.br/visualizacao/livros/liv101609.pdf
- Números da auditoria (`reports/qualidade_20261118.md`, seção 5.1):

| Medida | 2012 → 2013 | Outros anos |
|---|---|---|
| Variação média por município | +2,55% | +0,12% a +0,55% |
| Variação da soma municipal | +3,93% | +1,05% a +1,40% |

- Na nova projeção, SC em 2012 já fica 2,80% acima da estimativa publicada para 2012; o crescimento de 2012 para 2013 pela própria projeção é de 1,43% (A3, item 5).
- Em 2018, a variação estadual foi de +1,06%, sem salto visível em SC (A3, item 7).

**Impacto.**
- A variação de 2012 para 2013 é sobretudo mudança de base, não crescimento populacional.
- Pelo metadado oficial, comparações fora de 2013–2017 pedem cautela, inclusive entre 2017 e 2018.
- O PIB per capita de 2011–2012 usa estimativas da base antiga, e o de 2013 em diante, da nova. A comparação do per capita entre esses anos herda a quebra. Isso é inferência (A3, "Implicação para o D27").

**O que o projeto faz.**
- Regra 12 (D26): a GOLD não calcula nem exibe variação de `pop_estimada` entre anos de bases diferentes (≤2012 contra ≥2013) sem aviso explícito, e a série vem com a quebra marcada. A GOLD ainda não existe (D30).
- A revisão de 2018 fica documentada aqui, sem regra própria (D26).
- Por que o salto médio municipal é menor que o estadual: **NÃO CONFIRMADO** (A3, item 5).

## 2. Dupla contagem na soma de 2012

**O que é.** Em 2012, a soma dos 295 municípios na tabela 6579 é maior que o total publicado para SC. A diferença é exatamente a população de Pescaria Brava (4212650) e Balneário Rincão (4220000), que só foram instalados em 2013.

**Evidência.** `docs/fontes/alertas_qualidade_2026-11.md` (A3, achado 6) e `docs/dicionario_dados.md` (observações de `pop_estimada`).

| Item | Valor |
|---|---|
| Soma municipal de 2012 | 6.383.286 |
| Total de SC (N3) em 2012 | 6.362.734 |
| Diferença | 20.552 |
| 4212650 + 4220000 em 2012 | 9.416 + 11.136 = 20.552 |

Em 2011 e 2013, a soma municipal fecha com o total de SC.

**Impacto.** Somar 2012 sem cuidado conta essas 20.552 pessoas duas vezes. Uma hipótese é que Içara e Laguna, de onde os dois municípios foram desmembrados, ainda incluam essa população em 2012 (ver seção 9). A causa é **NÃO CONFIRMADA**.

**O que o projeto faz.**
- Regra 13 (D26): agregações de `pop_estimada` de 2012 (estado, região) excluem os dois municípios ou levam aviso. A escolha entre as duas opções fica para o D30.
- O teste `test_t16_dupla_contagem_2012_igual_a_populacao_dos_municipios_novos` confere que soma municipal − total de SC = população dos dois municípios. O total de SC vem do valor de referência `TOTAL_SC_6579_2012` do dicionário, porque não está no banco. Se uma revisão do IBGE mudar a diferença, o teste falha.

## 3. Censo e estimativa não são uma série única

**O que é.** O censo é uma contagem. A estimativa é calculada a partir de projeções. Além do método, as datas de referência são diferentes.

| Medida | Data de referência | Fonte |
|---|---|---|
| Estimativa (6579) | 1º de julho de cada ano | `docs/fontes/sidra_convencoes.md` (PDFs oficiais das estimativas) |
| Censo 2010 (1378) | noite de 31 de julho para 1º de agosto de 2010 | `docs/dicionario_dados.md`, nota ¹ |
| Censo 2022 (4709) | meia-noite de 31 de julho para 1º de agosto de 2022 | `docs/dicionario_dados.md`, nota ² |

**Evidência (observação da auditoria, não erro).** `reports/qualidade_20261118.md`, seção 4.3 e observação O6:

| Comparação | Municípios | Média | Mínimo | Máximo | Acima de 10% | Acima de 20% |
|---|---|---|---|---|---|---|
| Censo 2010 → estimativa 2011 | 293 | +0,47% | −1,67% | +4,23% | 0 | 0 |
| Estimativa 2021 → Censo 2022 | 295 | +4,82% | −19,34% | +79,56% (Guatambú) | 89 | 27 |

A causa das diferenças município a município não foi analisada.

**Impacto.** Ligar a estimativa de 2021 ao Censo 2022 numa linha só cria saltos que não são crescimento. A diferença entre os dois não mede erro da estimativa.

**O que o projeto faz.**
- Regra 2: o `tipo_medida` (`censo` ou `estimativa`) é atributo da `dim_indicador`, e cada linha da fato o herda pelo indicador.
- D01: a variação populacional oficial do projeto é Censo 2010 × Censo 2022. A estimativa entra só como série complementar.

## 4. Anos sem estimativa: 2010, 2022 e 2023

**O que é.** A tabela 6579 não tem estimativa municipal em 2010, 2022 e 2023. No recorte do projeto, ela cobre só 2011–2021.

**Evidência.** `docs/fontes/sidra_6579.md` (seção 3: consultas devolvem só o cabeçalho) e `docs/fontes/sidra_convencoes.md` (o FTP do IBGE também não tem publicações de 2007, 2010, 2022 e 2023). O motivo é **NÃO CONFIRMADO**: a hipótese de que 2010 e 2022 são anos de Censo não está escrita em nenhuma fonte lida, e 2023 não tem explicação.

**Impacto.** Não há série anual de população de 2010 a 2023 com um único método. Nesses três anos, só existe o censo (2010 e 2022) ou nada (2023).

**O que o projeto faz.**
- Não preenche os anos ausentes, não interpola e não usa o censo no lugar da estimativa (regras 2 e 5).
- O teste de cobertura confere só os anos que cada série publica (dicionário, seção 5; teste T5).

## 5. PIB nominal e sujeito a revisão

**O que é.**
- O PIB da tabela 5938 é a preços correntes. Variações entre anos incluem preço e volume.
- Os anos 2021, 2022 e 2023 foram modificados em 19/12/2025. Os de 2022 e 2023 estão "sujeitos a revisão na próxima publicação" (nota 1 do layout da base oficial).
- O SIDRA arredonda o PIB para inteiro em mil reais. A soma dos municípios difere do total de SC em até 8 mil reais.

**Evidência.** `docs/fontes/sidra_5938.md` (seções 3, 5 e 7) e `docs/fontes/alertas_qualidade_2026-11.md` (A2, conclusão PARCIAL).

**Salto nominal de 2021 (alerta A2).** A soma do PIB nominal de SC subiu 22,70% em 2021, contra 2,69% a 13,23% nos outros anos (relatório, seção 4.2). Pelas tabelas oficiais das Contas Regionais (https://ftp.ibge.gov.br/Contas_Regionais/2023/ods/Especiais_2010_2023_ods.zip):

| SC, 2021 | Variação |
|---|---|
| Nominal | +22,70% |
| Volume | +6,81% |
| Preço implícito (calculado pelo projeto a partir dos índices oficiais) | +14,88% |

O Brasil teve +18,43% nominal no mesmo ano. Nenhum texto oficial lido explica o caso de SC: atribuir o salto a preços de produtos específicos é hipótese, **NÃO CONFIRMADA**.

**Revisão de 19/12/2025.** Para 2021, a revisão manteve o total de SC e redistribuiu o valor entre os 295 municípios (variação de −1,38% a +0,55%; A2, item 3). O motivo metodológico é **NÃO CONFIRMADO**. Quando sairá a nova base 2021 das Contas Nacionais, e se ela muda a série, também é **NÃO CONFIRMADO** (`sidra_5938.md`, seção "Setores (D10)").

**Impacto.**
- Nenhuma variação do PIB deste projeto é crescimento econômico real. Os +22,70% de 2021 não significam que a economia de SC cresceu 22,70%.
- Valores de 2022 e 2023 podem mudar numa coleta futura. Coletas anteriores a 19/12/2025 teriam outro valor para 2021.

**O que o projeto faz.**
- Regra 3: o PIB é sempre descrito como nominal. Deflacionar ou calcular crescimento real está fora do MVP (`docs/escopo_mvp.md`).
- Cada coleta grava um arquivo novo na RAW (regra 7). Na carga, um valor revisado atualiza a linha da fato, troca a `data_coleta` e aparece no log com o valor antigo e o novo (D21).

## 6. PIB municipal é uma distribuição do PIB estadual

**O que é.** O IBGE não mede o PIB de cada município diretamente. Ele distribui o valor adicionado de cada atividade da UF entre os municípios por indicadores. A indústria de transformação usa o valor das saídas de mercadorias da SEFAZ, e parte dos serviços usa o próprio valor da indústria do município.

**Evidência.**
- `docs/fontes/alertas_qualidade_2026-11.md`, alerta A1 (conclusão PARCIAL).
- Nota metodológica do PIB dos Municípios, Referência 2010: https://ftp.ibge.gov.br/Pib_Municipios/Notas_Metodologicas_2010/NotaMetodologicaPIB_MunicipiosRef2010.pdf
- Auditoria (`reports/qualidade_20261118.md`, seção 5.2): 61 variações anuais de PIB nominal acima de 50% em módulo, em 51 municípios (55 altas e 6 quedas), 42 delas em 2011–2014. Máximo: +215,2% em Lajeado Grande (4209458), 2012.
- Na base oficial, dos 56 casos de 2011–2021, o maior componente da variação foi a indústria em 30, os serviços (exceto administração pública) em 17 e a agropecuária em 9 (A1, item 2).

**Impacto.** Em municípios pequenos, a entrada ou a saída de um estabelecimento (ou de um registro na SEFAZ) pode multiplicar ou dividir o PIB de um ano para outro. Rankings de variação nominal e variações de um único ano são frágeis nesses casos.

**O que o projeto faz.**
- Carrega o valor publicado, sem ajuste. Os valores são coerentes com o per capita publicado (seção "Validação" em `docs/metodologia.md`), então não há indício de erro de carga.
- Recomenda olhar a série inteira ou médias de vários anos em municípios pequenos.
- **NÃO CONFIRMADO:** a causa econômica de cada caso, a hipótese de mudança de município de registro na SEFAZ e a existência de usina hidrelétrica em Lajeado Grande (a base oficial não aponta eletricidade entre as 3 maiores atividades em 2012–2013).

## 7. Setores sem abertura em 2022–2023 (extensão)

**O que é.** O valor adicionado por setor e os impostos (tabela 5938, variáveis 498, 513, 517, 6575, 525 e 543) vêm com `...` para os 295 municípios em 2022 e 2023: 3.540 linhas. Nessas linhas, os campos de unidade (`MC`, `MN`) vêm vazios.

**Evidência.** `docs/fontes/sidra_5938.md`, seção "Setores (D10)", e a nota técnica 02/2024 do IBGE (https://biblioteca.ibge.gov.br/visualizacao/livros/liv102094.pdf): por causa da mudança do ano base das Contas Nacionais de 2010 para 2021, 2022 e 2023 foram publicados sem abertura por atividade.

**Impacto.** A pergunta derivada 5 do escopo (composição setorial) não tem resposta no MVP. Uma série setorial terminaria em 2021 e pode mudar de referência com a nova base.

**O que o projeto faz.** D10: setores ficam fora do MVP, como extensão. Os nomes propostos estão no dicionário, seção 2. Se a extensão entrar, ela precisa de uma regra de cobertura própria, porque os `...` de 2022–2023 conflitam com a regra 10.

## 8. Censo 2022: 1ª e 2ª apuração

**O que é.** O IBGE publicou os primeiros resultados de população do Censo 2022 em 28/06/2023 (1ª apuração) e os republicou em 27/10/2023 e 22/12/2023 (2ª apuração). A tabela 4709 foi modificada em 22/12/2023. O PIB per capita de 2022 usa a 1ª apuração como denominador.

**Evidência.** `docs/fontes/sidra_4709.md` (seções 3 e 9) e `docs/fontes/ibge_pesquisas_pib_per_capita.md` (seção 4).
- Que a 4709 traga a 2ª apuração é inferência forte (datas e valores coincidem com o PDF de 22/12/2023), não leitura direta.
- Na auditoria, 271 de 295 municípios reproduzem o per capita de 2022 com a 4709; 9 diferem em mais de 0,1%, com máximo de 2,96% em Ipuaçu (relatório, observação O5).

**Impacto.** A população do Censo 2022 no banco pode não ser a mesma usada pelo IBGE no per capita de 2022. Dividir o PIB de 2022 pela `pop_censo` de 2022 não reproduz o per capita oficial em todos os municípios.

**O que o projeto faz.** Usa a 4709 como está e não recalcula o per capita (regra 4). O ano de 2022 fica fora da validação PIB/população (D10).

**NÃO CONFIRMADO:** o que mudou entre as apurações, se municípios de SC foram afetados e os valores da 1ª apuração.

## 9. PIB per capita: denominador muda conforme o ano

**O que é.** O per capita oficial (API de Pesquisas, pesquisa 38, indicador 47001) é o PIB dividido por uma população que muda de fonte conforme o ano. Ele não é renda: é o valor da produção do município dividido pelos moradores.

| Anos | População usada pelo IBGE (nota 3 do layout da base oficial) | Reproduzível com as tabelas do projeto |
|---|---|---|
| 2010 | Estimativa TCU de 1º de julho de 2010 | Não. A 6579 não tem 2010; o Censo 2010 reproduz 113 de 293 |
| 2011–2021 | Estimativa TCU de 1º de julho de cada ano | Sim, com a 6579, exceto Içara e Laguna em 2012 |
| 2022 | 1ª apuração do Censo 2022 | 271 de 295 com a 4709 (seção 8) |
| 2023 | Relação da população enviada ao TCU em 2023 | Sim, com a 4709 (295 de 295) |

**Evidência.** `docs/fontes/ibge_pesquisas_pib_per_capita.md` (seção 4) e base oficial https://ftp.ibge.gov.br/Pib_Municipios/2022_2023/base/base_de_dados_2010_2023_txt.zip.

**Içara e Laguna em 2012.** PIB / estimativa de 2012 difere do per capita publicado em +22,62% (Içara, 4207007) e +22,03% (Laguna, 4209409). A população implícita no per capita é igual à soma da estimativa do município com a de um dos municípios instalados em 2013 (49.238 + 11.136 = 60.374; 42.750 + 9.416 = 52.166). A explicação (população desmembrada incluída) é **NÃO CONFIRMADA**; a associação de cada município novo foi feita só pela coincidência numérica (relatório, O3 e O4).

**Impacto.**
- Comparar o per capita entre anos mistura denominadores diferentes, inclusive a quebra de 2013 (seção 1) e a troca de estimativa por censo em 2022.
- Dividir o `pib_corrente` por `pop_estimada` ou `pop_censo` do banco não reproduz o per capita oficial em 2010, em parte de 2022 e em Içara e Laguna em 2012.
- Ler o per capita como renda média dos moradores é erro de interpretação.

**O que o projeto faz.**
- Regra 4: o per capita é o valor publicado, sem recálculo, e nunca é tratado como renda.
- A validação PIB/população ≈ per capita exclui 2010, 2022 e Içara e Laguna em 2012 (D10).

## 10. Municípios instalados em 2013 e recorte territorial vigente

**O que é.** Pescaria Brava (4212650) e Balneário Rincão (4220000) foram instalados em 1º/01/2013. O projeto usa o cadastro atual da API de Localidades: 295 municípios em todos os anos de 2010 a 2023.

**Evidência.**
- Data de instalação: nota "(3) Municípios instalados em 1º de janeiro de 2013" do PDF oficial das estimativas de 2012 (https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2012/estimativa_2012_TCU_20170614.pdf). A associação da nota aos dois municípios é inferência forte, pela coincidência dos valores 9.416 e 11.136; a página do PDF não foi conferida visualmente (`docs/fontes/sidra_convencoes.md`).
- Ausências na SILVER (`reports/qualidade_20261118.md`, seções 2.1 e 2.2):

| Série | Anos | Como aparece |
|---|---|---|
| `sidra_1378_v93` (Censo 2010) | 2010 | Sem linha (a consulta por UF não devolve os dois; D08) |
| `sidra_6579_v9324` | 2011 | `NULL`, sinal `...` (2 linhas) |
| `sidra_5938_v37` | 2010–2012 | `NULL`, sinal `...` (6 linhas) |
| `pesquisas_38_i47001` | 2010–2012 | `NULL`, sinal `-` (6 linhas) |

Os dois têm estimativa em 2012 e valores em todas as séries a partir de 2013.

**Impacto.**
- Somas estaduais antes de 2013 têm 293 municípios com valor no PIB (2010–2012), no Censo 2010 e na estimativa de 2011. Na estimativa de 2012, os 295 têm valor (seção 2).
- Os valores de Içara e Laguna antes de 2013 podem incluir o território que deu origem aos municípios novos (seções 2 e 9). Isso é **NÃO CONFIRMADO**.
- Que a API de Localidades não versione o recorte por data é inferência (dicionário, seção 3).

**O que o projeto faz.**
- Regras 6 e 10: ausência só é aceita para esses dois códigos antes de 2013; qualquer outra faz o teste falhar (testes T5 e T6).
- Ausência é `NULL`, nunca zero, e o sinal original fica em `sinal_origem` (regras 5 e 9).
- Não recompõe a série dos municípios novos com dados do município de origem (fora de escopo, `docs/escopo_mvp.md`).
- A grade completa município × ano, com "sem dado", será montada na GOLD (D08; planejado para o D30).

## 11. Documentação de origem não lida

Algumas fontes oficiais não puderam ser lidas. Os itens abaixo seguem como **NÃO CONFIRMADO** (`docs/dicionario_dados.md`, seção 7, e `docs/fontes/`):

- **Notas das tabelas no SIDRA web** (6579, 1378, 4709 e 5938): carregadas por JavaScript, atrás de Cloudflare.
- **Documentação da API de Pesquisas:** a sintaxe `N6[N3[42]]` foi validada só na prática, e o significado oficial de `-` nessa API não foi lido. O projeto o trata como ausência (D09).
- **Revisão de 2017–2020 da 6579** (modificação em 05/09/2022): motivo não lido.
- **Populações judiciais:** se o SIDRA publica o valor técnico ou o judicial; nenhuma nota de SC foi encontrada em 2012, 2013 e 2021.
- **Divisão regional:** o ano de 2017 da divisão em regiões imediatas e intermediárias.
- **Textos de divulgação do IBGE sobre SC em 2021** (Agência de Notícias): bloqueados (403).
