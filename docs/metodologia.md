# Metodologia

- **Versão:** 2026-11-18 (cartão D27)
- **Situação:** descreve o que está implementado até o D26: coleta RAW, banco, carga na SILVER e testes de qualidade. A GOLD, a EDA, os dashboards e o agente de verificação ainda não existem (D28 em diante, `docs/cronograma_previsto.md`).

Este documento resume o fluxo e aponta para os documentos de referência. As regras completas estão nos arquivos citados em cada seção.

## 1. Fluxo

```
APIs do IBGE (Localidades, SIDRA, Pesquisas)
   │  python -m brasil_em_dados.extract todas
   ▼
RAW      data/raw/{cod_serie}/  — resposta original + .meta.json, imutável
   │  python -m brasil_em_dados.load tudo
   ▼
SILVER   PostgreSQL, schema silver — dimensões, fato e controle de execução
   │  (D30, planejado)
   ▼
GOLD     PostgreSQL, schema gold — criado, ainda sem tabelas
```

| Etapa | Código | Referência |
|---|---|---|
| Coleta | `src/brasil_em_dados/extract/` | `docs/padrao_coleta.md`, D11 e D16 |
| Banco e DDL | `sql/ddl/`, `src/brasil_em_dados/db/` | D17 e D18/D19 |
| Transformação (sem I/O) | `src/brasil_em_dados/transform/` | D20 e D21 |
| Carga | `src/brasil_em_dados/load/` | D20 e D21 |
| Qualidade | `tests/test_qualidade_dados.py`, `.claude/agents/revisor-de-qualidade-de-dados.md` | D22 e D26 |

Os códigos D01–D26 citados neste documento são entradas de `docs/decisoes.md`.

## 2. Fontes e séries

O catálogo `brasil_em_dados.extract.catalogo` é a fonte única das séries: os extratores e a carga da `dim_serie` e da `dim_indicador` leem dele, e um teste o confere contra as tabelas 1.1 e 1.2 do dicionário (D11, D20).

| `cod_serie` | Indicador | Fonte | Tabela/pesquisa | Variável/indicador | Unidade de origem | Fator | Anos |
|---|---|---|---|---|---|---|---|
| `sidra_6579_v9324` | `pop_estimada` | SIDRA | 6579 | 9324 | Pessoas | 1 | 2011–2021 |
| `sidra_1378_v93` | `pop_censo` | SIDRA | 1378 (Censo 2010) | 93 | Pessoas | 1 | 2010 |
| `sidra_4709_v93` | `pop_censo` | SIDRA | 4709 (Censo 2022) | 93 | Pessoas | 1 | 2022 |
| `sidra_5938_v37` | `pib_corrente` | SIDRA | 5938 | 37 | Mil Reais | 1000 | 2010–2023 |
| `pesquisas_38_i47001` | `pib_per_capita` | API de Pesquisas | 38 | 47001 | R$ | 1 | 2010–2023 |

Além das séries, o catálogo tem a fonte de dimensão `ibge_localidades_sc` (API de Localidades), que alimenta a `dim_municipio` e serve de cadastro para validar os códigos das séries (D16).

URLs, datas de referência, sinais e cobertura: `docs/dicionario_dados.md` (seções 1, 4 e 5) e `docs/fontes/`.

## 3. Coleta (RAW)

Comando: `python -m brasil_em_dados.extract <cod_serie>` ou `python -m brasil_em_dados.extract todas`. Com `todas`, `ibge_localidades_sc` é coletada primeiro, porque as séries conferem seus códigos nesse cadastro. Uma falha não interrompe as demais coletas; o comando termina com código 1 se alguma falhar.

Padrão completo em `docs/padrao_coleta.md` (D11). Os pontos principais:

