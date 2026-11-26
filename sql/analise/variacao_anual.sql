-- Variação ano a ano de um indicador (pop_estimada ou pib_corrente) por município, com a base de cada ano (regra 12).
SELECT cod_municipio, nome_municipio, codigo_indicador, tipo_medida, ano_anterior, ano,
       valor_anterior, valor, variacao_absoluta, variacao_percentual, comparavel, motivo,
       base_anterior, base_estimativa
FROM gold.variacao_anual
WHERE codigo_indicador = :indicador
ORDER BY cod_municipio, ano
