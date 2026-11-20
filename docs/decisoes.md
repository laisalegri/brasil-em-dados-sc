# Registro de decisões

Decisões de projeto, da mais recente para a mais antiga. Cada entrada registra o que foi decidido, por quê e o que fica de fora.

## 2026-11-20 — Autenticação do agente de verificação pelo plano Pro (antes do D28)

- **Decisão:** o agente de verificação (D28/D29), feito com o Claude Agent SDK, autentica pelo login do plano Claude Pro (o mesmo do Claude Code). Não usa chave de API.
- **Por quê:**
  - o agente é uma ferramenta pessoal de desenvolvimento, rodada localmente;
  - logado com o plano, o Agent SDK consome dos limites da assinatura, sem cobrança extra;
  - não é preciso definir teto de gasto.
- **Fonte:** https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan. A política mudou algumas vezes em 2026, então a fonte deve ser reconferida no início do D28.
- **Cuidado:** se `ANTHROPIC_API_KEY` estiver definida no ambiente, ela tem prioridade sobre a assinatura, e a cobrança passa a ser por uso da API. Por isso:
  - `ANTHROPIC_API_KEY` saiu do `.env.example`, que agora explica que a variável não deve ser definida;
  - a autora confere pessoalmente que ela não está preenchida no `.env`, que não é lido pelos agentes;
  - no D28, o agente verifica ao iniciar se `ANTHROPIC_API_KEY` está definida e, se estiver, para com uma mensagem clara, sem mostrar o valor.
- **Consequência:** o cartão D28 deixa de prever "autenticação por chave de API" e "teto de gasto".

## 2026-11-18 — D30: camada GOLD em views

- **Decisão:**
  - **Views no schema `gold`:** versionadas em `sql/gold/NN_*.sql`. Os arquivos trazem só `CREATE VIEW gold.*` e `COMMENT ON`.
  - **`python -m brasil_em_dados.db.aplicar_gold`:** recria todas as views numa transação, como `bed_app`. Faz `DROP VIEW IF EXISTS` em ordem inversa, sem `CASCADE`, e `CREATE` em ordem direta.
  - **Exceção ao controle `public.ddl_aplicado`:** a GOLD fica fora dele. Views não guardam dados e são derivadas por inteiro da SILVER e dos arquivos versionados, então recriá-las a cada execução é seguro e mantém o banco igual aos arquivos. Por isso, os arquivos de `sql/gold/` podem ser editados, ao contrário dos de `sql/ddl/`, que rodam uma vez só (D18/D19).
  - **Leitura pelo `bed_readonly`:** vem dos privilégios padrão do schema `gold` (`01_schemas.sql`). No PostgreSQL, `ON TABLES` também vale para views, então uma view recriada recebe o `SELECT` de novo. Há teste para isso.
  - **Views:**
    - `dim_municipio`: as duas hierarquias, mais `ano_instalacao`, que é a fonte única dos municípios novos;
    - `grade_indicador_municipio_ano`: 12.095 linhas, com `status` (`com_valor`, `municipio_nao_instalado`, `sem_dado`) e `aviso`;
    - `painel_municipio_ano`: colunas `pop_estimada`, `pop_censo`, `pib_corrente_reais` e `pib_per_capita_reais`, sem população mista, e `base_estimativa`;
    - `variacao_populacao_censo`: 2010 × 2022;
    - `variacao_anual`: com `comparavel` e `motivo`;
    - `agregado_regiao_ano`: estado, região intermediária e região imediata;
    - `participacao_estadual`.
  - **Sem per capita agregado** (regra 4).
  - **Quebras da estimativa (regra 12, ampliada):** três bases (`ate_2012`, `2013_2017`, `desde_2018`).
    - Na variação de 2012 para 2013, o valor é `NULL` e `comparavel = false`.
    - Na de 2017 para 2018, o valor é calculado, com `comparavel = false` e motivo próprio.
  - **Dupla contagem de 2012 (regra 13, escolha do D26):** nas agregações e na participação, `pop_estimada` 2012 exclui 4212650 e 4220000. Há aviso na agregação, na grade e no painel (`dupla contagem 2012 (regra 13)`).
  - **Fonte única dentro da GOLD:**
    - a `base_estimativa` é calculada uma vez, na grade, a partir do ano, e as outras views herdam a coluna;
    - a grade junta a fato também por `cod_serie`, então uma segunda série num mesmo (indicador, ano) apareceria como chave repetida (testado), e não como valor trocado;
    - em `variacao_anual`, `comparavel` é `NULL` quando falta um dos valores;
    - divisões por zero viram `NULL`, com motivo.
  - **Validação do `aplicar_gold`:**
    - lê cada arquivo num único passe (literais e comentários `--` na ordem em que aparecem);
    - recusa `/* */`, `$` fora de literal, `--` dentro de literal e arquivos `00_*`;
    - aceita só `CREATE VIEW gold.<nome> AS` e `COMMENT ON VIEW`/`COLUMN` sobre views do próprio arquivo;
    - valida tudo antes de abrir a conexão.
  - **Operação:**
    - depois de editar um arquivo de `sql/gold/`, é preciso rodar o `aplicar_gold` de novo, porque o banco não se atualiza sozinho;
    - uma view removida ou renomeada nos arquivos continua no banco (o aplicador só avisa no log). A remoção é um `DROP VIEW` manual, feito a pedido da autora.
  - **Pendência para a reserva (D41/D42):** uma tabela versionada de anos esperados por série. Hoje, a grade deriva os anos da própria fato, e um ano que sumir inteiro some da grade sem status `sem_dado`. O teste de tamanho da grade pega esse caso, mas a view não o sinaliza. Essa tabela é uma decisão de modelagem.
