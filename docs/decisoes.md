# Registro de decisões

Decisões de projeto, da mais recente para a mais antiga. Cada entrada registra o que foi decidido, por quê e o que fica de fora.

## 2026-11-12 — D10: setores do PIB fora do MVP

- **Decisão:** o valor adicionado bruto por setor e os impostos ficam fora do MVP, como extensão. Na extensão, a fonte é a tabela 5938, variáveis 498 (VAB total), 513 (agropecuária), 517 (indústria), 6575 (serviços, exceto administração pública), 525 (administração pública) e 543 (impostos líquidos de subsídios). A tabela 5964 foi descartada: ela é da Pesquisa Nacional de Saúde do Escolar (PeNSE) 2015 e não tem relação com o PIB.
- **Por quê:**
  - a pergunta central do projeto não inclui a estrutura produtiva;
  - a série setorial termina em 2021: em 2022–2023, todas as variáveis setoriais vêm com `...` para os 295 municípios (nota técnica 02/2024 do IBGE);
  - a abertura setorial pode mudar com a nova base 2021 das Contas Nacionais;
  - a extensão é barata: usa a mesma URL e o mesmo extrator do PIB, só acrescentando variáveis (`v/37,498,513,517,6575,525,543`).
- **Consequência:** o dicionário de dados mantém os setores numa seção "EXTENSÃO (fora do MVP)". Testes previstos para a extensão: VAB total + impostos = PIB, e soma dos 4 setores = VAB total, com tolerância de arredondamento. Detalhes em `docs/fontes/sidra_5938.md` (seção "Setores (D10)") e `docs/fontes/sidra_5964.md`.
- **Ajustes aprovados na revisão do dicionário de dados:**
  1. **`tipo_medida`** sai da tabela fato e passa a ser atributo da `dim_indicador`, com valores `estimativa`, `censo` ou `nominal` e nunca `NULL`. A chave única da fato é (`cod_municipio`, `codigo_indicador`, `ano`). Motivo: o tipo depende só do indicador, e `NULL` em chave única no PostgreSQL permitiria duplicatas.
  2. **Códigos de indicador:** `pop_estimada`, `pop_censo` (único para 1378 e 4709), `pib_corrente` e `pib_per_capita`. Os nomes de colunas da `dim_municipio` estão aprovados; o código é convertido com `str(id).zfill(7)`.
  3. **Valor:** a fato tem uma coluna de valor única, em `numeric(18,2)`, para todos os indicadores.
  4. **Indicador separado da série de origem:**
     - `dim_indicador` (conceito de negócio): `codigo_indicador`, `nome`, `unidade_armazenada`, `tipo_medida`, `descricao`.
     - `dim_serie` (origem técnica, uma linha por tabela/variável ou pesquisa/indicador): `cod_serie`, `codigo_indicador` (FK), `fonte`, `tabela_ou_pesquisa`, `variavel_ou_indicador`, `unidade_origem`, `fator_conversao`, `data_referencia`, `url_extrator`. Séries do MVP: `sidra_6579_v9324`, `sidra_1378_v93`, `sidra_4709_v93`, `sidra_5938_v37` e `pesquisas_38_i47001`.
     - Fato: `cod_municipio`, `codigo_indicador`, `ano`, `cod_serie` (FK), `valor` (`numeric(18,2)`), `sinal_origem`, `data_coleta`. Chave única: (`cod_municipio`, `codigo_indicador`, `ano`).
     - A conversão de unidade usa o `fator_conversao` da `dim_serie`. A regra 8 é atendida pelo `cod_serie`: cada linha da fato identifica sua série, e a série identifica tabela/variável ou pesquisa/indicador.
     - Motivo: atributos que dependem da fonte (tabela, data de referência, unidade de origem, fator) ficam na série; o indicador guarda só o conceito. Isso permite um `pop_censo` único com duas origens (1378 em 2010 e 4709 em 2022) e facilita incluir os setores depois, como novas séries da 5938.
  5. **Extrator do SIDRA:** localiza os campos pelo cabeçalho da resposta (primeira linha), nunca pela posição das colunas `D*`, porque a ordem varia por tabela.
  6. **Testes previstos para o D26:**
     - validação do D09: PIB (R$) / população ≈ PIB per capita, usando a 6579 em 2011–2021 e a 4709 em 2023, excluindo 2010, 2022 e Içara e Laguna em 2012;
     - cada combinação (`codigo_indicador`, `ano`) vem de exatamente uma série.

## 2026-11-12 — D09: PIB, PIB per capita e API de Pesquisas

