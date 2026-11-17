-- Dimensões da SILVER (D18), conforme docs/dicionario_dados.md, seções 1.1, 1.2 e 3.
-- Roda uma vez só (registro em public.ddl_aplicado). Depois de aplicado, NÃO edite este
-- arquivo: mudanças vão num arquivo novo numerado (04_...sql). IF NOT EXISTS fica como
-- defesa extra para bancos criados antes do registro.

-- dim_municipio -------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS silver.dim_municipio (
    cod_municipio             text PRIMARY KEY
                              CONSTRAINT ck_dim_municipio_cod CHECK (cod_municipio ~ '^42[0-9]{5}$'),
    nome_municipio            text NOT NULL CHECK (nome_municipio <> ''),
    cod_regiao_imediata       text NOT NULL
                              CONSTRAINT ck_dim_municipio_imediata CHECK (cod_regiao_imediata ~ '^42[0-9]{4}$'),
    nome_regiao_imediata      text NOT NULL,
    cod_regiao_intermediaria  text NOT NULL
                              CONSTRAINT ck_dim_municipio_intermediaria CHECK (cod_regiao_intermediaria ~ '^42[0-9]{2}$'),
    nome_regiao_intermediaria text NOT NULL,
    cod_microrregiao          text NOT NULL
                              CONSTRAINT ck_dim_municipio_micro CHECK (cod_microrregiao ~ '^42[0-9]{3}$'),
    nome_microrregiao         text NOT NULL,
    cod_mesorregiao           text NOT NULL
                              CONSTRAINT ck_dim_municipio_meso CHECK (cod_mesorregiao ~ '^42[0-9]{2}$'),
    nome_mesorregiao          text NOT NULL,
    cod_uf                    text NOT NULL CONSTRAINT ck_dim_municipio_uf CHECK (cod_uf = '42'),
    sigla_uf                  text NOT NULL CONSTRAINT ck_dim_municipio_sigla CHECK (sigla_uf = 'SC')
);

COMMENT ON TABLE silver.dim_municipio IS
    'Municípios de SC (295), da API de Localidades do IBGE, com as divisões regionais nova '
    '(imediata/intermediária) e antiga (micro/mesorregião). As divisões nunca se relacionam pelo id (D06).';
COMMENT ON COLUMN silver.dim_municipio.cod_municipio IS
    'Código IBGE de 7 dígitos, como texto. Chave em todas as camadas (regra 1).';
COMMENT ON COLUMN silver.dim_municipio.nome_municipio IS 'Nome oficial. Nunca é chave.';
COMMENT ON COLUMN silver.dim_municipio.cod_regiao_intermediaria IS
    'Região geográfica intermediária (divisão nova); filtro principal dos dashboards (D06).';
COMMENT ON COLUMN silver.dim_municipio.cod_mesorregiao IS
    'Mesorregião (divisão antiga). Usa a mesma faixa de ids da região intermediária: não comparar entre divisões.';

-- dim_indicador -------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS silver.dim_indicador (
    codigo_indicador   text PRIMARY KEY CHECK (codigo_indicador ~ '^[a-z][a-z0-9_]*$'),
    nome               text NOT NULL CHECK (nome <> ''),
    unidade_armazenada text NOT NULL CHECK (unidade_armazenada <> ''),
    tipo_medida        text NOT NULL
                       CONSTRAINT ck_dim_indicador_tipo_medida
                       CHECK (tipo_medida IN ('estimativa', 'censo', 'nominal')),
    descricao          text NOT NULL CHECK (descricao <> '')
);

COMMENT ON TABLE silver.dim_indicador IS
    'Indicadores de negócio (conceito). A origem técnica de cada valor fica na dim_serie (D10).';
COMMENT ON COLUMN silver.dim_indicador.unidade_armazenada IS
    'Unidade dos valores na SILVER e na GOLD (por exemplo, R$ ou Pessoas), já convertidos.';
COMMENT ON COLUMN silver.dim_indicador.tipo_medida IS
    'estimativa, censo ou nominal; nunca NULL. Cada linha da fato herda pelo indicador (regra 2).';

-- dim_serie -----------------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS silver.dim_serie (
    cod_serie             text PRIMARY KEY,
    codigo_indicador      text NOT NULL
                          REFERENCES silver.dim_indicador (codigo_indicador),
    fonte                 text NOT NULL
                          CONSTRAINT ck_dim_serie_fonte CHECK (fonte IN ('sidra', 'api_pesquisas')),
    tabela_ou_pesquisa    text NOT NULL,
    variavel_ou_indicador text NOT NULL,
    unidade_origem        text NOT NULL CHECK (unidade_origem <> ''),
    fator_conversao       numeric NOT NULL
                          CONSTRAINT ck_dim_serie_fator CHECK (fator_conversao > 0),
    data_referencia       text NOT NULL,
    url_extrator          text NOT NULL CHECK (url_extrator LIKE 'https://%'),
    -- Alvo da FK composta da fato: garante que a série pertence ao indicador da linha.
    CONSTRAINT uq_dim_serie_indicador UNIQUE (cod_serie, codigo_indicador)
);

COMMENT ON TABLE silver.dim_serie IS
    'Séries de origem (tabela/variável SIDRA ou pesquisa/indicador da API de Pesquisas). '
    'Carregada a partir de brasil_em_dados.extract.catalogo (D11).';
COMMENT ON COLUMN silver.dim_serie.unidade_origem IS 'Unidade na fonte, antes da conversão.';
COMMENT ON COLUMN silver.dim_serie.fator_conversao IS
    'valor_silver = valor_origem × fator_conversao. Única conversão do pipeline (regra 11).';
COMMENT ON COLUMN silver.dim_serie.data_referencia IS
    'Data de referência da medida (estimativas em 1º de julho; Censos na noite de 31/07 para 1º/08).';
COMMENT ON COLUMN silver.dim_serie.url_extrator IS 'URL final usada pelo extrator.';
