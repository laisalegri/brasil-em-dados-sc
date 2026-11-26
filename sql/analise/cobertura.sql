-- Quantidade de linhas da grade por indicador e status (com_valor, municipio_nao_instalado, sem_dado).
SELECT codigo_indicador, status, count(*) AS linhas
FROM gold.grade_indicador_municipio_ano
GROUP BY codigo_indicador, status
ORDER BY codigo_indicador, status
