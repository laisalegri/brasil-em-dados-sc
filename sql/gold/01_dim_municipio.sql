-- GOLD (D30): views recriadas por `python -m brasil_em_dados.db.aplicar_gold` (DROP + CREATE,
-- numa transação). Views não guardam dados: ficam fora de public.ddl_aplicado (decisão D30).
-- Só CREATE VIEW e COMMENT ON; sem comandos do psql nem de transação.

CREATE VIEW gold.dim_municipio AS
SELECT m.cod_municipio,
       m.nome_municipio,
       m.cod_regiao_imediata,
       m.nome_regiao_imediata,
       m.cod_regiao_intermediaria,
       m.nome_regiao_intermediaria,
       m.cod_microrregiao,
       m.nome_microrregiao,
       m.cod_mesorregiao,
       m.nome_mesorregiao,
       m.cod_uf,
       m.sigla_uf,
       novos.ano_instalacao
FROM silver.dim_municipio m
-- Regra 10: únicos municípios instalados depois de 2010. Fonte única para as outras views.
LEFT JOIN (VALUES ('4212650', 2013),   -- Pescaria Brava (desmembrado de Laguna)
                  ('4220000', 2013))   -- Balneário Rincão (desmembrado de Içara)
          AS novos (cod_municipio, ano_instalacao) USING (cod_municipio);

COMMENT ON VIEW gold.dim_municipio IS
    'Municípios de SC com as duas hierarquias (nova: imediata/intermediária; antiga: '
    'micro/mesorregião). As divisões nunca se relacionam pelo id (D06).';
COMMENT ON COLUMN gold.dim_municipio.ano_instalacao IS
    'Ano de instalação, só para os municípios instalados depois de 2010 (regra 10); NULL para os demais.';
