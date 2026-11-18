-- Variação populacional oficial (D01): Censo 2010 × Censo 2022, por município.

CREATE VIEW gold.variacao_populacao_censo AS
SELECT m.cod_municipio,
       m.nome_municipio,
       c10.valor AS pop_censo_2010,
       c22.valor AS pop_censo_2022,
       c22.valor - c10.valor AS variacao_absoluta,
       round((c22.valor - c10.valor) / NULLIF(c10.valor, 0) * 100, 2) AS variacao_percentual,
       CASE
           WHEN c10.valor IS NULL AND m.ano_instalacao > 2010
           THEN 'sem Censo 2010: município instalado em ' || m.ano_instalacao
           WHEN c10.valor IS NULL OR c22.valor IS NULL THEN 'sem valor em um dos Censos'
           WHEN c10.valor = 0 THEN 'Censo 2010 igual a zero: variação percentual não definida'
       END AS motivo
FROM gold.dim_municipio m
LEFT JOIN gold.grade_indicador_municipio_ano c10
       ON c10.cod_municipio = m.cod_municipio AND c10.codigo_indicador = 'pop_censo'
      AND c10.ano = 2010
LEFT JOIN gold.grade_indicador_municipio_ano c22
       ON c22.cod_municipio = m.cod_municipio AND c22.codigo_indicador = 'pop_censo'
      AND c22.ano = 2022;

COMMENT ON VIEW gold.variacao_populacao_censo IS
    'Censo 2010 × Censo 2022 (mesmo método; datas de referência 1º/08). Variação NULL, com '
    'motivo, para os municípios instalados em 2013.';
