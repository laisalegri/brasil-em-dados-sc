-- R08: Florianópolis nos Censos 2010 e 2022 (docs/dashboards.md, seção 6)
SELECT pop_censo_2010, pop_censo_2022, variacao_percentual FROM gold.variacao_populacao_censo WHERE cod_municipio = '4205407';
