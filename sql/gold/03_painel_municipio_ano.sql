-- Painel (D30): uma linha por município e ano, com estimativa e Censo em colunas separadas
-- (regra 2). Nunca há uma coluna "população" que misture os dois.

CREATE VIEW gold.painel_municipio_ano AS
WITH linhas AS (
    SELECT g.cod_municipio,
           g.ano,
           max(g.valor) FILTER (WHERE g.codigo_indicador = 'pop_estimada')   AS pop_estimada,
           max(g.base_estimativa) FILTER (WHERE g.codigo_indicador = 'pop_estimada'
                                          AND g.valor IS NOT NULL)           AS base_estimativa,
           max(g.valor) FILTER (WHERE g.codigo_indicador = 'pop_censo')      AS pop_censo,
           max(g.valor) FILTER (WHERE g.codigo_indicador = 'pib_corrente')   AS pib_corrente_reais,
           max(g.valor) FILTER (WHERE g.codigo_indicador = 'pib_per_capita') AS pib_per_capita_reais,
           max(g.aviso) AS aviso
    FROM gold.grade_indicador_municipio_ano g
    GROUP BY g.cod_municipio, g.ano
)
SELECT l.cod_municipio,
       m.nome_municipio,
       m.cod_regiao_intermediaria,
       m.nome_regiao_intermediaria,
       m.cod_regiao_imediata,
       m.nome_regiao_imediata,
       l.ano,
       l.pop_estimada,
       l.base_estimativa,
       l.pop_censo,
       l.pib_corrente_reais,
       l.pib_per_capita_reais,
       l.aviso
FROM linhas l
JOIN gold.dim_municipio m USING (cod_municipio);

COMMENT ON VIEW gold.painel_municipio_ano IS
    'Uma linha por município e ano (2010–2023). pop_estimada e pop_censo nunca se misturam '
    '(regra 2). PIB nominal em R$ (regra 3); per capita publicado, não é renda (regra 4). '
    'O sinal de origem de cada valor (ex.: 0 vindo de "-") está na grade, não aqui.';
COMMENT ON COLUMN gold.painel_municipio_ano.base_estimativa IS
    'Base da estimativa (regra 12): ate_2012, 2013_2017 (nova projeção; IBGE declara comparáveis '
    'só 2013–2017) ou desde_2018 (revisão da projeção). Não compare valores de bases diferentes '
    'sem aviso.';
