-- Grao: uma linha por mes. Chave: mes.
-- A origem e a tabela da juncao (aula 7). O where e o filtro de integridade:
-- fato sem mes nao tem como ligar na dim_tempo.
select
    cast(mes as date) as mes,
    selic_meta,
    cambio_fim_mes,
    cambio_variacao_mensal_pct,
    ipca_mensal,
    ipca_extremo,
    ipca_acumulado_12m,
    juro_real_12m
from {{ source('prata', 'indicadores_mensais') }}
where mes is not null
