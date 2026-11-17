# Registro de decisões

Decisões de projeto, da mais recente para a mais antiga. Cada entrada registra o que foi decidido, por quê e o que fica de fora.

## 2026-11-17 — D18/D19: schemas por camada e regras de dados no banco

- **Decisão:**
  - **Schemas por camada:** `silver` e `gold`, com dono `bed_app`. A RAW continua em arquivos (`data/raw/`), fora do banco. O `bed_readonly` tem `USAGE` nos dois schemas e `SELECT` nas tabelas atuais e futuras (`ALTER DEFAULT PRIVILEGES`), sem escrita.
  - **Tabelas na SILVER:** `dim_municipio`, `dim_indicador`, `dim_serie`, `fato_indicador_municipio` e `controle_execucao`, conforme o dicionário (seção 1.4).
  - **Regras de dados como restrições no banco, além dos testes:**
    - código do município `^42[0-9]{5}$` e códigos regionais com o tamanho verificado na RAW;
    - ano de 2010 a 2023;
    - `valor numeric(18,2)` com `CHECK (valor IS NOT NULL OR sinal_origem IS NOT NULL)`;
    - regra 9 inteira: `sinal_origem` só aceita `-`, `...`, `..` ou uma letra de `A` a `Z` (inclui `X`), e valor numérico não tem sinal, exceto o `-` do SIDRA com valor 0;
    - chave primária (`cod_municipio`, `codigo_indicador`, `ano`) na fato;
    - `tipo_medida` `NOT NULL` com `CHECK` e `fator_conversao > 0`.
  - **Série coerente com o indicador:** a fato tem FK composta (`cod_serie`, `codigo_indicador`) para `dim_serie (cod_serie, codigo_indicador)`, que é `UNIQUE`. Assim, uma linha de `pop_censo` não pode apontar para uma série do PIB.
  - **`controle_execucao`:**
    - não tem FK para a `dim_serie`, porque recebe também as fontes de dimensão (`ibge_localidades_sc`);
    - um `CHECK` exige o mesmo contrato do `registrar_execucao`: sucesso tem arquivo e contagem, falha tem erro;
    - `UNIQUE (cod_serie, inicio)` permite recarregar o `execucoes.jsonl` (D21) sem duplicar.
  - **DDL:** arquivos numerados em `sql/ddl/` (`01_schemas`, `02_dimensoes`, `03_fato_e_controle`). São aplicados por `python -m brasil_em_dados.db.aplicar_ddl` como `bed_app`, em ordem e numa única transação: no primeiro erro, nada fica aplicado. O `00_banco_e_usuarios.sql` fica de fora, porque precisa de superusuário e roda no psql.
  - **Registro de DDL aplicado:** `public.ddl_aplicado` (`arquivo`, `sha256`, `aplicado_em`).
    - Cada arquivo roda uma vez só; rodar o aplicador de novo não reaplica nada.
    - Um arquivo já aplicado e editado depois (sha256 diferente) é erro, e a mensagem pede um arquivo novo numerado.
    - Também são erro: um arquivo registrado que sumiu da pasta, e um arquivo novo com número menor que o do último aplicado.
    - O sha256 é calculado com as quebras de linha normalizadas, porque o Git troca CRLF por LF.
    - O aplicador recusa comandos do psql e de transação (`BEGIN`, `COMMIT`...) nos scripts.
    - `IF NOT EXISTS` continua nos scripts como defesa extra.
  - **Pacote `db`:** o módulo `brasil_em_dados.db` virou pacote (`db/__init__.py`) para permitir `python -m brasil_em_dados.db.aplicar_ddl`. A interface (`engine_app`, `engine_readonly`) não mudou.
- **Por quê:**
  - uma regra que só existe em teste pode ser violada por uma carga com bug, ou por um `INSERT` manual, e só ser percebida depois. No banco, ela barra a linha na hora;
  - os schemas por camada deixam explícito o que é dado tratado (SILVER) e o que é analítico (GOLD), e permitem dar privilégios por camada;
  - a transação única evita um banco com metade do DDL aplicado.
- **Consequência:**
  - os arquivos `01` a `03` foram aplicados em 2026-11-17 e não podem mais ser editados. Qualquer mudança de estrutura vai num arquivo novo (`04_...sql`), que roda uma vez só;
  - os testes de integração aplicam o DDL numa transação sempre desfeita, com dados fictícios (município `4299990`, indicadores `teste_*`), e confirmam pelo SQLSTATE qual restrição barrou cada caso inválido;
  - os testes do `bed_readonly` nas tabelas reais executam `SET TRANSACTION READ WRITE` antes de tentar escrever, para provar que é a permissão da tabela (ACL) que barra (`42501`), e não só o `default_transaction_read_only`, que o próprio usuário pode desligar.

## 2026-11-17 — D17: banco, usuários e conexões