- **Decisão:**
  1. **PIB e unidades monetárias:** valores monetários são convertidos para reais (R$) na camada SILVER. A RAW continua guardando a resposta original da API, sem alteração.
     - O PIB da tabela 5938 (variável 37), publicado em "Mil Reais", é multiplicado por 1000 na carga para a SILVER. O PIB per capita (indicador 47001) já vem em reais (fator 1).
     - Tipo no PostgreSQL: `numeric(18,2)` para valores monetários; nunca `float`/`double`.
     - Rastreabilidade: a `dim_serie` registra `unidade_origem` e `fator_conversao`, e a `dim_indicador` registra `unidade_armazenada`; a RAW preserva o valor original. *(Ajustado no D10. O texto anterior dizia que a `dim_indicador` registrava as três colunas; elas foram divididas com a criação da `dim_serie`.)*
     - *(Revisado em 2026-11-12. O texto anterior dizia: "PIB em mil reais (unidade da fonte: 'Mil Reais'). A unidade é guardada como veio; a conversão para reais, quando necessária, acontece na GOLD." Motivo da mudança: padronizar unidades é papel da SILVER; isso elimina o risco de misturar mil reais e reais nas camadas seguintes e permite validações diretas como PIB / população ≈ PIB per capita.)*
  2. **PIB per capita:** API de Pesquisas do IBGE, pesquisa 38, indicador 47001 ("PIB per capita" → "Série revisada"), em **reais** (unidade R$ com multiplicador 1; "R$ 1,00" no layout da base oficial). Fica diferente da unidade do PIB, e as duas unidades são registradas em cada linha da tabela fato. O valor é o publicado, sem recálculo.
  3. **Nova fonte:** a API de Pesquisas passa a ser fonte oficial do projeto. Na tabela fato, a identificação da série guarda tabela/variável para o SIDRA e pesquisa/indicador para a API de Pesquisas.
  4. **Código de 6 dígitos:** a API de Pesquisas devolve o código do município sem o dígito verificador. O extrator converte para 7 dígitos pelo cadastro da API de Localidades. Um teste garante correspondência 1:1: cada código de 6 dígitos corresponde a exatamente um código de 7 dígitos do cadastro, e nenhum código fica sem par.
  5. **Sinal `-` na API de Pesquisas:** carrega como `NULL`, com `sinal_origem` = `-`. Nessa API, o `-` marca municípios que não existiam no ano (Pescaria Brava e Balneário Rincão em 2010–2012). A regra de `-` como zero absoluto vale só para o SIDRA.
  6. **Cobertura (ajuste da D08):** ausência ou sinal é aceito para 4212650 e 4220000 em anos anteriores a 2013, o ano de instalação.
- **Por quê:** nenhuma tabela SIDRA traz o PIB per capita no nível municipal. O indicador 47001 é idêntico à base oficial do PIB dos Municípios nas 4.124 linhas de SC. Na 5938, os dois municípios vêm com `...` até 2012, porque o PIB deles começa em 2013. Carregar o `-` da API de Pesquisas como 0 criaria um valor falso para municípios inexistentes.
  Converter na SILVER padroniza as unidades na camada certa, elimina o risco de misturar mil reais e reais nas camadas seguintes e permite validar PIB / população ≈ PIB per capita diretamente.
- **Consequência:** a população usada pelo IBGE no per capita está documentada em `docs/fontes/ibge_pesquisas_pib_per_capita.md`: estimativa TCU em 2010–2021, 1ª apuração do Censo 2022 em 2022 e população enviada ao TCU em 2023. Os valores de 2022 e 2023 podem ser revisados pelo IBGE.
  - Testes previstos para o D26: (1) cada indicador tem exatamente uma `unidade_armazenada` na tabela fato; (2) para uma amostra de municípios e anos, PIB (R$) / população usada pelo IBGE ≈ PIB per capita publicado, dentro de uma tolerância de arredondamento.
  - O catálogo de indicadores em `docs/dicionario_dados.md` (D10) deve incluir as colunas `unidade_origem`, `fator_conversao` e `unidade_armazenada`.

## 2026-11-12 — D08: filtro por UF e cobertura das tabelas SIDRA

