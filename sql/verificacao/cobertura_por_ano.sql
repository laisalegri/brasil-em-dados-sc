-- Municípios com valor por indicador e ano (295 é a cobertura completa; 293 é esperado antes de 2013).
SELECT codigo_indicador, ano,
       count(*) FILTER (WHERE valor IS NOT NULL) AS municipios_com_valor,
       count(*) AS linhas
FROM silver.fato_indicador_municipio
GROUP BY codigo_indicador, ano
ORDER BY codigo_indicador, ano