- **Arquivos:** `data/raw/{cod_serie}/{AAAAMMDDTHHMMSSfffZ}.json` com os bytes originais da resposta, e `.meta.json` com URL, parâmetros, status HTTP, `coletado_em`, `n_registros`, `sha256`, `versao_extrator` e `igual_a_anterior`.
- **Imutabilidade (regra 7):** gravação em arquivo temporário seguida de `os.link`, que falha se o destino existir. Nada é sobrescrito nem apagado. O `.meta.json` é gravado por último; só o par completo é uma coleta válida.
- **Validação antes de gravar:** status 200, JSON válido, conteúdo não vazio, contagens esperadas por série (`extract/conteudo.py`), todo código de município presente no cadastro e sinais só nos municípios e anos previstos. Na API de Pesquisas, cada localidade precisa ter os anos de 2010 a 2023, e o `-` só é aceito para 4212650 e 4220000 em 2010–2012 (D16, D21). Se a validação falha, nada é gravado na RAW.
- **HTTP:** timeout de 10 s (conexão) e 60 s (leitura), até 3 tentativas para 429, 5xx e timeout, `Retry-After` respeitado com teto de 60 s.
- **Controle de execução:** cada execução, com sucesso ou falha, acrescenta uma linha em `data/controle/execucoes.jsonl`, fora da RAW.
- **Logs:** `logging`, no console e em `logs/pipeline_AAAAMMDD.log`.

`data/raw/`, `data/controle/` e `logs/` não são versionados (D02).

## 4. Banco e DDL

| Passo | Como | Quem |
|---|---|---|
| Banco e usuários | `psql -U postgres -f sql/ddl/00_banco_e_usuarios.sql`, depois `\password bed_app` e `\password bed_readonly` no psql | superusuário |
| Schemas e tabelas | `python -m brasil_em_dados.db.aplicar_ddl` | `bed_app` |

- **Usuários (D17):**
  - `bed_app` é dono do banco e dos schemas; o pipeline cria tabelas e carrega dados com ele.
  - `bed_readonly` é usado pelos agentes e pelos testes de qualidade: só `SELECT` nas tabelas atuais e futuras dos schemas `public`, `silver` e `gold`, sem criar tabelas e com `default_transaction_read_only = on`.
  - As senhas ficam só no `.env` (modelo em `.env.example`), nunca nos scripts.
- **Schemas (D18/D19):** `silver` e `gold`. A RAW fica em arquivos, fora do banco.
- **Aplicador de DDL:** roda os arquivos `01_` em diante em ordem numérica, numa única transação. Cada arquivo aplicado fica registrado em `public.ddl_aplicado` (`arquivo`, `sha256`, `aplicado_em`) e não roda de novo. Editar um arquivo já aplicado é erro: a mudança vai num arquivo novo numerado (como `04_comentario_data_coleta.sql`, do D21).
- **Regras no banco, além dos testes:** código do município `^42[0-9]{5}$`, ano de 2010 a 2023, `valor numeric(18,2)`, valor ou sinal sempre presente, `sinal_origem` restrito à legenda da regra 9, chave primária (`cod_municipio`, `codigo_indicador`, `ano`), `tipo_medida` `NOT NULL` com `CHECK`, `fator_conversao > 0` e FK composta que impede uma linha de apontar para série de outro indicador. Lista completa no dicionário, seção 1.4.

## 5. Carga na SILVER

Comando: `python -m brasil_em_dados.load {dimensoes,fato,tudo}`, como `bed_app`. Cada comando roda numa transação só; em qualquer erro, nada fica gravado.

### 5.1 Dimensões (D20)

- `dim_municipio`: da última coleta válida de `ibge_localidades_sc`, revalidada (295 municípios, códigos únicos). O código vira texto de 7 dígitos (regra 1).
- `dim_indicador` e `dim_serie`: do catálogo.
- Numa linha existente, a carga recusa mudança de `fator_conversao`, `unidade_origem` e `codigo_indicador` (série) e de `tipo_medida` e `unidade_armazenada` (indicador). Uma série que mudou de fato vira um novo `cod_serie`.

### 5.2 Fato (D21)

