-- Painel de um ano: uma linha por município, estimativa e Censo em colunas separadas (regra 2).
SELECT cod_municipio, nome_municipio, cod_regiao_intermediaria, nome_regiao_intermediaria, ano,
       pop_estimada, base_estimativa, pop_censo, pib_corrente_reais, pib_per_capita_reais, aviso
FROM gold.painel_municipio_ano
WHERE ano = :ano
ORDER BY cod_municipio
