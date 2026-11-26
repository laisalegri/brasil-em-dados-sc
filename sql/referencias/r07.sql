-- R07: 3 maiores em PIB nominal, 2023 (docs/dashboards.md, seção 6)
SELECT nome_municipio, valor, participacao_percentual FROM gold.participacao_estadual WHERE codigo_indicador = 'pib_corrente' AND ano = 2023 ORDER BY valor DESC NULLS LAST, cod_municipio LIMIT 3;
