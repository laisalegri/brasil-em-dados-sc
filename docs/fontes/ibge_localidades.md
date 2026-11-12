# API de Localidades do IBGE: municípios de Santa Catarina

- **Data da consulta:** 2026-11-12
- **Recorte:** municípios de Santa Catarina (UF 42)

## URLs consultadas

| # | URL | Uso |
|---|-----|-----|
| A | https://servicodados.ibge.gov.br/api/v1/localidades/estados/42/municipios | Endpoint principal, com a resposta hierárquica |
| B | https://servicodados.ibge.gov.br/api/v1/localidades/estados/42/municipios?view=nivelado | Mesma lista em formato achatado |
| C | https://servicodados.ibge.gov.br/api/v1/localidades/estados/42/municipios?orderBy=nome | Teste da ordenação alfabética |
| D | https://servicodados.ibge.gov.br/api/docs/localidades | Documentação oficial: HTML acessível, com o esquema e os parâmetros |
| E | https://apisidra.ibge.gov.br/values/t/6579/n6/in%20n3%2042/v/9324/p/2011-2021 | Comparação dos códigos com a tabela 6579 (ver `sidra_6579.md`) |

## 1. Estrutura retornada por município (fonte: A)

A resposta é um array JSON, com um objeto por município. A estrutura abaixo foi verificada nos 295 registros: todos têm exatamente o mesmo conjunto de chaves e nenhum campo vem nulo.

```text
id                                   número (inteiro)  código do município (7 dígitos)
nome                                 texto
microrregiao
  id                                 número            ex.: 42009
  nome                               texto
  mesorregiao
    id                               número            ex.: 4203
    nome                             texto
    UF
      id                             número            42
      sigla                          texto             "SC"
      nome                           texto             "Santa Catarina"
      regiao
        id                           número            4
        sigla                        texto             "S"
        nome                         texto             "Sul"
regiao-imediata
  id                                 número            ex.: 420008
  nome                               texto
  regiao-intermediaria
    id                               número            ex.: 4204
    nome                             texto
    UF                               (mesma estrutura de UF acima, com regiao)
```

**Observações:**

- As chaves `regiao-imediata` e `regiao-intermediaria` têm hífen. Em Python, acesse com `m["regiao-imediata"]`, não como atributo.
- O esquema publicado na documentação (D) escreve `"regiao-intermediara"` (sem o "i") dentro de `RegiaoImediata`. A resposta real (A) usa **`regiao-intermediaria`**. Confie na resposta, não no esquema.
- A UF aparece duas vezes por município, pelas duas hierarquias. Em todos os 295 registros as duas vêm com `id` 42.

### Formato nivelado (fonte: B)

Com `?view=nivelado`, cada município vira um objeto plano com 16 campos:

| Campo | Tipo |
|-------|------|
| `municipio-id` | número |
| `municipio-nome` | texto |
| `microrregiao-id` | número |
| `microrregiao-nome` | texto |
| `mesorregiao-id` | número |
| `mesorregiao-nome` | texto |
| `regiao-imediata-id` | número |
| `regiao-imediata-nome` | texto |
| `regiao-intermediaria-id` | número |
| `regiao-intermediaria-nome` | texto |
| `UF-id` | número |
| `UF-sigla` | texto |
| `UF-nome` | texto |
| `regiao-id` | número |
| `regiao-sigla` | texto |
| `regiao-nome` | texto |

O formato nivelado trouxe 295 registros, sem nulos e com 295 `municipio-id` distintos.

## 2. Código do município (fonte: A)

- **Tipo no JSON:** `id` vem como **número** (inteiro), não como texto.
- **Dígitos:** todos os 295 têm 7 dígitos.
- **Prefixo:** todos começam com `42`.
- **Unicidade:** 295 valores distintos, sem duplicados.
- **Ordenação padrão:** por `id` crescente, confirmado na resposta e descrito na documentação (D).

