-- Pares (indicador, ano) com mais de uma série de origem; o esperado é nenhuma linha.
SELECT codigo_indicador, ano, count(DISTINCT cod_serie) AS series
FROM silver.fato_indicador_municipio
GROUP BY codigo_indicador, ano
HAVING count(DISTINCT cod_serie) > 1
ORDER BY codigo_indicador, ano
