-- R05: Estimativa de SC, 2012 (regra 13) (docs/dashboards.md, seção 6)
SELECT valor, municipios_somados, municipios_excluidos FROM gold.agregado_regiao_ano WHERE nivel = 'estado' AND codigo_indicador = 'pop_estimada' AND ano = 2012;
