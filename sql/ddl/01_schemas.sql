-- Schemas por camada (D18/D19). Executado como bed_app (dono do banco) por:
--     python -m brasil_em_dados.db.aplicar_ddl
-- Roda uma vez só (registro em public.ddl_aplicado); depois de aplicado, não edite: crie um
-- arquivo novo numerado. Sem comandos do psql nem de transação: o aplicador recusa.

CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

COMMENT ON SCHEMA silver IS
    'Camada SILVER: dados normalizados, com chaves, tipos, unidades convertidas e restrições.';
COMMENT ON SCHEMA gold IS
    'Camada GOLD: views e tabelas analíticas para EDA e dashboards; sem conversão de unidade.';

-- bed_readonly (agentes) lê as duas camadas e não escreve em nenhuma.
GRANT USAGE ON SCHEMA silver, gold TO bed_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA silver, gold TO bed_readonly;

-- Tabelas e views que bed_app criar depois nos dois schemas já nascem legíveis pelo bed_readonly.
-- (Valem só para objetos criados por bed_app, o usuário que roda este script.)
ALTER DEFAULT PRIVILEGES FOR ROLE bed_app IN SCHEMA silver, gold
    GRANT SELECT ON TABLES TO bed_readonly;
