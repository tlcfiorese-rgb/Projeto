-- Passa quando devolve ZERO linhas.
-- Faixas largas de proposito: nao julgam a economia, so pegam erro de unidade
-- (valor x100, zero no lugar de ausente, sinal trocado).
select mes, selic_meta, cambio_fim_mes, ipca_mensal
from {{ ref('fato_indicador_mensal') }}
where selic_meta not between 0 and 50
   or cambio_fim_mes not between 0.5 and 20
   or ipca_mensal not between -3 and 6