- **Decisão:** todas as tabelas SIDRA são extraídas com o filtro por UF (`n6/in n3 42`). A tabela fato guarda apenas o que a fonte devolveu: valores numéricos e sinais, estes com `sinal_origem`. Combinações município × ano ausentes na fonte não geram linha. A grade completa (295 municípios × anos) é montada na camada GOLD a partir da `dim_municipio`, exibindo "sem dado" onde não há valor.
- **Por quê:** a consulta por UF omite municípios sem valor no período. Na tabela 1378 (Censo 2010), Pescaria Brava (4212650) e Balneário Rincão (4220000) não aparecem, embora venham com `...` quando consultados pelo código. Guardar só o que a fonte devolveu mantém a tabela fato fiel ao RAW e evita criar linhas que a fonte não publicou. A grade completa é uma necessidade de apresentação e por isso fica na GOLD.
- **Consequência:** a cobertura é garantida por teste. Ausência de linha ou `...` só é aceita para 4212650 e 4220000 em anos anteriores a 2013; qualquer outro município ou ano sem valor faz o teste falhar. *(Ajustado no D09: o texto original dizia "anteriores a 2012", mas a tabela 5938 traz `...` para os dois municípios também em 2012.)* As URLs de extração estão em `docs/fontes/sidra_6579.md`, `docs/fontes/sidra_1378.md` e `docs/fontes/sidra_4709.md`.

## 2026-11-12 — D06: hierarquia territorial na `dim_municipio`

- **Decisão:** a `dim_municipio` guarda as duas divisões regionais do IBGE, com códigos em texto e nomes de coluna explícitos por divisão:
  - divisão nova: `cod_regiao_imediata`, `nome_regiao_imediata`, `cod_regiao_intermediaria`, `nome_regiao_intermediaria`;
  - divisão antiga: `cod_microrregiao`, `nome_microrregiao`, `cod_mesorregiao`, `nome_mesorregiao`.

  Os dashboards usam a divisão nova, com a região intermediária como filtro principal. As duas divisões nunca se relacionam pelo id.
- **Por quê:** a API de Localidades entrega as duas hierarquias completas, e a divisão nova substitui a antiga. Manter a antiga permite comparar com análises e publicações anteriores. Os ids de mesorregião e de região intermediária usam a mesma faixa (4201–4207) para entidades diferentes; por exemplo, a mesorregião 4201 é o Oeste Catarinense e a intermediária 4201 é Florianópolis. Nomes de coluna genéricos (como `cod_regiao`) permitiriam junções erradas.
- **Consequência:** a carga converte todos os ids para texto. Detalhes da fonte estão em `docs/fontes/ibge_localidades.md`.

## 2026-11-12 — D07: sinais especiais do SIDRA e coluna `sinal_origem`

- **Decisão:** a tabela fato terá a coluna `sinal_origem` (texto), com o sinal SIDRA original. Ela fica `NULL` quando o valor veio numérico. Os sinais `-` (zero absoluto) e `0` (zero por arredondamento) carregam como 0. Os demais (`...`, `..`, `X` e letras de faixa) carregam como `NULL`.
- **Por quê:** a regra "ausência é `NULL`, nunca zero" não deve apagar a informação de *por que* o valor falta. Guardar o sinal mantém a rastreabilidade até a fonte e distingue zero verdadeiro de ausência. Exemplo: Pescaria Brava e Balneário Rincão vêm com `...` em 2011 na tabela 6579.
- **Consequência:** o significado de cada sinal está em `docs/fontes/sidra_convencoes.md`. Os testes de carga devem verificar que nenhum sinal vira zero indevidamente.

## 2026-11-11 — D02: dados brutos fora do Git

- **Decisão:** `data/raw/`, `data/processed/` e `reports/` não são versionados. O pipeline recria esses arquivos.
- **Por quê:** manter o repositório leve e garantir que os dados venham sempre da fonte oficial, de forma reproduzível.
- **Consequência:** amostras pequenas usadas em testes ou na documentação ficam em `tests/` ou `docs/`.

## 2026-11-11 — D01: escopo do MVP

| Decisão | Motivo |
| --- | --- |
| Indicadores do MVP: população (censo e estimativa), PIB nominal e PIB per capita | São as fontes com tabelas identificadas; a estrutura setorial ainda depende de validação (D10) |
| Estrutura setorial fica como extensão | Setores (extensão): tabela 5938, variáveis 498, 513, 517, 6575, 525 e 543; sem abertura em 2022–2023. *(Corrigido no D10. O texto anterior dizia: "Tabela candidata 5964 e códigos setoriais não confirmados". A 5964 é da PeNSE 2015 e foi descartada.)* |
| Período 2010–2023 e cadastro atual de 295 municípios | Mantém o Censo 2010; municípios instalados depois de 2010 têm ausência esperada e documentada |
| PIB per capita: valor publicado pelo IBGE, sem recálculo | Usa a referência oficial; a população usada como denominador será documentada |
| Variação populacional oficial: Censo 2010 × Censo 2022 | Estimativas aparecem só como série complementar |
| MVP roda localmente; publicar o Streamlit (sem agente) é a primeira extensão | Evita custo e infraestrutura no MVP |
| Agentes de IA servem ao desenvolvimento; agente de perguntas de negócio é extensão | Prioriza entregar mais rápido e com qualidade |
