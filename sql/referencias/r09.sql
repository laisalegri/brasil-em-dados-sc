-- R09: Participação de Itajaí no PIB, 2010 e 2023 (docs/dashboards.md, seção 6)
SELECT ano, participacao_percentual FROM gold.participacao_estadual WHERE cod_municipio = '4208203' AND codigo_indicador = 'pib_corrente' AND ano IN (2010, 2023) ORDER BY ano;
