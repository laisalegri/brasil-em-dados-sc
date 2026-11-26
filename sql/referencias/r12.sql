-- R12: PIB per capita 2023: mediana entre os municípios (docs/dashboards.md, seção 6)
SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY pib_per_capita_reais) AS mediana, count(pib_per_capita_reais) AS municipios FROM gold.painel_municipio_ano WHERE ano = 2023;
