-- R11: Maior PIB per capita, 2023 (docs/dashboards.md, seção 6)
SELECT nome_municipio, pib_per_capita_reais FROM gold.painel_municipio_ano WHERE ano = 2023 ORDER BY pib_per_capita_reais DESC NULLS LAST, cod_municipio LIMIT 1;
