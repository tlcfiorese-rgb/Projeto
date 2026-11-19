-- Passa quando devolve ZERO linhas.
-- Todo mes, exceto o primeiro, precisa ter o mes anterior na fato.
-- A linha devolvida e o mes SEGUINTE ao buraco.
-- Pega um mes que sumiu da Selic ou do cambio, que a juncao nao reclama.
select f.mes
from {{ ref('fato_indicador_mensal') }} f
where f.mes > (select min(mes) from {{ ref('fato_indicador_mensal') }})
  and not exists (
      select 1
      from {{ ref('fato_indicador_mensal') }} anterior
      where anterior.mes = cast(f.mes - interval 1 month as date)
  )
