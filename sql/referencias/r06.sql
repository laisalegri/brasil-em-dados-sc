-- R06: 3 maiores em população, Censo 2022 (docs/dashboards.md, seção 6)
SELECT nome_municipio, valor, participacao_percentual FROM gold.participacao_estadual WHERE codigo_indicador = 'pop_censo' AND ano = 2022 ORDER BY valor DESC NULLS LAST, cod_municipio LIMIT 3;
