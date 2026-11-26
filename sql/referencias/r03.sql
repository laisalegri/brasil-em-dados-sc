-- R03: PIB nominal de SC, 2023 (docs/dashboards.md, seção 6)
SELECT valor FROM gold.agregado_regiao_ano WHERE nivel = 'estado' AND codigo_indicador = 'pib_corrente' AND ano = 2023;
