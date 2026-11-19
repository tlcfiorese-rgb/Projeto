-- Uma linha por mes do primeiro ao ultimo mes da Prata.
select
    cast(mes as date)       as mes,
    year(mes)               as ano,
    month(mes)              as mes_numero,
    quarter(mes)            as trimestre,
    case when month(mes) <= 6 then 1 else 2 end as semestre,
    strftime(mes, '%Y-%m')  as ano_mes
from (
    select unnest(generate_series(min(mes), max(mes), interval 1 month)) as mes
    from {{ source('prata', 'indicadores_mensais') }}
)