- **Por quê:**
  - **2013 e 2018 tratados de forma diferente:**
    - Em 2013, a nova projeção muda o nível da série: SC já fica 2,80% acima da estimativa publicada para 2012, e o salto aparece em todos os municípios. Uma variação calculada seria lida como crescimento, então fica `NULL`.
    - Em 2018, o IBGE também troca a base (declara comparáveis só 2013–2017), mas não há salto visível em SC (+1,06% no estado). A variação é informativa e fica calculada, marcada como não comparável.
  - **Exclusão em 2012:** os dois municípios novos estão na mesma região imediata e intermediária do município de origem (Pescaria Brava e Laguna em 420003; Balneário Rincão e Içara em 420002). Por isso, excluí-los dá totais consistentes em todos os níveis, e o total do estado fica igual ao total de SC publicado (6.362.734). Se um município novo estivesse em outra região, a região de origem continuaria com dupla contagem e a região do novo perderia população. Há um teste que confere que os dois continuam na mesma região.
- **Consequência:**
  - as views foram aplicadas no banco real em 2026-11-18;
  - os testes de integração recriam as views numa transação desfeita, para testar os arquivos atuais sem mudar o banco, e conferem a leitura pelo `bed_readonly` nas views aplicadas.

## 2026-11-18 — D26: quebra de série e dupla contagem em pop_estimada

- **Decisão:**
  - **Quebra entre 2012 e 2013 (regra 12):**
    - a GOLD não calcula nem exibe variação de `pop_estimada` entre anos de bases diferentes (≤2012 contra ≥2013) sem aviso explícito;
    - a série vem com a quebra marcada.
  - **Dupla contagem em 2012 (regra 13):**
    - agregações de `pop_estimada` 2012 (estado, região) excluem 4212650 e 4220000 ou levam aviso;
    - a escolha entre as duas opções fica para o D30;
    - um teste de qualidade (`test_t16_dupla_contagem_2012_...`, marcador `integracao`) confere que soma municipal de 2012 − total de SC = população dos dois municípios. O total de SC, que não está no banco, vem do valor de referência do dicionário (`TOTAL_SC_6579_2012`).
- **Por quê:**
  - **Quebra:** a auditoria de qualidade (alerta A3) achou um salto de +2,55% em média por município em 2013. Os documentos oficiais confirmam a causa: a partir de 2013, as estimativas usam a nova Projeção da População por UF, e o IBGE declara comparáveis só as de 2013 a 2017. O salto é mudança de base, não crescimento populacional.
  - **Dupla contagem:** em 2012, a soma municipal da 6579 excede o total de SC exatamente pela população dos dois municípios ainda não instalados. Em 2011 e 2013, a soma fecha. A causa é NÃO CONFIRMADA. Somar 2012 sem cuidado contaria essas 20.552 pessoas duas vezes.
  - O teste avisa se uma revisão do IBGE mudar essa diferença.
