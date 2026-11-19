-- Passa quando devolve ZERO linhas.
-- A fato nao pode perder nem ganhar meses em relacao a tabela da juncao.
select linhas_fato, linhas_prata
from (
    select
        (select count(*) from {{ ref('fato_indicador_mensal') }}) as linhas_fato,
        (select count(*) from {{ source('prata', 'indicadores_mensais') }}) as linhas_prata
)
where linhas_fato <> linhas_prata
