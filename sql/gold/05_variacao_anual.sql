-- Variação ano a ano de pop_estimada e pib_corrente por município (D30, regras 3 e 12).

CREATE VIEW gold.variacao_anual AS
WITH serie AS (
    SELECT cod_municipio, codigo_indicador, ano, valor, tipo_medida, unidade, base_estimativa
    FROM gold.grade_indicador_municipio_ano
    WHERE codigo_indicador IN ('pop_estimada', 'pib_corrente')
),
pares AS (
    SELECT b.cod_municipio, b.codigo_indicador, b.tipo_medida, b.unidade,
           a.ano AS ano_anterior, b.ano, a.valor AS valor_anterior, b.valor,
           a.base_estimativa AS base_anterior, b.base_estimativa,
           -- Regra 12: a troca de base vem da grade. ate_2012 → 2013_2017 é salto de nível
           -- (nova projeção); 2013_2017 → desde_2018 é revisão, sem salto visível em SC.
           -- COALESCE só nos marcadores de quebra (booleanos sobre base_estimativa), nunca em
           -- valor: no PIB a base é NULL, a comparação dava NULL e o CASE abaixo deixava NULL a
           -- variação de todo o pib_corrente (corrigido no D31). Valor ausente continua NULL, e
           -- valor - NULL continua NULL (regra 5).
           coalesce(a.base_estimativa = 'ate_2012' AND b.base_estimativa = '2013_2017', false)
               AS quebra_nivel,
           coalesce(a.base_estimativa = '2013_2017' AND b.base_estimativa = 'desde_2018', false)
               AS quebra_revisao
    FROM serie a
    JOIN serie b ON b.cod_municipio = a.cod_municipio
                AND b.codigo_indicador = a.codigo_indicador
                AND b.ano = a.ano + 1
)
SELECT p.cod_municipio,
       m.nome_municipio,
       p.codigo_indicador,
       p.tipo_medida,
       p.unidade,
       p.ano_anterior,
       p.ano,
       p.base_anterior,
       p.base_estimativa,
       p.valor_anterior,
       p.valor,
       CASE WHEN NOT p.quebra_nivel THEN p.valor - p.valor_anterior END AS variacao_absoluta,
       CASE WHEN NOT p.quebra_nivel
            THEN round((p.valor - p.valor_anterior) / NULLIF(p.valor_anterior, 0) * 100, 2)
       END AS variacao_percentual,
       CASE
           WHEN p.quebra_nivel OR p.quebra_revisao THEN false
           WHEN p.valor IS NULL OR p.valor_anterior IS NULL THEN NULL  -- sem número, sem juízo
           ELSE true
       END AS comparavel,
       CASE
           WHEN p.quebra_nivel THEN 'quebra de série: estimativas a partir de 2013 usam a nova '
                                    'projeção por UF; variação não calculada (regra 12)'
           WHEN p.quebra_revisao THEN 'revisão da projeção em 2018: o IBGE declara comparáveis só '
                                      '2013–2017; variação calculada, sem salto visível em SC, '
                                      'mas não comparável (regra 12)'
           WHEN p.valor IS NULL OR p.valor_anterior IS NULL THEN 'sem valor em um dos anos'
           WHEN p.valor_anterior = 0 THEN 'valor anterior igual a zero: variação percentual '
                                          'não definida'
       END AS motivo
FROM pares p
JOIN gold.dim_municipio m USING (cod_municipio);

COMMENT ON VIEW gold.variacao_anual IS
    'Variação ano a ano. pib_corrente é NOMINAL (tipo_medida): nunca crescimento real (regra 3). '
    'pop_estimada: 2012→2013 NULL e não comparável; 2017→2018 calculada e não comparável (regra 12). '
    'comparavel é NULL quando falta um dos valores.';
