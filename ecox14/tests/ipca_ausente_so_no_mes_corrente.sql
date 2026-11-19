-- Passa quando devolve ZERO linhas.
-- Regra documentada no README: so o ultimo mes pode estar sem IPCA (ainda nao
-- divulgado). IPCA ausente em qualquer outro mes e defeito da fonte ou da juncao.
select mes
from {{ ref('fato_indicador_mensal') }}
where ipca_mensal is null
  and mes < (select max(mes) from {{ ref('fato_indicador_mensal') }})
