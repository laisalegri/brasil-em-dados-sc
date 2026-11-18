-- Participação de cada município no total de SC, por indicador e ano (D30).

CREATE VIEW gold.participacao_estadual AS
SELECT g.cod_municipio,
       m.nome_municipio,
       g.codigo_indicador,
       g.tipo_medida,
       g.ano,
       g.base_estimativa,
       g.valor,
       e.valor AS total_estado,
       CASE WHEN g.aviso IS NULL THEN round(g.valor / NULLIF(e.valor, 0) * 100, 4)
       END AS participacao_percentual,
       g.aviso
FROM gold.grade_indicador_municipio_ano g
JOIN gold.dim_municipio m USING (cod_municipio)
JOIN gold.agregado_regiao_ano e
  ON e.nivel = 'estado' AND e.codigo_indicador = g.codigo_indicador AND e.ano = g.ano
WHERE g.codigo_indicador IN ('pop_estimada', 'pop_censo', 'pib_corrente');

COMMENT ON VIEW gold.participacao_estadual IS
    'Participação (%) no total de SC por indicador e ano; estimativa e Censo em linhas '
    'separadas (regra 2). Em pop_estimada 2012, os municípios em dupla contagem ficam sem '
    'participação e o total exclui os dois (regra 13).';
