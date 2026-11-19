"""Consultas de leitura sobre a camada Ouro. Todo o SQL do painel mora aqui.

O painel e consumidor: abre o banco em modo somente leitura, entao nao
altera nada e nao trava o dbt (ver _consultar). Valores que vem da tela
entram sempre como parametro (?), nunca concatenados no texto do SQL."""

import json
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "dados" / "ouro" / "projeto.duckdb"
PROVENIENCIA = RAIZ / "dados" / "bronze" / "bcb" / "proveniencia.json"


def _consultar(sql, parametros=None):
    con = duckdb.connect(str(BANCO), read_only=True)
    try:
        return con.execute(sql, parametros or []).df()
    finally:
        con.close()


def anos_disponiveis():
    """Primeiro e ultimo ano da Ouro, para o filtro de periodo."""
    return _consultar("""
        select min(ano) as ano_min, max(ano) as ano_max
        from ouro.vw_indicador_completo
    """)


def serie_mensal(ano_inicial, ano_final):
    """A serie mensal do periodo, uma linha por mes."""
    return _consultar(
        """
        select mes, ano_mes, selic_meta, cambio_fim_mes,
               cambio_variacao_mensal_pct, ipca_mensal,
               ipca_acumulado_12m, juro_real_12m
        from ouro.vw_indicador_completo
        where ano between ? and ?
        order by mes
        """,
        [int(ano_inicial), int(ano_final)],
    )


def mes_mais_recente():
    """Ultimo mes da Ouro (o mes em curso: Selic e cambio ate a data da
    extracao, IPCA ainda ausente)."""
    return _consultar("""
        select mes, selic_meta, cambio_fim_mes
        from ouro.vw_indicador_completo
        order by mes desc limit 1
    """)


def ultimo_mes_completo():
    """Ultimo mes com IPCA divulgado e, portanto, juro real calculado."""
    return _consultar("""
        select mes, ipca_acumulado_12m, juro_real_12m
        from ouro.vw_indicador_completo
        where juro_real_12m is not null
        order by mes desc limit 1
    """)


def correlacoes(ano_inicial, ano_final):
    """Correlacoes de Pearson da pergunta norteadora, no periodo escolhido.
    Valorizacao do real = queda do dolar = variacao mensal negativa.
    A defasagem (Selic do mes anterior) usa a serie inteira e so depois
    filtra o periodo, para o primeiro mes do filtro nao perder o par."""
    return _consultar(
        """
        with base as (
            select ano, selic_meta, cambio_fim_mes, cambio_variacao_mensal_pct,
                   juro_real_12m,
                   lag(selic_meta) over (order by mes) as selic_mes_anterior
            from ouro.vw_indicador_completo
        ),
        periodo as (select * from base where ano between ? and ?)
        select 'Selic (nível) × dólar (nível)' as relacao,
               corr(selic_meta, cambio_fim_mes) as correlacao,
               count(*) filter (where selic_meta is not null
                                  and cambio_fim_mes is not null) as pares
        from periodo
        union all
        select 'Selic (nível) × variação mensal do dólar',
               corr(selic_meta, cambio_variacao_mensal_pct),
               count(*) filter (where selic_meta is not null
                                  and cambio_variacao_mensal_pct is not null)
        from periodo
        union all
        select 'Selic do mês anterior × variação mensal do dólar',
               corr(selic_mes_anterior, cambio_variacao_mensal_pct),
               count(*) filter (where selic_mes_anterior is not null
                                  and cambio_variacao_mensal_pct is not null)
        from periodo
        union all
        select 'Juro real 12m × variação mensal do dólar',
               corr(juro_real_12m, cambio_variacao_mensal_pct),
               count(*) filter (where juro_real_12m is not null
                                  and cambio_variacao_mensal_pct is not null)
        from periodo
        """,
        [int(ano_inicial), int(ano_final)],
    )


def proveniencia():
    """De onde veio o dado: o registro que a ingestao gravou na Bronze."""
    if not PROVENIENCIA.exists():
        return {}
    return json.loads(PROVENIENCIA.read_text(encoding="utf-8"))