1. Para cada série da `dim_serie`, lê a última coleta válida na RAW e a revalida com as mesmas regras da coleta, usando a `dim_municipio` do banco como cadastro.
2. Interpreta os valores (`transform/fato.py`, sem I/O):
   - **SIDRA:** campos localizados pelo cabeçalho da resposta, nunca pela posição.
   - **API de Pesquisas:** código de 6 dígitos convertido para 7 pelo cadastro, com correspondência 1:1; recorte 2010–2023 na carga (a RAW guarda 1999–2023).
3. Aplica os sinais (regra 9):

| Fonte | Sinal | `valor` | `sinal_origem` |
|---|---|---|---|
| SIDRA | número, inclusive `0` | o número | `NULL` |
| SIDRA | `-` | 0 | `-` |
| SIDRA | `...`, `..`, `X`, letras de faixa | `NULL` | o sinal |
| API de Pesquisas | `-` | `NULL` | `-` |

   Um valor fora da legenda é erro.
4. Converte a unidade (regra 11): `Decimal(valor) × fator_conversao`, com 2 casas, nunca `float`. Se o resultado exato tiver mais de 2 casas, a carga é recusada.
5. Grava por upsert em lote: só linhas novas ou com `valor` ou `sinal_origem` diferentes vão ao banco. A conferência compara chave a chave o que o banco gravou com o previsto.

- **`data_coleta`:** a coleta que trouxe este valor (valor e sinal). Uma coleta nova com o mesmo valor e sinal não reescreve a linha. A coleta mais recente de cada série está em `silver.controle_execucao`.
- **Nada é apagado:** uma linha que existe só no banco gera aviso e fica. Um valor revisado pela fonte é atualizado e aparece no log com o valor antigo e o novo. O `cod_serie` de uma linha existente não muda.
- **Sem linha para o que a fonte não devolveu:** combinações ausentes na resposta não geram linha; a grade completa fica para a GOLD (D08).
- **Controle:** `data/controle/execucoes.jsonl` é carregado em `silver.controle_execucao`, pela chave (`cod_serie`, `inicio`).

### 5.3 Resultado da primeira carga (2026-11-18)

12.093 linhas na fato e 24 execuções no controle (D21):

| Série | Linhas |
|---|---|
| `sidra_6579_v9324` | 3.245 |
| `sidra_1378_v93` | 293 |
| `sidra_4709_v93` | 295 |
| `sidra_5938_v37` | 4.130 |
| `pesquisas_38_i47001` | 4.130 |

Os 14 `NULL` são todos de 4212650 ou 4220000 antes de 2013. A segunda carga (`tudo`) não alterou nenhuma linha.

## 6. Qualidade

### 6.1 Auditoria

O subagent `revisor-de-qualidade-de-dados` (`.claude/agents/`) audita a SILVER como `bed_readonly`, numa transação somente leitura, e grava o relatório em `reports/` (não versionado). A auditoria de 2026-11-18 (`reports/qualidade_20261118.md`) encontrou:

| Classe | Quantidade |
|---|---|
| ERRO (quebra regra do projeto) | 0 |
| ALERTA | 3: A1 variações de PIB municipal acima de 50%; A2 salto da soma do PIB em 2021; A3 salto da estimativa em 2013 |
| OBSERVAÇÃO | 9 |

Os alertas foram investigados em fontes oficiais (`docs/fontes/alertas_qualidade_2026-11.md`) e estão descritos em `docs/limitacoes.md`.

### 6.2 Validação PIB / população ≈ per capita

Confere se o PIB em reais dividido pela população reproduz o per capita publicado (D09/D10).

- **Base:** estimativa 6579 em 2011–2021 e Censo 2022 (4709) em 2023, que são os denominadores oficiais reproduzíveis (`docs/fontes/ibge_pesquisas_pib_per_capita.md`).
- **Excluídos:** 2010 e 2022 (denominador oficial fora das tabelas do projeto) e Içara (4207007) e Laguna (4209409) em 2012. Os dois municípios instalados em 2013 não têm valor em 2011–2012.
- **Tolerância:** `500 / população + R$ 0,01`. O SIDRA arredonda o PIB para inteiro em mil reais, então o PIB em reais tem erro de até R$ 500, e o per capita publicado tem arredondamento de centavo.

