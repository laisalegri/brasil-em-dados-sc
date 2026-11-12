# Convenções do SIDRA: símbolos especiais e notas da tabela 6579

- **Data da consulta:** 2026-11-12

## URLs consultadas

| # | URL | Resultado |
|---|-----|-----------|
| A | https://sidra.ibge.gov.br/tabela/6579 | HTML acessível por curl e WebFetch. Contém o modal estático "Símbolos especiais" (`div id="modal-simbolos-especiais"`). As notas da tabela (`div id="notas-tabela"`) chegam **vazias** no HTML, porque são preenchidas por JavaScript. |
| B | https://sidra.ibge.gov.br/Ajax/JSon/Tabela/1/6579?versao=-1 | Endpoint que o script `/Scripts/editor-tabela.js` usa para carregar a tabela, inclusive as notas. Retornou uma página de desafio Cloudflare ("Just a moment..."), sem dados. |
| C | https://apisidra.ibge.gov.br/home/ajuda | Página de desafio Cloudflare, sem conteúdo. |
| D | https://apisidra.ibge.gov.br/desctabapi.aspx?c=6579 | Página de desafio Cloudflare, sem conteúdo. |
| E | https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-populacao.html | HTTP 403, tanto por WebFetch quanto por curl. |
| F | https://servicodados.ibge.gov.br/api/v3/agregados/6579/metadados | Sem campo de notas. Já registrado em `sidra_6579.md`. |
| G | https://ftp.ibge.gov.br/Estimativas_de_Populacao/ | Listagem oficial das publicações por ano. |
| H | https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2012/estimativa_2012_TCU_20170614.pdf | PDF oficial de 2012. Texto extraído com `pdftotext`. |
| I | https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2013/estimativa_2013_TCU_20170614.pdf | PDF oficial de 2013. |
| J | https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2021/POP2021_20240624.pdf | PDF oficial de 2021. |

Não tentei contornar os desafios Cloudflare. As páginas B, C e D exigem um navegador e não foram lidas.

## Símbolos especiais do SIDRA (fonte: A, modal "Símbolos especiais")

| Sinal | Significado oficial (citação literal de A) | Como carregar no pipeline (sugestão) |
|-------|--------------------------------------------|--------------------------------------|
| `-` | "Zero absoluto, não resultante de um cálculo ou arredondamento." | Carregar como valor **0**, porque é um zero verdadeiro e não ausência. Registrar o sinal original (`-`) numa coluna de observação, para mostrar que o zero veio do símbolo. |
| `0` | "Zero resultante de um cálculo ou arredondamento." | Carregar como valor **0**, porque é numérico e foi publicado assim. Se útil, marcar "zero arredondado" na coluna de observação. |
| `X` | "Valor inibido para não identificar o informante." | **NULL**, com o sinal `X` na coluna de observação. Nunca carregar como zero. |
| `..` | "Valor não se aplica." | **NULL**, com o sinal `..` na coluna de observação. |
| `...` | "Valor não disponível." O exemplo oficial cita: "determinado município não existia no ano da pesquisa." | **NULL**, com o sinal `...` na coluna de observação. Não interpolar. |
| `A` a `Z` (exceto `X`) | "Significa uma faixa de valores. Varia em função da tabela (se for o caso)." | **NULL** no valor numérico, com a letra na coluna de observação. Não ocorre na 6579 para SC em 2011–2021. |

**Observações:**

- A distinção entre `-` (zero absoluto) e `0` (zero arredondado) é oficial. Os dois são valores e não ausência. A regra "ausência é NULL" vale para `X`, `..`, `...` e as letras.
- A coluna de observação (por exemplo, `sinal_original` ou `flag_valor`) é apenas uma sugestão. A decisão de modelagem é da autora e deve ir para `docs/decisoes.md`.
- Na tabela 6579 (SC, 2011–2021), o único sinal encontrado foi `...`, em 2 linhas: Pescaria Brava (4212650) e Balneário Rincão (4220000), ambas em 2011. Ver `sidra_6579.md`.

## Notas metodológicas da tabela 6579

As notas da página SIDRA não foram lidas, porque dependem de JavaScript e de um endpoint bloqueado por Cloudflare (A, B). Usei como substituto os PDFs oficiais das estimativas no FTP do IBGE (G a J). Eles são a publicação de origem, mas **não são a nota da tabela 6579 em si**.

### Data de referência

O título dos PDFs H, I e J diz "ESTIMATIVAS DA POPULAÇÃO RESIDENTE NO BRASIL E UNIDADES DA FEDERAÇÃO COM DATA DE REFERÊNCIA EM 1º DE JULHO DE {ano}", para 2012, 2013 e 2021. Portanto a estimativa se refere a **1º de julho** de cada ano, e não a 31 de dezembro nem à data do Censo.

### Municípios instalados em 2013

