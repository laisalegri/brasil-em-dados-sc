# SIDRA 4709: População residente (Censo Demográfico 2022)

- **Data da consulta:** 2026-11-12
- **Recorte:** municípios de Santa Catarina (UF 42), ano 2022

## URLs consultadas

| # | URL | Uso |
|---|-----|-----|
| A | https://servicodados.ibge.gov.br/api/v3/agregados/4709/metadados | Metadados: nome, pesquisa, níveis, variáveis e classificações |
| B | https://servicodados.ibge.gov.br/api/v3/agregados/4709/periodos | Períodos disponíveis |
| C | https://apisidra.ibge.gov.br/values/t/4709/n6/in%20n3%2042/v/93/p/2022 | Todos os municípios de SC (**URL final**) |
| D | https://apisidra.ibge.gov.br/values/t/4709/n6/4212650,4220000/v/93/p/2022 | Municípios instalados em 2013 |
| E | https://apisidra.ibge.gov.br/values/t/6579/n6/in%20n3%2042/v/9324/p/2011-2021 | Estimativa 2021, para a checagem de coerência |
| F | https://servicodados.ibge.gov.br/api/v1/localidades/estados/42/municipios | Cadastro de 295 municípios |
| G | https://sidra.ibge.gov.br/Ajax/JSon/Tabela/1/4709?versao=-1 | Notas da tabela: devolveu o **desafio Cloudflare** ("Just a moment..."). Não tentei contornar. |
| H | https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Populacao_e_domicilios_Primeiros_resultados/ | Listagem oficial das publicações dos primeiros resultados |
| I | https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Populacao_e_domicilios_Primeiros_resultados/Tabelas_completas_de_resultados_20231027.txt | Aviso de atualização |
| J | https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Populacao_e_domicilios_Primeiros_resultados/Resultados_da_2a_apuracao_20231027/ | Arquivos da 2ª apuração |
| K | https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Populacao_e_domicilios_Primeiros_resultados/Resultados_da_2a_apuracao_20231027/POP2022_Municipios_Primeiros_Resultados_20231222.pdf | PDF oficial de população por município. Texto extraído com `pdftotext`. |

## 1. Tabela e pesquisa (fonte: A)

- **Id:** 4709
- **Nome:** "População residente, Variação absoluta de população residente e Taxa de crescimento geométrico"
- **Pesquisa:** "Censo Demográfico"
- **Assunto:** "Pessoas"
- **Periodicidade:** anual, com `inicio` 2022 e `fim` 2022

## 2. Variáveis (fonte: A; MC confirmado em C)

| id | nome | unidade | Observação |
|----|------|---------|------------|
| **93** | **População residente** | **Pessoas** (MC=45) | Variável a usar |
| 5936 | Variação absoluta da população residente 2010 compatibilizada | Pessoas | Não usar no MVP |
| 10605 | Taxa de crescimento geométrico | % | Não usar no MVP |

## 3. Períodos (fonte: B)

| Período | Data de modificação |
|---------|---------------------|
| 2022 | **22/12/2023** |

É o único período da tabela.

## 4. Níveis territoriais (fonte: A)

- **Administrativo:** N1, N2, **N6**, N3
- **Especial:** nenhum
- **IBGE:** nenhum

## 5. Classificações (fonte: A)

A tabela não tem classificações: `"classificacoes": []`. A URL final não precisa de filtro de total.

## 6. Contagem de municípios de SC (fontes: C, D, F)

| Consulta | Linhas | Valores numéricos | Sinais | Códigos ausentes em relação a F | Códigos extras |
|----------|--------|-------------------|--------|---------------------------------|----------------|
| C | **295** | 295 | 0 | nenhum | nenhum |

Os 295 códigos de C são idênticos aos da API de Localidades (ver `ibge_localidades.md`).

### Pescaria Brava e Balneário Rincão em 2022 (fonte: D)

| Código | Município | V |
|--------|-----------|---|
| 4212650 | Pescaria Brava | 10190 |
| 4220000 | Balneário Rincão | 15981 |

Os dois têm valor numérico, em "Pessoas". Os mesmos números aparecem no texto extraído do PDF oficial (K).

## 7. Sinais SIDRA encontrados

**Nenhum** sinal na URL final (C): os 295 valores são numéricos, então `sinal_origem` fica `NULL` em todas as linhas (regra 9 do CLAUDE.md).

## 8. Checagem de coerência (ordem de grandeza)

A diferença percentual serve **só como conferência** de ordem de grandeza, e não deve ser lida como crescimento nem como erro de estimativa. Estimativa e Censo são medidas diferentes, com datas de referência diferentes: a estimativa se refere a 1º de julho.

### Estimativa 2021 (6579) × Censo 2022 (4709)

Fontes: E e C.