- **Decisão:**
  - banco `brasil_em_dados` no PostgreSQL local (15.5, porta 5432), com dono `bed_app`, usado pelo pipeline para criar tabelas e carregar dados;
  - `bed_readonly`, usado pelos agentes: só `CONNECT` no banco, `USAGE` no schema `public` e `SELECT` nas tabelas, inclusive as que o `bed_app` criar depois (`ALTER DEFAULT PRIVILEGES`). Não cria tabelas nem tabelas temporárias. Além disso, tem `default_transaction_read_only = on`, uma segunda barreira caso um privilégio de escrita seja concedido por engano;
  - os privilégios padrão valem só para objetos criados pelo `bed_app`; tabela criada por outro usuário precisa de `GRANT SELECT` explícito;
  - `PUBLIC` perde o acesso ao banco e o `CREATE` no schema `public`;
  - o script de criação fica em `sql/ddl/00_banco_e_usuarios.sql`. É idempotente e não tem senhas, que são definidas com `\password` e guardadas só no `.env`;
  - as conexões são montadas em `brasil_em_dados.db`, com `URL.create` do SQLAlchemy, driver `psycopg`, `hide_parameters=True` e tempo limite de conexão de 10 s;
  - o `.env` é lido com `dotenv_values` num dicionário local, e as variáveis do processo têm precedência. Os segredos não vão para `os.environ`, nem são herdados por subprocessos;
  - os testes que precisam do banco levam o marcador `integracao`.
- **Por quê:**
  - o CLAUDE.md exige acesso somente leitura para os agentes, e o próprio banco garante isso, não só a instrução;
  - `URL.create` mascara a senha em `str`/`repr`, então ela não vaza em log ou erro;
  - variável ausente gera erro que cita só o nome dela;
  - o tempo limite evita que um servidor parado trave o pipeline.
- **Consequência:**
  - os testes de integração são pulados quando a porta do banco não aceita conexão, e falham quando o servidor está no ar mas recusa a conexão (senha errada, banco inexistente), para não esconder configuração quebrada;
  - `pytest -m "not integracao"` roda só os testes sem banco;
  - a carga (D20 em diante) usa `engine_app()`, e os agentes usam `engine_readonly()`.

## 2026-11-14 — D16: códigos conferidos no cadastro e aviso de zero no SIDRA

- **Decisão:**
  - nas séries do SIDRA e da API de Pesquisas, todo código de município precisa existir no cadastro (`ibge_localidades_sc`); código desconhecido é falha de validação e nada é gravado na RAW;
  - no SIDRA, valor `0` em população ou PIB municipal gera aviso no log, sem reprovar a resposta.
  - no SIDRA, o único sinal aceito para os municípios novos é `...`, que é o que as tabelas 6579 e 5938 devolvem; um `-` nesses casos reprova a resposta.
- **Por quê:** o padrão `42xxxxx` sozinho aceitaria um código inexistente. O zero pode ser arredondamento (regra 9) e, para população e PIB de um município, é suspeito; mas reprovar a coleta inteira por isso bloquearia dados válidos da fonte. Já o `-` viraria zero na carga (regra 9) para município que ainda não existia, o que contraria as regras 5 e 10.
- **Consequência:** todas as séries passam a depender de uma coleta válida de `ibge_localidades_sc` na RAW. Se o cadastro mudar (município novo), as séries falham até que ele seja coletado de novo, o que é o comportamento desejado.

## 2026-11-14 — D11: padrão de coleta e rastreabilidade

- **Decisão:** todas as coletas seguem `docs/padrao_coleta.md`. Os pontos principais:
  - **RAW:** `data/raw/{cod_serie}/{AAAAMMDDTHHMMSSfffZ}.json`, em UTC com milissegundos, com os bytes originais da resposta. Os metadados ficam em `.meta.json` com o mesmo nome, incluindo `url`, `parametros`, `sha256`, `versao_extrator` e `igual_a_anterior`.
  - **Imutabilidade:** gravação em arquivo temporário seguida de `os.link`, que falha se o destino existir. Se o sistema de arquivos não suportar `os.link`, a coleta falha com erro claro; nunca se usa um caminho que possa sobrescrever. O `.meta.json` é gravado por último.
  - **Coleta válida:** só a que tem o par completo (dados + `.meta.json`). `igual_a_anterior` compara apenas com a última coleta válida da série, e a carga usa a coleta válida mais recente.
  - **Falha:** nada é gravado na RAW; o erro vai para o log e para o controle de execução.
  - **Controle de execução:** `data/controle/execucoes.jsonl`, fora da RAW. O D15 foi absorvido pelo D11.
  - **Catálogo de séries:** o módulo `brasil_em_dados.extract.catalogo` é a fonte única, usada pelos extratores e pela carga da `dim_serie` (D20), com teste que o confere contra o dicionário de dados.
  - **HTTP:** `requests.Session`, timeout de 10 s e 60 s, até 3 tentativas com backoff para 429, 5xx e timeout, respeitando `Retry-After`; User-Agent sem dados pessoais.
- **Por quê:**
  - um arquivo de controle alterado a cada execução dentro da RAW contrariaria a regra 7;
  - gravar os bytes originais mantém o `sha256` estável e a RAW fiel à resposta;
  - `os.rename` sobrescreve no Linux, e `os.link` impede a sobrescrita em qualquer sistema;
  - o par completo evita carregar coletas interrompidas;
  - o carimbo com milissegundos evita colisão de nomes;
  - o catálogo único evita três fontes da verdade (dicionário, extrator e banco);
  - o controle de execução é compartilhado por todos os extratores, por isso foi adiantado do D15.
- **Consequência:** os extratores do D12 ao D14 usam os módulos compartilhados. No D16, o escritor-de-testes amplia os testes de falha. A tabela `controle_execucao` é criada no D19 e carregada no D21.

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
