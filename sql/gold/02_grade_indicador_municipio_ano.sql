-- Grade completa (D30): 295 municípios × anos publicados de cada indicador × indicador.

CREATE VIEW gold.grade_indicador_municipio_ano AS
WITH anos AS (
    -- Anos publicados por indicador, com a série de origem. Uma série por (indicador, ano) é
    -- garantida pelo teste de qualidade T3; a junção abaixo também usa cod_serie, então uma
    -- segunda série num mesmo ano apareceria como chave repetida (testado), não como valor
    -- trocado. Limitação: um ano que sumir inteiro da fato some da grade sem status sem_dado
    -- (o teste de tamanho da grade pega isso; tabela de anos esperados: pendência D41/D42).
    SELECT codigo_indicador, ano, cod_serie
    FROM silver.fato_indicador_municipio
    GROUP BY codigo_indicador, ano, cod_serie
)
SELECT m.cod_municipio,
       a.codigo_indicador,
       a.ano,
       f.valor,
       f.sinal_origem,
       CASE
           WHEN f.valor IS NOT NULL THEN 'com_valor'
           WHEN a.ano < m.ano_instalacao THEN 'municipio_nao_instalado'
           ELSE 'sem_dado'
       END AS status,
       CASE
           WHEN a.codigo_indicador = 'pop_estimada' AND a.ano = 2012
                AND m.ano_instalacao > a.ano AND f.valor IS NOT NULL
           THEN 'dupla contagem 2012 (regra 13)'
       END AS aviso,
       -- Regra 12: base da estimativa, definida pelo ano (fonte única para as outras views).
       CASE
           WHEN a.codigo_indicador <> 'pop_estimada' THEN NULL
           WHEN a.ano <= 2012 THEN 'ate_2012'
           WHEN a.ano <= 2017 THEN '2013_2017'
           ELSE 'desde_2018'
       END AS base_estimativa,
       i.unidade_armazenada AS unidade,
       i.tipo_medida,
       s.fonte,
       a.cod_serie,
       s.data_referencia,
       f.data_coleta
FROM gold.dim_municipio m
CROSS JOIN anos a
JOIN silver.dim_indicador i ON i.codigo_indicador = a.codigo_indicador
JOIN silver.dim_serie s ON s.cod_serie = a.cod_serie
LEFT JOIN silver.fato_indicador_municipio f
       ON f.cod_municipio = m.cod_municipio
      AND f.codigo_indicador = a.codigo_indicador
      AND f.ano = a.ano
      AND f.cod_serie = a.cod_serie;

COMMENT ON VIEW gold.grade_indicador_municipio_ano IS
    'Um registro por município, indicador e ano publicado. status: com_valor, '
    'municipio_nao_instalado (regra 10) ou sem_dado (não deveria ocorrer). Valores já na '
    'unidade armazenada (regra 11). PIB é nominal; per capita é o publicado, não é renda. '
    'Um ano ausente por inteiro da fato não aparece aqui (ver comentário no SQL).';
COMMENT ON COLUMN gold.grade_indicador_municipio_ano.aviso IS
    'Preenchido nas linhas de pop_estimada 2012 dos municípios ainda não instalados: entram em '
    'dupla contagem com o município de origem (regra 13, causa NÃO CONFIRMADA).';
COMMENT ON COLUMN gold.grade_indicador_municipio_ano.base_estimativa IS
    'Só para pop_estimada (regra 12): ate_2012, 2013_2017 (nova projeção; IBGE declara '
    'comparáveis só 2013–2017) ou desde_2018 (revisão da projeção).';
