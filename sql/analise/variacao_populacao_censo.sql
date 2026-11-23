-- Censo 2010 × Censo 2022 por município, com a região intermediária.
SELECT v.cod_municipio, v.nome_municipio, m.cod_regiao_intermediaria, m.nome_regiao_intermediaria,
       v.pop_censo_2010, v.pop_censo_2022, v.variacao_absoluta, v.variacao_percentual, v.motivo
FROM gold.variacao_populacao_censo v
JOIN gold.dim_municipio m USING (cod_municipio)
ORDER BY v.cod_municipio
