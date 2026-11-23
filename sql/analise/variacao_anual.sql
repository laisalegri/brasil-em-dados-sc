-- Variação ano a ano de um indicador (pop_estimada ou pib_corrente) por município.
SELECT cod_municipio, nome_municipio, codigo_indicador, tipo_medida, ano_anterior, ano,
       valor_anterior, valor, variacao_absoluta, variacao_percentual, comparavel, motivo
FROM gold.variacao_anual
WHERE codigo_indicador = :indicador
ORDER BY cod_municipio, ano
