-- Linhas, anos, municípios, nulos e zeros por indicador na fato (SILVER).
SELECT codigo_indicador,
       count(*) AS linhas,
       min(ano) AS ano_min,
       max(ano) AS ano_max,
       count(DISTINCT cod_municipio) AS municipios,
       count(*) FILTER (WHERE valor IS NULL) AS nulos,
       count(*) FILTER (WHERE valor = 0) AS zeros
FROM silver.fato_indicador_municipio
GROUP BY codigo_indicador
ORDER BY codigo_indicador
