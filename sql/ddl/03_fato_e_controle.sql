-- Fato e controle de execução da SILVER (D19), conforme docs/dicionario_dados.md (1.3)
-- e docs/padrao_coleta.md (seção 9). Depende de 02_dimensoes.sql.
-- Roda uma vez só (registro em public.ddl_aplicado). Depois de aplicado, NÃO edite este
-- arquivo: mudanças vão num arquivo novo numerado (04_...sql).

-- fato_indicador_municipio --------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS silver.fato_indicador_municipio (
    cod_municipio    text NOT NULL
                     CONSTRAINT ck_fato_cod_municipio CHECK (cod_municipio ~ '^42[0-9]{5}$'),
    codigo_indicador text NOT NULL,
    ano              smallint NOT NULL
                     CONSTRAINT ck_fato_ano CHECK (ano BETWEEN 2010 AND 2023),
    cod_serie        text NOT NULL,
    valor            numeric(18, 2),
    -- Sinais oficiais (docs/fontes/sidra_convencoes.md): -, ..., .., X e letras de faixa A–Z.
    sinal_origem     text CONSTRAINT ck_fato_sinal_dominio
                     CHECK (sinal_origem IN ('-', '...', '..') OR sinal_origem ~ '^[A-Z]$'),
    data_coleta      timestamptz NOT NULL,
    CONSTRAINT pk_fato_indicador_municipio PRIMARY KEY (cod_municipio, codigo_indicador, ano),
    -- Ausência é NULL (regra 5), mas sempre com o sinal que a explica (regra 9).
    CONSTRAINT ck_fato_valor_ou_sinal CHECK (valor IS NOT NULL OR sinal_origem IS NOT NULL),
    -- Regra 9: valor numérico não tem sinal. Única exceção: "-" do SIDRA, que carrega como 0.
    -- (O "-" da API de Pesquisas carrega como NULL e passa pela primeira condição.)
    CONSTRAINT ck_fato_valor_e_sinal_coerentes CHECK (
        valor IS NULL OR sinal_origem IS NULL OR (sinal_origem = '-' AND valor = 0)
    ),
    CONSTRAINT fk_fato_municipio FOREIGN KEY (cod_municipio)
        REFERENCES silver.dim_municipio (cod_municipio),
    CONSTRAINT fk_fato_indicador FOREIGN KEY (codigo_indicador)
        REFERENCES silver.dim_indicador (codigo_indicador),
    -- A série precisa pertencer ao indicador da linha (por exemplo, sidra_5938_v37 só em pib_corrente).
    CONSTRAINT fk_fato_serie_do_indicador FOREIGN KEY (cod_serie, codigo_indicador)
        REFERENCES silver.dim_serie (cod_serie, codigo_indicador)
);

CREATE INDEX IF NOT EXISTS ix_fato_indicador_ano
    ON silver.fato_indicador_municipio (codigo_indicador, ano);

COMMENT ON TABLE silver.fato_indicador_municipio IS
    'Um valor por município, indicador e ano. tipo_medida vem da dim_indicador (regra 2). '
    'Guarda só o que a fonte devolveu; a grade completa é montada na GOLD.';
COMMENT ON COLUMN silver.fato_indicador_municipio.ano IS 'Ano de referência, de 2010 a 2023.';
COMMENT ON COLUMN silver.fato_indicador_municipio.cod_serie IS
    'Série de origem (regra 8); FK composta com codigo_indicador para a dim_serie.';
COMMENT ON COLUMN silver.fato_indicador_municipio.valor IS
    'Já convertido para a unidade_armazenada (regra 11). NULL quando veio sinal de ausência (regra 5). '
    'PIB é nominal (regra 3); PIB per capita é o publicado, não é renda (regra 4).';
COMMENT ON COLUMN silver.fato_indicador_municipio.sinal_origem IS
    'Sinal original da fonte (-, ..., .., X); NULL quando o valor veio numérico (regra 9).';
COMMENT ON COLUMN silver.fato_indicador_municipio.data_coleta IS
    'Momento (UTC) da coleta que gerou o arquivo RAW de origem.';

-- controle_execucao ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS silver.controle_execucao (
    id_execucao bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cod_serie   text NOT NULL,
    inicio      timestamptz NOT NULL,
    fim         timestamptz NOT NULL,
    status      text NOT NULL
                CONSTRAINT ck_controle_status CHECK (status IN ('sucesso', 'falha')),
    n_registros integer CONSTRAINT ck_controle_n_registros CHECK (n_registros >= 0),
    arquivo     text,
    erro        text,
    CONSTRAINT ck_controle_fim_depois_do_inicio CHECK (fim >= inicio),
    -- Mesmo contrato do registrar_execucao: sucesso tem arquivo e contagem; falha tem erro.
    CONSTRAINT ck_controle_coerente CHECK (
        (status = 'sucesso' AND arquivo IS NOT NULL AND n_registros IS NOT NULL AND erro IS NULL)
        OR (status = 'falha' AND arquivo IS NULL AND erro IS NOT NULL)
    ),
    -- Permite recarregar o execucoes.jsonl (D21) sem duplicar linhas.
    CONSTRAINT uq_controle_serie_inicio UNIQUE (cod_serie, inicio)
);

COMMENT ON TABLE silver.controle_execucao IS
    'Execuções das coletas, carregadas de data/controle/execucoes.jsonl (docs/padrao_coleta.md, seção 9). '
    'cod_serie não tem FK: inclui fontes de dimensão (ibge_localidades_sc), que não estão na dim_serie.';
COMMENT ON COLUMN silver.controle_execucao.arquivo IS
    'Arquivo de dados gravado na RAW ({cod_serie}/{carimbo}.json); NULL em falha.';
COMMENT ON COLUMN silver.controle_execucao.erro IS 'Tipo e mensagem do erro; NULL em sucesso.';
