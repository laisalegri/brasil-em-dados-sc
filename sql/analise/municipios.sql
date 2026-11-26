-- Municípios de SC com as regiões intermediária e imediata e o ano de instalação (dashboards).
SELECT cod_municipio, nome_municipio, cod_regiao_intermediaria, nome_regiao_intermediaria,
       cod_regiao_imediata, nome_regiao_imediata, ano_instalacao
FROM gold.dim_municipio
ORDER BY nome_municipio, cod_municipio