> Regra do projeto: na carga, o código deve ser convertido para **texto de 7 dígitos** (por exemplo, `str(id)`) e usado como chave em todas as camadas. O formato de 7 dígitos já vem completo, sem zeros à esquerda a recuperar, porque os códigos de SC começam com 42.

## 3. Total de municípios e comparação com a tabela 6579

- **Total em A:** **295** municípios.
- **Comparação com a tabela 6579 (E):** o conjunto de códigos de A, convertidos para texto, é **idêntico** ao conjunto de `D1C` da consulta da tabela 6579 para 2011–2021. Os 295 códigos são os mesmos, sem faltas nem sobras (ver também `sidra_6579.md`, seção 6).

## 4. Hierarquia regional em SC (fonte: A)

| Divisão | Quantidade distinta em SC |
|---------|---------------------------|
| Microrregiões | 20 |
| Mesorregiões | 6 |
| Regiões geográficas imediatas | 24 |
| Regiões geográficas intermediárias | 7 |

**Mesorregiões:**

| id | Nome |
|----|------|
| 4201 | Oeste Catarinense |
| 4202 | Norte Catarinense |
| 4203 | Serrana |
| 4204 | Vale do Itajaí |
| 4205 | Grande Florianópolis |
| 4206 | Sul Catarinense |

**Regiões intermediárias:**

| id | Nome |
|----|------|
| 4201 | Florianópolis |
| 4202 | Criciúma |
| 4203 | Lages |
| 4204 | Chapecó |
| 4205 | Caçador |
| 4206 | Joinville |
| 4207 | Blumenau |

> **Atenção:** os `id` de mesorregião e de região intermediária usam a **mesma faixa numérica** (4201, 4202...), mas são entidades diferentes. Por exemplo, mesorregião 4201 é "Oeste Catarinense" e região intermediária 4201 é "Florianópolis". Nunca junte as duas divisões pelo `id` sem saber de qual hierarquia ele vem.

### Origem das duas divisões (fonte: D, texto introdutório)

- **Meso e microrregiões:** a documentação diz que foram "institucionalizadas pela aprovação da presidência do IBGE da resolução PR nº 51/1989 e pela publicação Divisão regional do Brasil em mesorregiões e microrregiões geográficas".
- **Regiões imediatas e intermediárias:** "decorrem da revisão das microrregiões e mesorregiões" e "passam a substituir as mesorregiões e microrregiões geográficas de forma progressiva até 21/12/2023".
- O **ano de 2017** para a divisão em regiões imediatas e intermediárias **não aparece** nesse texto. Ver "Inferido / não confirmado".

## 5. Nomes de municípios (fonte: A)

- **Nomes distintos:** 295, sem homônimos dentro de SC.
- **Acentos:** 110 nomes têm caracteres não ASCII.
- **Apóstrofo:** 1 nome, "Herval d'Oeste" (4206702), com o apóstrofo reto `'`.
- **Hífen:** 1 nome, "Grão-Pará" (4206108).
- **Espaços:** nenhum nome tem espaço no início, no fim ou duplicado.
- **Nomes de regiões imediatas** também podem ter hífen e apóstrofo, por exemplo "Joaçaba - Herval d'Oeste".
- **Municípios recentes presentes:** Pescaria Brava (4212650) e Balneário Rincão (4220000) estão em A.
- **Florianópolis (4205407)** também está presente.

O nome nesta API não traz o sufixo de UF. Já o SIDRA devolve "Florianópolis (SC)" ou "Abdon Batista - SC", conforme o filtro (ver `sidra_6579.md`). Isso reforça que **nome nunca é chave**: a junção entre fontes é sempre pelo código de 7 dígitos.

## 6. Parâmetros do endpoint (fonte: D; testados em B e C)

