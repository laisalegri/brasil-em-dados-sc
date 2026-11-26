# Padrão de coleta e rastreabilidade

- **Versão:** 2026-11-14 (cartão D11; absorve o D15, controle de execução)
- **Decisão:** D11 em `docs/decisoes.md`
- **Vale para:** todos os extratores em `src/brasil_em_dados/extract/` (API de Localidades, API SIDRA e API de Pesquisas)

Este documento define como cada coleta é feita, gravada e registrada, para que a camada RAW seja imutável (regra 7) e todo dado carregado possa ser rastreado até a resposta original da API.

## 1. Catálogo de séries (fonte única)

- O módulo `brasil_em_dados.extract.catalogo` é a **fonte única** das séries coletadas: `cod_serie`, URL do extrator (`url_extrator`, mesmo nome da coluna da `dim_serie`), parâmetros, fonte e os atributos da `dim_serie` (indicador, tabela/pesquisa, variável/indicador, unidade de origem, fator de conversão, data de referência).
- O mesmo módulo é usado pela carga da `dim_serie` e da `dim_indicador` (D20). Assim, extrator e banco não divergem.
- Um teste confere que os `cod_serie` do catálogo, com indicador, fonte e fator, batem com a tabela 1.2 do `docs/dicionario_dados.md`.
- A coleta de municípios (API de Localidades) entra no catálogo como **fonte de dimensão**, com código `ibge_localidades_sc`. Ela não é uma série da `dim_serie`.

## 2. Caminhos e nomes na RAW

```
data/raw/{cod_serie}/{AAAAMMDDTHHMMSSfffZ}.json        resposta original
data/raw/{cod_serie}/{AAAAMMDDTHHMMSSfffZ}.meta.json   metadados da coleta
data/raw/ibge_localidades_sc/...                       mesma regra para municípios
```

- O carimbo é o instante da coleta em **UTC**, com milissegundos (`fff`), para que duas coletas no mesmo segundo não gerem o mesmo nome. Exemplo: `20261114T153012045Z.json`.
- O arquivo de dados guarda os **bytes originais** da resposta (`response.content`), sem reprocessar o JSON. Reprocessar mudaria espaços, ordem das chaves e escape de acentos, e a RAW deixaria de ser a resposta original.

## 3. Metadados (`.meta.json`)

| Campo | Conteúdo |
|---|---|
| `cod_serie` | Código da série no catálogo |
| `url` | URL exata consultada |
| `parametros` | Parâmetros legíveis da consulta, por exemplo `{"tabela": "5938", "variaveis": ["37"], "periodo": "2010-2023", "nivel": "n6 in n3 42"}` (regra 7) |
| `status_http` | Código HTTP da resposta |
| `coletado_em` | Instante da coleta, UTC, ISO 8601 com milissegundos (ex.: `2026-11-14T15:30:12.045Z`) |
| `duracao_ms` | Duração da requisição bem-sucedida, em milissegundos |
| `tentativas` | Número de tentativas HTTP até o sucesso |
| `n_registros` | Registros de dados na resposta (ver seção 6) |
| `tamanho_bytes` | Tamanho do arquivo de dados |
| `sha256` | Hash SHA-256 dos bytes gravados |
| `versao_extrator` | Hash curto do commit (`git rev-parse --short HEAD`), com sufixo `-dirty` se houver mudanças locais; `desconhecido` fora de um repositório git |
| `igual_a_anterior` | `true` se o `sha256` é igual ao da última coleta válida da série |
| `arquivo_dados` | Nome do arquivo de dados correspondente |

## 4. Imutabilidade e gravação

1. O conteúdo é gravado num arquivo temporário oculto **na mesma pasta** do destino.
2. O destino é criado com `os.link(temporario, destino)`, que **falha se o destino já existir**, em qualquer sistema operacional.
3. O temporário é removido. Removê-lo não fere a regra 7, porque ele ainda não é RAW.
4. Se o destino existir, a coleta falha. Nada é sobrescrito nem apagado.
5. Se o sistema de arquivos não suportar `os.link`, a coleta **falha com erro claro**. Nunca se usa um caminho alternativo que possa sobrescrever (`os.replace`, `os.rename` no Linux, `shutil.move`).
6. O `.meta.json` é gravado **por último**, com o mesmo mecanismo.

**Coleta válida:** só é válida a coleta que tem o **par completo** (arquivo de dados + `.meta.json`). Um arquivo de dados sem `.meta.json` é uma coleta incompleta: é ignorado pela carga e pelo `igual_a_anterior`, e gera um aviso no log.