No PDF de 2012 (H), a nota (3) diz literalmente: "(3) Municípios instalados em 1º de janeiro de 2013."

No texto extraído, a marca "(3)" aparece junto aos valores 9.416 e 11.136. São exatamente os valores de 2012 que o SIDRA 6579 devolve para Pescaria Brava (4212650) e Balneário Rincão (4220000).

### Anos sem estimativa

A listagem do FTP (G) tem pastas `Estimativas_2001` a `Estimativas_2026`, mas **sem 2007, 2010, 2022 e 2023**. São as mesmas lacunas da tabela 6579 (ver `sidra_6579.md`). Nenhuma das fontes lidas explica o motivo.

### Revisões

- O PDF de 2012 e o de 2013 têm o sufixo `_20170614`.
- O FTP de 2013 tem um arquivo `retificacao_estimativa_2013_dou.pdf` (não lido).
- O PDF de 2021 tem o sufixo `_20240624`, que coincide com a data de modificação do período 2021 na API de Agregados (24/06/2024).
- O FTP de 2024 tem duas versões (`POP2024_20241101` e `POP2024_20241230`).

Isso indica republicações com data. Os motivos não foram lidos.

### Populações judiciais

Os PDFs de 2012, 2013 e 2021 têm notas de "População judicial" ou "determinação judicial... para efeito de distribuição do Fundo de Participação dos Municípios". O PDF de 2021 tem 30 menções a "Processo". Nenhuma das notas encontradas cita municípios de SC.

**NÃO CONFIRMADO:** se o SIDRA 6579 publica a estimativa técnica ou o valor judicial nesses casos.

### Limites interestaduais (2021)

O PDF de 2021 (J), notas (1) a (4) do quadro de UFs, registra diferenças em relação à Projeção da População 2021 "em virtude de alteração de limites entre municípios na fronteira interestadual". Os casos são PI/CE, AL/PE, SE/BA e GO/DF. Nenhum envolve SC.

## Verificado diretamente

- O texto literal dos 6 símbolos especiais está no HTML de https://sidra.ibge.gov.br/tabela/6579 (A). O WebFetch da mesma URL devolveu os mesmos textos.
- As notas da tabela chegam vazias no HTML (A). O endpoint de notas (B) e as páginas C e D estão atrás de Cloudflare, e a página E retornou 403.
- A data de referência de 1º de julho está no título dos PDFs de 2012, 2013 e 2021 (H, I, J).
- A nota "(3) Municípios instalados em 1º de janeiro de 2013." está no PDF de 2012 (H), e a marca (3) aparece junto aos valores 9.416 e 11.136.
- O FTP não tem pastas de 2007, 2010, 2022 e 2023 (G).
- Os sufixos de data dos arquivos estão listados na seção "Revisões" acima (G).

## Inferido / não confirmado

- **Instalação de Pescaria Brava e Balneário Rincão.** Que a nota (3) do PDF de 2012 se refira a esses dois municípios é inferência forte, mas não leitura direta da tabela do PDF. A extração de texto perde o layout, e a associação vem da coincidência exata dos valores (9.416 e 11.136) com o SIDRA 6579 de 2012. Uma confirmação definitiva exigiria ler a página do PDF renderizada ou outra fonte oficial (por exemplo, a lei estadual de criação).
- **Significado de `...` em 2011 para esses municípios.** É compatível com a definição oficial ("Valor não disponível"; "município não existia no ano da pesquisa"). A tabela 6579 não traz nota específica confirmando isso.
- **Estimativa em 2012 para municípios instalados em 2013.** A nota (3) sugere que o IBGE publicou a estimativa de 2012 já para os municípios a serem instalados em 1º/01/2013. É uma interpretação.
- **Motivo das lacunas.** O motivo de 2010, 2022 e 2023 faltarem continua **NÃO CONFIRMADO**. A hipótese é que 2010 e 2022 são anos de Censo, mas nenhuma fonte lida diz isso. Para 2023 também não há explicação.
- **Motivo das republicações.** O que mudou nas republicações de 2017 e 2024, e na revisão de 2017–2020 sugerida pela data 05/09/2022, é **NÃO CONFIRMADO**.
- **Populações judiciais no SIDRA.** Se o SIDRA usa o valor judicial é **NÃO CONFIRMADO**.

## Pendências

- Ler as notas da tabela 6579 num navegador, em https://sidra.ibge.gov.br/tabela/6579 (aba/opção de notas), e as páginas https://apisidra.ibge.gov.br/home/ajuda e https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-populacao.html (notas técnicas).
- Confirmar visualmente a nota (3) no PDF de 2012 (H), na página de SC.
- Ler `retificacao_estimativa_2013_dou.pdf` e verificar se afeta SC.
- Conferir se há notas judiciais de SC nos demais anos (2011, 2014 a 2020). Só verifiquei 2012, 2013 e 2021.