- **`{UF}` (caminho):** "Um ou mais identificadores de Unidades da Federação delimitados pelo caracter | (pipe)", por exemplo `estados/33|35/municipios`.
- **`orderBy` (query):** "Por padrão, os muncípios são ordenados pela propriedade **id**... Se desejar ordenar alfabeticamente pelo nome do município, use o parâmetro **orderBy** com o valor **nome**". O teste C devolveu 295 registros em ordem alfabética.
- **`view` (query):** "Por padrão, a resposta JSON é configurada para refletir a hierarquia à qual pertencem as localidades. A outra opção é configurar o parâmetro **view** com o valor **nivelado**...". O teste B devolveu o formato plano descrito acima.

## 7. Amostra para testes

- **Arquivo:** `tests/fixtures/localidades_sc_amostra.json`
- **Origem:** recortada da resposta de https://servicodados.ibge.gov.br/api/v1/localidades/estados/42/municipios, consultada em 2026-11-12.
- **Conteúdo:** 5 objetos completos, com a estrutura aninhada e os valores sem alteração e o `id` como número.
- **Formato:** UTF-8, com indentação de 2 espaços.
- **Reserialização:** os objetos foram reserializados com `json.dump(..., ensure_ascii=False, indent=2)`. A releitura do arquivo foi conferida como igual aos objetos originais.

| id | nome | Por que está na amostra |
|----|------|-------------------------|
| 4205407 | Florianópolis | Capital, com acento |
| 4212650 | Pescaria Brava | Instalado depois de 2010 |
| 4220000 | Balneário Rincão | Instalado depois de 2010, com acento |
| 4206702 | Herval d'Oeste | Apóstrofo no nome |
| 4206108 | Grão-Pará | Hífen e acentos no nome |

## Verificado diretamente

- A estrutura aninhada e os tipos de todos os campos, nos 295 registros, sem campos nulos e com o mesmo conjunto de chaves em todos (A).
- O `id` vem como inteiro, com 7 dígitos, começa com 42 e é único (A).
- O total de 295 municípios, e a igualdade do conjunto de códigos com a tabela 6579 em 2011–2021 (A, E).
- As contagens 20 micro, 6 meso, 24 imediatas e 7 intermediárias, com a sobreposição numérica dos ids de meso e intermediária (A).
- Os nomes com apóstrofo e hífen, a contagem de nomes acentuados e a presença de 4212650 e 4220000 (A).
- Os parâmetros `UF` com pipe, `orderBy=nome` e `view=nivelado`, descritos em D e testados em B e C. A ordenação padrão por `id` também foi confirmada.
- O texto da documentação sobre a origem das divisões (resolução PR nº 51/1989; substituição progressiva até 21/12/2023) (D).
- A divergência de nome de chave entre o esquema da documentação (`regiao-intermediara`) e a resposta real (`regiao-intermediaria`) (D, A).

## Inferido / não confirmado

- **Ano da divisão de 2017.** Que as regiões imediatas e intermediárias sejam a divisão de **2017** é conhecimento geral sobre o IBGE. A documentação lida (D) não cita o ano, só que elas "decorrem da revisão". **NÃO CONFIRMADO** nesta fonte.
- **"1989/1990" para meso e micro.** A documentação cita a resolução de 1989. O ano de 1990 da publicação não aparece no texto lido. **NÃO CONFIRMADO**.
- **Recorte temporal.** A API retorna o recorte territorial vigente na data da consulta, e não o de cada ano de 2010 a 2023. É inferência: a documentação lida não fala de versão por data. Para o projeto, isso significa que o cadastro tem 295 municípios mesmo nos anos em que Pescaria Brava e Balneário Rincão ainda não existiam.
- **Estabilidade da hierarquia.** Se a composição das regiões imediatas e intermediárias mudou desde a publicação ("serão periodicamente revisadas", segundo D) é **NÃO CONFIRMADO**.

## Pendências

- Confirmar o ano oficial da divisão em regiões imediatas e intermediárias na publicação do IBGE citada em D ("Divisão regional do Brasil em regiões geográficas imediatas e regiões geográficas intermediárias"), que não foi lida.
- Decidir (autora, em `docs/decisoes.md`) qual hierarquia regional usar nas análises e dashboards: meso/micro, imediata/intermediária ou ambas.