| Pares comparados | Fora da tolerância | Mediana da diferença relativa | Máxima diferença relativa | Máxima diferença absoluta |
|---|---|---|---|---|
| 3.534 | 0 | 8,4e-7 | 1,71e-5 | R$ 0,32 |

Números da auditoria (relatório, seção 4.1). Uma tolerância fixa de meio centavo reprovaria 84% dos pares, por causa do arredondamento do PIB.

### 6.3 Testes automatizados

`tests/test_qualidade_dados.py` (marcador `integracao`) roda como `bed_readonly`, numa transação somente leitura sempre desfeita. Os valores esperados saem do catálogo e de `extract/conteudo.py`. Se a fato estiver vazia, os testes são pulados.

| Teste | O que verifica |
|---|---|
| T1 | Linhas por série e ano iguais às publicadas (295 por ano; 293 na 1378) |
| T2 | Nenhuma linha em ano que a série não publica |
| T3 | Cada (indicador, ano) vem de uma única série |
| T4 | Sem órfãos nas FKs, e toda dimensão usada na fato |
| T5 | Cobertura da regra 10, por série, nos anos publicados |
| T6 | Os `NULL` são exatamente os previstos e todos têm sinal |
| T7 | Unidade armazenada, unidade de origem e fator por indicador iguais ao catálogo |
| T8 | Nenhum valor negativo |
| T10 | Conversão coerente: PIB múltiplo de 1000 e população inteira |
| T11 | PIB / população ≈ per capita (seção 6.2), com o número de pares conferido (3.534) |
| T13 | `data_coleta` corresponde ao arquivo RAW de uma coleta com sucesso da mesma série |
| T14 | `n_registros` da última coleta bate com as linhas da fato |
| T15 | Soma anual do PIB entre R$ 10 bilhões e R$ 10 trilhões (detecta erro de fator 1000) |
| T16 | Dupla contagem de 2012: soma municipal − total de SC = 4212650 + 4220000 (regra 13) |

- `tests/test_qualidade_regras.py` confere, sem banco, as expectativas usadas por esses testes (por exemplo, os 3.534 pares do T11).
- As demais suítes testam coleta, falhas HTTP, não sobrescrita da RAW, transformação, upsert, aplicador de DDL e permissões dos usuários. As que precisam do banco têm o marcador `integracao`: são puladas quando a porta do banco não aceita conexão e falham quando o servidor recusa a conexão (D17).
- Os testes de classe ALERTA propostos no relatório (zeros, exclusões do T11, saltos nas somas, variações extremas e censo × estimativa) não foram implementados como pytest.

## 7. Ainda não implementado

| Item | Cartão previsto |
|---|---|
| Agente de verificação com o Claude Agent SDK | D28–D29 |
| Camada GOLD (grade completa, regras 12 e 13 na apresentação) | D30 |
| EDA em notebooks | D31–D33 |
| Dashboards Power BI e Streamlit | D34–D37 |
| Comparação dos totais da GOLD com os totais publicados pelo IBGE | critério do D39 (`docs/escopo_mvp.md`) |

## 8. Documentos de referência

| Documento | Conteúdo |
|---|---|
| `CLAUDE.md` | Regras de dados 1–13 |
| `docs/escopo_mvp.md` | Escopo, fora de escopo e critérios de sucesso |
| `docs/decisoes.md` | Decisões D01–D26 |
| `docs/dicionario_dados.md` | Tabelas, colunas, restrições, sinais e cobertura |
| `docs/padrao_coleta.md` | Coleta, RAW, metadados e controle de execução |
| `docs/limitacoes.md` | Limitações dos dados e como o projeto as trata |
| `docs/fontes/` | Investigação de cada fonte, com URLs oficiais |
