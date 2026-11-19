{{ config(materialized='view') }}

-- A tabela achatada: fato com o calendario ao lado, derivada da estrela.
select f.*, d.ano, d.mes_numero, d.trimestre, d.semestre, d.ano_mes
from {{ ref('fato_indicador_mensal') }} f
join {{ ref('dim_tempo') }} d using (mes)
