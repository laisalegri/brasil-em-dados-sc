-- Banco e usuários do projeto Brasil em Dados SC (D17).
--
-- Executar no psql como superusuário (por exemplo, postgres):
--     psql -U postgres -f sql/ddl/00_banco_e_usuarios.sql
-- O script é idempotente: pode ser rodado de novo sem erro e só reaplica os privilégios.
--
-- Senhas NÃO ficam neste arquivo. Depois de rodar o script, defina-as no psql com:
--     \password bed_app
--     \password bed_readonly
-- e copie-as para o .env (modelo em .env.example), que nunca é versionado.
--
-- Usuários:
--   bed_app       dono do banco; usado pelo pipeline para criar tabelas e carregar dados.
--   bed_readonly  somente leitura; usado pelos agentes (CLAUDE.md: agentes não alteram dados).

-- Qualquer erro real interrompe o script.
\set ON_ERROR_STOP on

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bed_app') THEN
        CREATE ROLE bed_app LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bed_readonly') THEN
        CREATE ROLE bed_readonly LOGIN;
    END IF;
END
$$;

-- Segunda barreira: mesmo que um privilégio de escrita seja concedido por engano no futuro,
-- as transações do bed_readonly começam somente leitura.
ALTER ROLE bed_readonly SET default_transaction_read_only = on;

-- CREATE DATABASE não roda dentro de DO; \gexec executa o comando só se o banco não existir.
SELECT 'CREATE DATABASE brasil_em_dados OWNER bed_app ENCODING ''UTF8'' TEMPLATE template0'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'brasil_em_dados')
\gexec

-- Nenhum usuário comum além dos dois conecta (superusuários sempre conectam).
-- PUBLIC também perde o direito a tabelas temporárias.
REVOKE ALL ON DATABASE brasil_em_dados FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE brasil_em_dados TO bed_app;
GRANT CONNECT ON DATABASE brasil_em_dados TO bed_readonly;

\connect brasil_em_dados

-- Schema public:
--   PostgreSQL >= 15: public pertence a pg_database_owner (aqui, bed_app) e PUBLIC já não tem
--                     CREATE; os dois comandos abaixo só deixam a regra explícita na ACL.
--   PostgreSQL < 15:  public pertence ao postgres e PUBLIC tem CREATE; os dois são necessários.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO bed_app;
GRANT USAGE ON SCHEMA public TO bed_readonly;

-- Leitura do que já existe e do que bed_app criar no futuro.
-- Atenção: os privilégios padrão valem só para objetos criados POR bed_app. Uma tabela criada
-- por outro usuário (por exemplo, postgres) fica invisível ao bed_readonly até um GRANT explícito.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO bed_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE bed_app IN SCHEMA public
    GRANT SELECT ON TABLES TO bed_readonly;
