-- Valores NULL fora da exceção da regra 10 (4212650 e 4220000 antes de 2013); o esperado é nenhuma linha.
SELECT cod_municipio, codigo_indicador, ano, sinal_origem, cod_serie
FROM silver.fato_indicador_municipio
WHERE valor IS NULL
  AND NOT (cod_municipio IN ('4212650', '4220000') AND ano < 2013)
ORDER BY codigo_indicador, ano, cod_municipio
