-- Painel de todos os anos: uma linha por município e ano, estimativa e Censo em colunas separadas.
SELECT cod_municipio, nome_municipio, cod_regiao_intermediaria, nome_regiao_intermediaria, ano,
       pop_estimada, base_estimativa, pop_censo, pib_corrente_reais, pib_per_capita_reais, aviso
FROM gold.painel_municipio_ano
ORDER BY cod_municipio, ano
