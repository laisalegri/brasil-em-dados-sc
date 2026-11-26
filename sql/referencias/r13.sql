-- R13: Saltos anuais de PIB nominal acima de 50% (alerta A1) (docs/dashboards.md, seção 6)
SELECT count(*) AS variacoes, count(DISTINCT cod_municipio) AS municipios FROM gold.variacao_anual WHERE codigo_indicador = 'pib_corrente' AND abs(variacao_percentual) > 50;
