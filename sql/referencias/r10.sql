-- R10: Municípios comparáveis e que perderam população entre os Censos (docs/dashboards.md, seção 6)
SELECT count(variacao_percentual) AS comparaveis, count(*) FILTER (WHERE variacao_absoluta < 0) AS perderam FROM gold.variacao_populacao_censo;
