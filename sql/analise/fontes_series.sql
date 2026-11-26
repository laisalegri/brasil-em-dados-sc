-- Uma linha por série de origem: fonte, indicador, unidade, anos cobertos e última coleta.
SELECT cod_serie, fonte, codigo_indicador, tipo_medida, unidade,
       min(ano) AS ano_inicial, max(ano) AS ano_final, max(data_coleta) AS ultima_coleta
FROM gold.grade_indicador_municipio_ano
GROUP BY cod_serie, fonte, codigo_indicador, tipo_medida, unidade
ORDER BY codigo_indicador, cod_serie
