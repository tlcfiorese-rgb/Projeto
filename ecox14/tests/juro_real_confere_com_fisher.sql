-- Passa quando devolve ZERO linhas.
-- Recalcula o juro real a partir das colunas da propria fato e compara.
-- Tambem exige que ele esteja ausente exatamente onde o IPCA acumulado esta.
select mes, juro_real_12m, esperado
from (
    select
        mes,
        juro_real_12m,
        ipca_acumulado_12m,
        ((1 + selic_meta / 100) / (1 + ipca_acumulado_12m / 100) - 1) * 100 as esperado
    from {{ ref('fato_indicador_mensal') }}
)
where (juro_real_12m is null) <> (ipca_acumulado_12m is null)
   or abs(juro_real_12m - esperado) > 1e-6