- **Fonte:** `docs/fontes/alertas_qualidade_2026-11.md` (A3 e achado 6).
- **Nota (2026-11-18, D30):** a regra 12 foi ampliada. Ela passa a cobrir também a revisão de 2018, com três bases: `ate_2012`, `2013_2017` e `desde_2018`. A escolha deixada para o D30 na regra 13 foi feita: excluir os dois municípios das agregações de 2012, com coluna de aviso. Ver D30.
- **Consequência:**
  - as regras 12 e 13 entram no CLAUDE.md;
  - o dicionário (observações de `pop_estimada`) e `docs/limitacoes.md` (D27) descrevem as duas limitações;
  - a revisão de 2018 da projeção, sem salto visível em SC, fica documentada como limitação, sem regra própria.

## 2026-11-18 — D21: carga da fato e do controle de execução

- **Decisão:**
  - **Origem:**
    - para cada série da `dim_serie` (lida do banco), a última coleta válida na RAW;
    - a coleta é revalidada com as mesmas regras da coleta (`validar_conteudo`), usando como cadastro a `dim_municipio` do banco.
  - **Parsers (`transform/fato.py`, sem I/O):**
    - **SIDRA:** campos pelo cabeçalho. Pela regra 9, `-` vira 0 com sinal, número (inclusive `0`) vira valor sem sinal, e `...`, `..`, `X` e letras de faixa viram `NULL` com o sinal.
    - **API de Pesquisas:** código de 6 para 7 dígitos pelo cadastro (1:1), recorte 2010–2023 na carga, e `-` vira `NULL` com sinal `-`.
    - Um valor fora da legenda ou um `null` dentro do recorte é erro.
  - **Regra 10 na API de Pesquisas:** a validação de conteúdo, na coleta e na revalidação da carga, exige os anos de 2010 a 2023 em cada localidade, com um número em cada um, e só aceita `-` para 4212650 e 4220000 em 2010–2012. Antes, só as localidades eram conferidas, e um `-` fora do previsto viraria `NULL` em silêncio.
  - **Conversão (regra 11):** `Decimal(valor) × fator_conversao`, com 2 casas. Nunca `float`. Se o resultado exato tiver mais de 2 casas, a carga é recusada: arredondar mudaria o valor publicado em silêncio (regra 4).
  - **`data_coleta`:** significa "a coleta que trouxe este valor (valor e sinal)". O comentário da coluna no banco foi atualizado por `sql/ddl/04_comentario_data_coleta.sql`. Só `valor` e `sinal_origem` definem se uma linha mudou; a `data_coleta` é gravada junto quando eles mudam. Uma coleta nova com os mesmos valores não reescreve nada. A coleta mais recente de cada série está em `silver.controle_execucao`.
  - **Upsert em lote** (`load/upsert.py`, compartilhado com o D20):
    - só as linhas novas ou alteradas vão ao `INSERT`, então uma linha inalterada não gasta número da sequência nem ida ao banco;
    - `INSERT` com até 1.000 linhas por comando, limitado pelo número máximo de parâmetros, e `ON CONFLICT ... WHERE ROW(valor, sinal_origem) IS DISTINCT FROM ...`;
    - o `RETURNING` devolve as chaves, e a conferência compara chave a chave o que o banco gravou com o que a classificação previu;
    - um valor revisado é atualizado e aparece no log com a chave, o valor antigo e o novo;
    - uma linha que existe só no banco gera aviso e nunca é apagada;
    - `cod_serie` é imutável numa linha existente (`ErroCarga`), porque cada (indicador, ano) vem de uma única série.
  - **Controle:** `data/controle/execucoes.jsonl` é carregado em `silver.controle_execucao` pela chave (`cod_serie`, `inicio`). Uma execução já carregada com conteúdo diferente é recusada, porque o arquivo só recebe acréscimos.
  - **Sem tabela de estágio:** o parse é em memória e grava direto na fato. O texto do D21 no cronograma foi ajustado. D23, D24 e D25 foram absorvidos.
  - **Comandos:** `python -m brasil_em_dados.load fato` carrega a fato e o controle; `tudo` carrega dimensões, fato e controle. Cada comando roda numa transação só e mostra o resumo por série.
