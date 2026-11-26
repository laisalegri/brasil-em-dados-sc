-- Participação de cada município no total de SC, em todos os anos de um indicador.
SELECT cod_municipio, nome_municipio, codigo_indicador, tipo_medida, ano, base_estimativa,
       valor, total_estado, participacao_percentual, aviso
FROM gold.participacao_estadual
WHERE codigo_indicador = :indicador
ORDER BY cod_municipio, ano
