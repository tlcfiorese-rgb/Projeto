{{ config(materialized='view') }}

-- Responde a pergunta norteadora: Selic alta anda junto com real valorizado?
-- Valorizacao do real = queda do USD/BRL, ou seja, variacao negativa do cambio.
-- Correlacao negativa entre Selic e variacao do cambio apoia a hipotese.
-- corr() ignora pares com valor ausente; as colunas 'meses_*' dizem quantos pares entraram.
with base as (
    select
        mes,
        selic_meta,
        cambio_fim_mes,
        cambio_variacao_mensal_pct,
        juro_real_12m,
        lag(selic_meta) over (order by mes) as selic_mes_anterior
    from {{ ref('fato_indicador_mensal') }}
)
select
    min(mes) as primeiro_mes,
    max(mes) as ultimo_mes,
    count(*) as meses,
    count(cambio_variacao_mensal_pct) as meses_com_variacao_cambio,
    count(juro_real_12m) as meses_com_juro_real,
    corr(selic_meta, cambio_fim_mes)                       as corr_selic_nivel_cambio_nivel,
    corr(selic_meta, cambio_variacao_mensal_pct)           as corr_selic_nivel_variacao_cambio,
    corr(selic_mes_anterior, cambio_variacao_mensal_pct)   as corr_selic_defasada_1m_variacao_cambio,
    corr(juro_real_12m, cambio_variacao_mensal_pct)        as corr_juro_real_variacao_cambio
from base
