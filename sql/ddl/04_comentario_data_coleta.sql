-- Atualiza o significado de data_coleta na fato (D21, opção a), sem mexer nos dados.
-- O 03_fato_e_controle.sql já foi aplicado e não pode ser editado (public.ddl_aplicado).

COMMENT ON COLUMN silver.fato_indicador_municipio.data_coleta IS
    'A coleta que trouxe este valor (valor e sinal): coletado_em (UTC) do .meta.json da coleta '
    'em que o valor apareceu ou mudou. Coleta nova com o mesmo valor e sinal não altera a linha. '
    'A coleta mais recente de cada série está em silver.controle_execucao.';
