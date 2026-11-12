# SIDRA 1378: População residente (Censo Demográfico 2010)

- **Data da consulta:** 2026-11-12
- **Recorte:** municípios de Santa Catarina (UF 42), ano 2010

## URLs consultadas

| # | URL | Uso |
|---|-----|-----|
| A | https://servicodados.ibge.gov.br/api/v3/agregados/1378/metadados | Metadados: nome, pesquisa, níveis, variáveis e classificações |
| B | https://servicodados.ibge.gov.br/api/v3/agregados/1378/periodos | Períodos disponíveis |
| C | https://apisidra.ibge.gov.br/values/t/1378/n6/in%20n3%2042/v/93/p/2010/c1/0/c2/0/c287/0/c455/0 | Todos os municípios de SC, com todos os filtros de total explícitos (**URL final**) |
| D | https://apisidra.ibge.gov.br/values/t/1378/n6/in%20n3%2042/v/93/p/2010 | Mesma consulta, sem os filtros de classificação |
| E | https://apisidra.ibge.gov.br/values/t/1378/n6/4205407/v/93/p/2010 | Florianópolis, sem os filtros de classificação |
| F | https://apisidra.ibge.gov.br/values/t/1378/n6/4212650,4220000,4205407/v/93/p/2010/c1/0/c2/0/c287/0/c455/0 | Municípios instalados em 2013, consultados pelo código |
| G | https://apisidra.ibge.gov.br/values/t/6579/n6/in%20n3%2042/v/9324/p/2011-2021 | Estimativas 2011 e 2021, para a checagem de coerência |
| H | https://servicodados.ibge.gov.br/api/v1/localidades/estados/42/municipios | Cadastro de 295 municípios (ver `ibge_localidades.md`) |
| I | https://sidra.ibge.gov.br/tabela/1378 | **Não consultada.** As notas do SIDRA web caem no bloqueio Cloudflare (ver `sidra_convencoes.md`). |

## 1. Tabela e pesquisa (fonte: A)

- **Id:** 1378
- **Nome:** "População residente, por situação do domicílio, sexo e idade, segundo a condição no domicílio e compartilhamento da responsabilidade pelo domicílio"
- **Pesquisa:** "Censo Demográfico"
- **Assunto:** "Pessoas"
- **Periodicidade:** anual, com `inicio` 2010 e `fim` 2010

## 2. Variáveis (fonte: A; MC confirmado em C)

| id | nome | unidade | Observação |
|----|------|---------|------------|
| **93** | **População residente** | **Pessoas** (MC=45) | Variável a usar |
| 1000093 | População residente - percentual do total geral | % | Não usar |

## 3. Períodos (fonte: B)

| Período | Data de modificação |
|---------|---------------------|
| 2010 | 01/02/2019 |

É o único período da tabela.

## 4. Níveis territoriais (fonte: A)

- **Administrativo:** N15, N102, N1, N10, N2, N8, N9, **N6**, N14, N7, N13, N11, N3
- **Especial:** N23
- **IBGE:** nenhum

O nível municipal (N6) existe. Os demais níveis não são usados no projeto e não foram detalhados.

## 5. Classificações e categoria de total (fonte: A)

| Classificação | id | Nº de categorias | Categoria de total | Filtro na URL |
|---------------|----|------------------|--------------------|---------------|
| Situação do domicílio | 1 | 3 (Total, Urbana, Rural) | `0` "Total" (nível 0) | `c1/0` |
| Sexo | 2 | 3 (Total, Homens, Mulheres) | `0` "Total" (nível 0) | `c2/0` |
| Idade | 287 | 135 | `0` "Total" (nível 0) | `c287/0` |
| Condição no domicílio e o compartilhamento da responsabilidade pelo domicílio | 455 | 25 | `0` "Total" (nível 0) | `c455/0` |

**Na prática (C):** cada linha veio com `D4C`, `D5C`, `D6C` e `D7C` = `0` ("Total"), e houve uma linha por município.

## 6. Contagem de municípios de SC (fontes: C, D, F, H)

| Consulta | Linhas | Valores numéricos | Sinais | Códigos ausentes em relação a H |
|----------|--------|-------------------|--------|---------------------------------|
| C (com totais explícitos) | **293** | 293 | 0 | 4212650, 4220000 |
| D (sem filtros de classificação) | 293 | 293 | 0 | 4212650, 4220000 |

- Não há códigos a mais em relação a H, e não há códigos duplicados.
- A consulta D, sem filtros, também devolveu só os totais (`D4C` a `D7C` = 0). E também devolveu uma linha só para Florianópolis. Mesmo assim, a URL final deixa os filtros explícitos, para não depender do comportamento padrão.

### Pescaria Brava e Balneário Rincão em 2010

| Código | Município | Na consulta por UF (C) | Na consulta pelo código (F) |
|--------|-----------|------------------------|-----------------------------|
| 4212650 | Pescaria Brava | **linha ausente** | linha presente, `V` = `...` |
| 4220000 | Balneário Rincão | **linha ausente** | linha presente, `V` = `...` |

**Comportamento importante para o extrator:** com o filtro `in n3 42`, os dois municípios **não aparecem**. Consultados pelo código, aparecem com o sinal `...` ("Valor não disponível", ver `sidra_convencoes.md`).

