-- R01: População de SC, Censo 2022 (docs/dashboards.md, seção 6)
SELECT valor FROM gold.agregado_regiao_ano WHERE nivel = 'estado' AND codigo_indicador = 'pop_censo' AND ano = 2022;
