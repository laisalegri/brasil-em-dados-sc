-- Quantidade de valores negativos por indicador; o esperado é nenhuma linha.
SELECT codigo_indicador, count(*) AS negativos
FROM silver.fato_indicador_municipio
WHERE valor < 0
GROUP BY codigo_indicador
ORDER BY codigo_indicador