| Código | Município | Estimativa 2021 (6579) | Censo 2022 (4709) | Diferença % |
|--------|-----------|------------------------|-------------------|-------------|
| 4205407 | Florianópolis | 516524 | 537211 | +4,01% |
| 4209102 | Joinville | 604708 | 616317 | +1,92% |
| 4204202 | Chapecó | 227587 | 254785 | +11,95% |
| 4206702 | Herval d'Oeste | 22820 | 21724 | −4,80% |
| 4200051 | Abdon Batista | 2534 | 2598 | +2,53% |

### Censo 2010 (1378) × Estimativa 2011 (6579)

Resumo da tabela completa em `sidra_1378.md`, seção 8.

| Município | Diferença % |
|-----------|-------------|
| Florianópolis | +1,44% |
| Joinville | +1,09% |
| Chapecó | +1,53% |
| Herval d'Oeste | +0,43% |
| Abdon Batista | −0,34% |

Todos os valores estão na mesma ordem de grandeza. As diferenças entre 2021 e 2022 são maiores que as de 2010 a 2011, e é só isso que se registra aqui.

## 9. Revisão e republicação dos resultados de 2022

- **API de Agregados (B):** o período 2022 foi modificado em **22/12/2023**.
- **FTP oficial (H):** a pasta dos primeiros resultados tem as subpastas:
  - `Historico_dos_resultados_da_1a_apuracao_20230628/`
  - `Resultados_da_2a_apuracao_20231027/`, com data de modificação 2023-12-22 09:42
- **Aviso oficial (I):** "As tabelas de resultados atualizadas em 27/10/2023 podem ser acessadas em: https://www.ibge.gov.br/estatisticas/sociais/trabalho/22827-censo-demografico-2022.html?edicao=37225&t=resultados"
- **Arquivos da 2ª apuração (J),** todos datados de 20231222:
  - `POP2022_Municipios_Primeiros_Resultados_20231222.pdf`
  - `CD2022_Populacao_Coletada_Imputada_e_Total_Municipio_e_UF_20231222` (.ods/.xlsx)
  - `CD2022_Populacao_2010_Compatibilizada_20231222` (.ods/.xlsx)
- **PDF oficial (K):** o título é "Primeiros Resultados de População do Censo Demográfico 2022 (22 de dezembro de 2023)".
  - As 29 notas são de população judicial; nenhuma cita município de SC.
  - No texto extraído aparecem os mesmos valores do SIDRA para Florianópolis (537.211), Chapecó (254.785), Pescaria Brava (10.190) e Balneário Rincão (15.981).

## URL final para o extrator

```
https://apisidra.ibge.gov.br/values/t/4709/n6/in%20n3%2042/v/93/p/2022
```

Testada em 2026-11-12. Devolveu **295 linhas de dados**, mais o cabeçalho. Todas são numéricas, com unidade "Pessoas". Os campos são `NC`, `NN`, `MC`, `MN`, `V`, `D1C`, `D1N`, `D2C`, `D2N`, `D3C`, `D3N`. Não há filtros de classificação, porque a tabela não tem classificações.

## Verificado diretamente

- Nome, pesquisa, assunto e periodicidade da tabela; níveis com N6; variáveis 93, 5936 e 10605 com nome e unidade; `classificacoes: []` (A).
- Período único 2022, modificado em 22/12/2023 (B).
- 295 linhas numéricas, com códigos idênticos aos da API de Localidades (C, F).
- Valores de Pescaria Brava (10190) e Balneário Rincão (15981) (D), que coincidem com o texto do PDF oficial (K).
- Existência de uma 1ª apuração (pasta datada de 20230628) e de uma 2ª apuração (pasta de 20231027, arquivos de 20231222), além do texto do aviso de atualização (H, I, J).
- As notas do PDF oficial são todas de população judicial, sem SC (K).
- As notas do SIDRA web caem no bloqueio Cloudflare (G).

## Inferido / não confirmado

- **Origem dos valores.** Que os valores da tabela 4709 sejam os da 2ª apuração, republicada em 22/12/2023, é **inferência forte**: a data de modificação do período coincide com a dos arquivos, e alguns valores coincidem com o PDF de 22/12/2023. Não comparei com a 1ª apuração.
- **O que mudou entre as apurações.** O que mudou da 1ª apuração (28/06/2023) para a 2ª (27/10/2023 e 22/12/2023), e se municípios de SC foram afetados, é **NÃO CONFIRMADO**. A página do IBGE citada no aviso (I) não foi lida, e www.ibge.gov.br retornou 403 em tarefa anterior.
- **Data de referência do Censo 2022.** A data de referência (noite de 31/07 para 1º/08/2022, segundo conhecimento geral) é **NÃO CONFIRMADA** nas fontes lidas.
- **Variável 5936.** O significado de "2010 compatibilizada" (população de 2010 recalculada na malha de 2022, o que poderia cobrir municípios instalados em 2013) é **inferência** a partir do nome. Não foi investigado nem faz parte do MVP.

## Pendências

- Ler as notas da tabela em https://sidra.ibge.gov.br/tabela/4709, pelo navegador.
- Ler a página de resultados citada em I e confirmar o que mudou entre as apurações.
- Confirmar a data de referência do Censo 2022 em fonte oficial.
