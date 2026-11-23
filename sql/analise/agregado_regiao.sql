-- Somas por nível territorial (estado, regiao_intermediaria, regiao_imediata) para um indicador.
SELECT nivel, cod_regiao, nome_regiao, codigo_indicador, tipo_medida, unidade, ano,
       base_estimativa, valor, municipios_somados, municipios_sem_valor, municipios_excluidos, aviso
FROM gold.agregado_regiao_ano
WHERE nivel = :nivel AND codigo_indicador = :indicador
ORDER BY nome_regiao, ano