Para o pipeline, dá no mesmo: a população de Censo 2010 desses municípios é `NULL`. Se a linha vier da consulta por código, `sinal_origem` = `...`. Se vier da consulta por UF, a linha simplesmente não existe e a ausência é esperada (regra 6 do CLAUDE.md).

## 7. Sinais SIDRA encontrados

Na URL final (C), **nenhum** sinal aparece: os 293 valores são numéricos. O único sinal visto nesta tabela foi `...`, na consulta F, para os dois municípios acima.

| Sinal | Onde | Carga (regra 9 do CLAUDE.md e `sidra_convencoes.md`) |
|-------|------|------------------------------------------------------|
| `...` | F: 4212650 e 4220000 | Valor `NULL`, `sinal_origem` = `...` |

## 8. Checagem de coerência (ordem de grandeza)

Censo 2010 (1378, consulta C) comparado com a estimativa 2011 (6579, consulta G). A diferença percentual serve **só como conferência** de ordem de grandeza, e não deve ser lida como crescimento nem como erro de estimativa. Censo e estimativa são medidas diferentes, com datas de referência diferentes: a estimativa se refere a 1º de julho (ver `sidra_convencoes.md`).

| Código | Município | Censo 2010 (1378) | Estimativa 2011 (6579) | Diferença % |
|--------|-----------|-------------------|------------------------|-------------|
| 4205407 | Florianópolis | 421240 | 427298 | +1,44% |
| 4209102 | Joinville | 515288 | 520905 | +1,09% |
| 4204202 | Chapecó | 183530 | 186337 | +1,53% |
| 4206702 | Herval d'Oeste | 21239 | 21331 | +0,43% |
| 4200051 | Abdon Batista | 2653 | 2644 | −0,34% |

Os valores estão na mesma ordem de grandeza. A comparação estimativa 2021 × Censo 2022 está em `sidra_4709.md`, seção 8.

## 9. Formato da resposta (fonte: C)

- **Campos:** `NC`, `NN`, `MC`, `MN`, `V`, `D1C`, `D1N`, `D2C`, `D2N`, `D3C`, `D3N`, `D4C`, `D4N`, `D5C`, `D5N`, `D6C`, `D6N`, `D7C`, `D7N`
  - `D4` a `D7` são as 4 classificações, na ordem 1, 2, 287 e 455.
- **Nome do município:** vem como "Abdon Batista - SC" no filtro por UF e como "Florianópolis (SC)" no filtro por código, o mesmo comportamento da 6579. A chave é sempre `D1C`.

## URL final para o extrator

```
https://apisidra.ibge.gov.br/values/t/1378/n6/in%20n3%2042/v/93/p/2010/c1/0/c2/0/c287/0/c455/0
```

Testada em 2026-11-12. Devolveu **293 linhas de dados**, mais o cabeçalho. Todas são numéricas, com unidade "Pessoas" e as classificações em "Total". Ficam ausentes 4212650 e 4220000.

## Verificado diretamente

- Nome, pesquisa, assunto e periodicidade da tabela; níveis com N6; variáveis 93 e 1000093 com nome e unidade (A).
- Período único 2010, modificado em 01/02/2019 (B).
- As 4 classificações, com ids 1, 2, 287 e 455, e a categoria `0` "Total" em cada uma (A). Os totais aplicados devolvem uma linha por município (C).
- 293 linhas por UF, todas numéricas, com 4212650 e 4220000 ausentes (C, D, H).
- Os dois municípios aparecem com `...` quando consultados pelo código (F).
- Os valores da tabela de coerência (C, G).

- **Data de referência do Censo 2010** (confirmada em 2026-11-12): **noite de 31 de julho para 1º de agosto de 2010**.
  - Documento: *Metodologia do Censo Demográfico 2010* (IBGE, Série Relatórios Metodológicos, v. 41, 2013), seção 1.3 "Periodicidade e data de referência", p. 44 impressa (p. 45 do PDF).
  - Citação literal: "A investigação das características dos domicílios e das pessoas neles residentes teve como data de referência deste Censo Demográfico a noite de 31 de julho para 1º de agosto de 2010."
  - URL: https://ftp.ibge.gov.br/Censos/Censo_Demografico_2010/metodologia/metodologia_censo_dem_2010.pdf
  - A mesma publicação diz que "A coleta dos dados iniciou em 1º de agosto de 2010".

## Inferido / não confirmado

- **Ausência no filtro por UF.** Que os dois municípios sumam do filtro `in n3 42` porque o SIDRA omite unidades territoriais sem valor nesse tipo de filtro é **inferência**. Não li documentação que descreva esse comportamento.
- **Revisões.** O motivo da modificação em 01/02/2019 é **NÃO CONFIRMADO**: não li as notas da tabela.
- **Notas da tabela.** As notas metodológicas e de rodapé da tabela 1378 **não foram lidas**. O SIDRA web está bloqueado por Cloudflare, e não tentei contornar.

## Pendências

- Ler as notas da tabela em https://sidra.ibge.gov.br/tabela/1378, pelo navegador.
- Decidir (autora) se o extrator deve consultar 4212650 e 4220000 pelo código, para registrar o `...` em `sinal_origem`, ou aceitar a ausência da linha.