## 5. Reexecução

- Toda coleta gera arquivos novos, mesmo que a resposta seja idêntica à anterior.
- `igual_a_anterior` compara o `sha256` apenas com a **última coleta válida** da série (par completo). Coletas incompletas são ignoradas.
- A carga usa a **coleta válida mais recente** de cada série.

## 6. Validação mínima

Uma resposta só é gravada se passar por todas as verificações:

1. `status_http` = 200.
2. JSON válido. Isso barra, por exemplo, a página HTML do desafio Cloudflare, que vem com status 200.
3. Conteúdo não vazio, conforme a fonte:

| Fonte | Estrutura esperada | `n_registros` |
|---|---|---|
| API SIDRA | Lista com cabeçalho e **pelo menos uma** linha de dados | Linhas sem contar o cabeçalho |
| API de Localidades | Lista não vazia | Número de municípios |
| API de Pesquisas | Lista não vazia; cada indicador com lista `res` não vazia | Número de localidades |

4. **Códigos no cadastro:** nas séries do SIDRA e da API de Pesquisas, todo código de município precisa existir no cadastro, que é a última coleta válida de `ibge_localidades_sc` na RAW. Código desconhecido reprova a resposta. Sem cadastro na RAW, a coleta da série falha com a mensagem "colete ibge_localidades_sc antes". Por isso, com "todas", as dimensões são coletadas primeiro.

As contagens esperadas por série (por exemplo, 295 municípios, ou 293 linhas na 1378) ficam em `extract/conteudo.py`, do D12 ao D14. No SIDRA, o único sinal aceito é `...`, e só nos municípios e anos previstos na regra da série. Um `-` nesses casos reprova a resposta, porque na carga viraria zero (regra 9) para município que ainda não existia.

**Aviso, sem reprovar:** no SIDRA, um valor `0` em população ou PIB municipal gera aviso no log, mas a resposta é gravada. Pela regra 9 ele pode ser zero por arredondamento, e para esses indicadores é suspeito. A assimetria é intencional: `0` é um número publicado pela fonte; `-` fora do previsto é um sinal inesperado.

## 7. Cliente HTTP

- `requests.Session`, com `User-Agent` que identifica o projeto sem dados pessoais: `brasil-em-dados-sc/0.1 (projeto de portfolio)`.
- Timeout de 10 s para conexão e 60 s para leitura.
- Até **3 tentativas**, com backoff exponencial (1 s, 2 s...) para **429**, **5xx** e **timeout**.
- Em 429 ou 5xx com cabeçalho `Retry-After` em segundos, esse valor prevalece sobre o backoff. Um `Retry-After` inválido é ignorado e vale o backoff.
- Toda espera, por backoff ou por `Retry-After`, tem teto de **60 s**, para que um servidor não bloqueie a coleta por tempo indefinido.
- Os demais **4xx** falham sem nova tentativa.

## 8. Falhas

- Em qualquer falha (HTTP, validação ou gravação), **nada é gravado na RAW**.
- O erro vai para o log e para o controle de execução.

## 9. Controle de execução

- Arquivo `data/controle/execucoes.jsonl`, **fora da RAW**, não versionado. Uma linha JSON por execução, sempre acrescentada ao final.
- Campos: `cod_serie`, `inicio`, `fim` (UTC, ISO 8601), `status` (`sucesso` ou `falha`), `n_registros`, `arquivo` (arquivo de dados gravado, ou `null`), `erro` (mensagem, ou `null`).
- A tabela `controle_execucao` é criada no D19 e recebe este arquivo no D21.

## 10. Logs

- Módulo `logging`, nunca `print`.
- Saída no console e em arquivo na pasta `logs/`, não versionada.
- Os logs nunca registram credenciais nem conteúdo do `.env`.

## 11. Testes

- Sem acesso à rede: `unittest.mock` para simular respostas HTTP e `tests/fixtures` para amostras.
- Arquivos gravados em pasta temporária do pytest (`tmp_path`). Nenhum teste escreve em `data/`.
- Sem dependências novas.
- No D16, o subagent escritor-de-testes amplia os testes de falha: timeout, erro HTTP, resposta vazia e não sobrescrita da RAW.

## 12. Fora deste padrão

- A extensão de setores (URL combinada de cerca de 9 MB) não faz parte do MVP. Quando entrar, rever o tempo limite de leitura.
