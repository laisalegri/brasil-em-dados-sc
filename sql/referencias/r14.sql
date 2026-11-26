-- R14: Variação da estimativa 2012→2013 (regra 12) (docs/dashboards.md, seção 6)
SELECT count(*) AS pares, count(variacao_percentual) AS com_variacao, bool_or(comparavel) AS algum_comparavel FROM gold.variacao_anual WHERE codigo_indicador = 'pop_estimada' AND ano = 2013;