- **Por quê:**
  - comparar a `data_coleta` faria cada coleta nova reescrever as 12.093 linhas, mesmo sem nenhuma mudança de valor;
  - `Decimal` evita o erro binário do `float` em valores monetários;
  - a revalidação na carga protege contra uma RAW incompleta ou alterada desde a coleta.
- **Consequência:**
  - a primeira carga real (2026-11-18) gravou 12.093 linhas: 3.245 da 6579, 293 da 1378, 295 da 4709, 4.130 da 5938 e 4.130 da API de Pesquisas. Também gravou 24 execuções no controle;
  - na conferência:
    - os 14 `NULL` são todos de 4212650 ou 4220000 antes de 2013 (6 com `-`, da API de Pesquisas, e 8 com `...`, do SIDRA);
    - cada (indicador, ano) vem de uma única série;
    - não há PIB nem per capita negativo;
  - a segunda carga (`tudo`) deu tudo inalterado.

## 2026-11-17 — D20: carga das dimensões

- **Decisão:**
  - **Origem:** a `dim_municipio` vem da última coleta válida de `ibge_localidades_sc` na RAW, revalidada antes da carga (295 municípios, códigos únicos no padrão 42xxxxx). A `dim_indicador` e a `dim_serie` vêm do catálogo `brasil_em_dados.extract.catalogo`, que passou a guardar também os indicadores (`INDICADORES`). Testes conferem as tabelas 1.1 e 1.2 do dicionário contra o catálogo.
  - **Organização do código:** a transformação fica em `transform/dimensoes.py`, sem I/O. A leitura da RAW e a gravação ficam em `load/dimensoes.py`. O comando é `python -m brasil_em_dados.load dimensoes`, rodado como `bed_app` numa transação.
  - **Idempotência:** upsert com `INSERT ... ON CONFLICT DO UPDATE ... WHERE (colunas) IS DISTINCT FROM (novos valores)`. Uma linha igual não é reescrita, e a segunda carga não toca no banco.
  - **Resumo:** o resumo traz linhas inseridas, atualizadas e inalteradas por tabela. As contagens vêm da comparação com o que já estava no banco e são conferidas contra o número de linhas que o PostgreSQL gravou de fato.
  - **Nada é apagado:** uma linha no banco que não está na fonte é mantida e gera aviso no log.
  - **Atributos imutáveis:** numa linha que já existe, a carga recusa com `ErroCarga` qualquer mudança em:
    - `dim_serie`: `fator_conversao`, `unidade_origem` e `codigo_indicador`;
    - `dim_indicador`: `tipo_medida` e `unidade_armazenada`.

    A mensagem mostra o valor antigo e o novo e orienta: se a série (ou o indicador) mudou de fato, crie um novo `cod_serie` (ou `codigo_indicador`) no catálogo, em vez de alterar o existente. Os campos descritivos (`nome`, `descricao`, `url_extrator`, `data_referencia` e os nomes de municípios e regiões) continuam atualizáveis, e cada linha atualizada aparece no log com o valor antigo e o novo.
  - **Preparação fora da transação:** as linhas são montadas antes de abrir a transação. Cada tabela é travada (`SHARE ROW EXCLUSIVE`) entre a leitura e a gravação. As contagens de inseridas e de atualizadas são conferidas separadamente contra o que o banco devolve (`RETURNING (xmax = 0)`).
- **Por quê:**
  - um catálogo único evita que dicionário, extrator e banco divirjam;
  - mudar o fator, a unidade ou o indicador de uma série já carregada deixaria a fato com valores convertidos pelo fator antigo, ou com outro rótulo de censo ou estimativa, sem nenhum erro (regras 2 e 11). Uma série nova preserva a rastreabilidade;
  - o `WHERE ... IS DISTINCT FROM` deixa a reexecução sem efeito no banco (sem novas versões de linha);
  - apagar dimensão quebraria as FKs da fato e a rastreabilidade.
- **Consequência:** a primeira carga real (2026-11-17) gravou 4 indicadores, 5 séries e 295 municípios. A segunda carga deu 0 inseridas e 0 atualizadas, e todas as linhas de cada tabela têm o mesmo `xmin`, ou seja, foram gravadas por uma só transação.

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
