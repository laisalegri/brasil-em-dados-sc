-- Somas por estado, região intermediária e região imediata (D30). Sem per capita agregado
-- (regra 4). Em pop_estimada 2012, os municípios ainda não instalados ficam fora (regra 13).

CREATE VIEW gold.agregado_regiao_ano AS
WITH base AS (
    SELECT g.codigo_indicador, g.ano, g.valor, g.unidade, g.tipo_medida, g.base_estimativa,
           (g.aviso IS NOT NULL) AS excluido,
           m.cod_uf, m.cod_regiao_intermediaria, m.nome_regiao_intermediaria,
           m.cod_regiao_imediata, m.nome_regiao_imediata
    FROM gold.grade_indicador_municipio_ano g
    JOIN gold.dim_municipio m USING (cod_municipio)
    WHERE g.codigo_indicador IN ('pop_estimada', 'pop_censo', 'pib_corrente')
),
niveis AS (
    SELECT 'estado' AS nivel, cod_uf AS cod_regiao, 'Santa Catarina' AS nome_regiao,
           codigo_indicador, ano, valor, unidade, tipo_medida, base_estimativa, excluido
    FROM base
    UNION ALL
    SELECT 'regiao_intermediaria', cod_regiao_intermediaria, nome_regiao_intermediaria,
           codigo_indicador, ano, valor, unidade, tipo_medida, base_estimativa, excluido
    FROM base
    UNION ALL
    SELECT 'regiao_imediata', cod_regiao_imediata, nome_regiao_imediata,
           codigo_indicador, ano, valor, unidade, tipo_medida, base_estimativa, excluido
    FROM base
)
SELECT nivel,
       cod_regiao,
       nome_regiao,
       codigo_indicador,
       tipo_medida,
       unidade,
       ano,
       base_estimativa,
       sum(valor) FILTER (WHERE NOT excluido) AS valor,
       count(*) FILTER (WHERE valor IS NOT NULL AND NOT excluido) AS municipios_somados,
       count(*) FILTER (WHERE valor IS NULL) AS municipios_sem_valor,
       count(*) FILTER (WHERE excluido) AS municipios_excluidos,
       CASE WHEN bool_or(excluido)
            THEN 'pop_estimada 2012 sem 4212650 e 4220000: dupla contagem com o município de '
                 'origem (regra 13)'
       END AS aviso
FROM niveis
GROUP BY nivel, cod_regiao, nome_regiao, codigo_indicador, tipo_medida, unidade, ano,
         base_estimativa;

COMMENT ON VIEW gold.agregado_regiao_ano IS
    'Somas por estado, região intermediária e imediata. Sem per capita agregado (regra 4). '
    'pop_estimada 2012 exclui 4212650 e 4220000 (regra 13; os dois estão na mesma região do '
    'município de origem). PIB nominal (regra 3). Soma de quem tem valor: confira '
    'municipios_sem_valor (hoje só os municípios não instalados ficam sem valor).';
