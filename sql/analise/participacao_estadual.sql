-- Participação de cada município no total de SC para um indicador e um ano (maior primeiro).
SELECT cod_municipio, nome_municipio, codigo_indicador, tipo_medida, ano, base_estimativa,
       valor, total_estado, participacao_percentual, aviso
FROM gold.participacao_estadual
WHERE codigo_indicador = :indicador AND ano = :ano
ORDER BY valor DESC NULLS LAST, cod_municipio
