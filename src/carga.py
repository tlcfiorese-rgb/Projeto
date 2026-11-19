"""Carga: abre o DuckDB e carrega a Prata nele.

A Ouro (dim_tempo, fato_indicador_mensal e as views) e construida pelo dbt,
na etapa 'modelagem', e testada pelo dbt na etapa 'testes' (ver ecox14/).
Este modulo faz o que nao e transformacao: ler arquivo, abrir banco e
conferir que a Prata chegou inteira.

O SQL de construir_ouro foi mantido, sem ser chamado, para comparar com
o que o dbt produz: python src/carga.py --sql"""

import logging
import sys

import duckdb

from config import BANCO, OURO, PRATA, TABELAS_PRATA

log = logging.getLogger(__name__)


def conectar():
    OURO.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(BANCO))


def criar_esquemas(con):
    con.execute("CREATE SCHEMA IF NOT EXISTS prata")
    con.execute("CREATE SCHEMA IF NOT EXISTS ouro")


def um_valor(con, sql):
    """con.execute, e nao con.sql: o objeto de con.sql nem sempre tem fetchone."""
    return con.execute(sql).fetchone()[0]


def carregar_prata(con):
    """Cada Parquet da Prata vira uma tabela no esquema prata."""
    for tabela in TABELAS_PRATA:
        # as_posix: o SQL espera barra comum, nao a barra invertida do Windows
        caminho = (PRATA / f"{tabela}.parquet").as_posix()
        con.execute(f"""
            CREATE OR REPLACE TABLE prata.{tabela} AS
            SELECT * FROM read_parquet('{caminho}')
        """)
        linhas = um_valor(con, f"SELECT COUNT(*) FROM prata.{tabela}")
        log.info("prata.%s: %d linhas", tabela, linhas)


def conferir_prata(con):
    """O banco tem o mesmo numero de linhas que o Parquet, e o grao
    de indicadores_mensais (um mes por linha) se confirma."""
    for tabela in TABELAS_PRATA:
        caminho = (PRATA / f"{tabela}.parquet").as_posix()
        no_arquivo = um_valor(con, f"SELECT COUNT(*) FROM read_parquet('{caminho}')")
        no_banco = um_valor(con, f"SELECT COUNT(*) FROM prata.{tabela}")
        if no_arquivo != no_banco:
            raise ValueError(f"prata.{tabela}: {no_arquivo} no arquivo, {no_banco} no banco")
    repetidos = um_valor(con, """
        SELECT COUNT(*) FROM (
            SELECT mes FROM prata.indicadores_mensais
            GROUP BY mes HAVING COUNT(*) > 1)
    """)
    if repetidos:
        raise ValueError(f"prata.indicadores_mensais: {repetidos} meses repetidos")
    log.info("prata conferida: contagens batem e o grao (um mes) se confirma")


def construir_ouro(con):
    """Versao em SQL puro da Ouro (aula 9). Hoje quem constroi e o dbt;
    esta funcao serve para comparar os dois resultados."""
    con.execute("""
        CREATE OR REPLACE TABLE ouro.dim_tempo AS
        SELECT
            CAST(mes AS DATE)       AS mes,
            YEAR(mes)               AS ano,
            MONTH(mes)              AS mes_numero,
            QUARTER(mes)            AS trimestre,
            CASE WHEN MONTH(mes) <= 6 THEN 1 ELSE 2 END AS semestre,
            STRFTIME(mes, '%Y-%m')  AS ano_mes
        FROM (
            SELECT UNNEST(GENERATE_SERIES(MIN(mes), MAX(mes), INTERVAL 1 MONTH)) AS mes
            FROM prata.indicadores_mensais
        )
    """)
    con.execute("""
        CREATE OR REPLACE TABLE ouro.fato_indicador_mensal AS
        SELECT
            CAST(mes AS DATE) AS mes,
            selic_meta, cambio_fim_mes, cambio_variacao_mensal_pct,
            ipca_mensal, ipca_extremo, ipca_acumulado_12m, juro_real_12m
        FROM prata.indicadores_mensais
        WHERE mes IS NOT NULL
    """)
    con.execute("""
        CREATE OR REPLACE VIEW ouro.vw_indicador_completo AS
        SELECT f.*, d.ano, d.mes_numero, d.trimestre, d.semestre, d.ano_mes
        FROM ouro.fato_indicador_mensal f
        JOIN ouro.dim_tempo d USING (mes)
    """)


def resumir_ouro(con=None):
    """Registra no log o que ha na Ouro e as correlacoes da pergunta
    norteadora. NAO confere nada: quem confere sao os testes do dbt
    (ecox14/models/schema.yml e ecox14/tests), que param o pipeline."""
    fechar = con is None
    con = con or conectar()
    try:
        na_dim = um_valor(con, "SELECT COUNT(*) FROM ouro.dim_tempo")
        na_fato = um_valor(con, "SELECT COUNT(*) FROM ouro.fato_indicador_mensal")
        na_view = um_valor(con, "SELECT COUNT(*) FROM ouro.vw_indicador_completo")
        sem_ipca = um_valor(con, """
            SELECT COUNT(*) FROM ouro.fato_indicador_mensal WHERE ipca_mensal IS NULL
        """)
        log.info("ouro: dim_tempo %d | fato %d | view %d", na_dim, na_fato, na_view)
        if sem_ipca:
            log.warning("ouro: %d meses sem IPCA na fato (mes em curso ainda nao divulgado)",
                        sem_ipca)
        corr = con.execute("SELECT * FROM ouro.vw_correlacao_selic_dolar").fetchdf()
        log.info("correlacao Selic x dolar:\n%s", corr.T.to_string(header=False))
    finally:
        if fechar:
            con.close()


def main(construir_com_sql=False):
    con = conectar()
    try:
        criar_esquemas(con)
        carregar_prata(con)
        conferir_prata(con)
        if construir_com_sql:
            construir_ouro(con)
            log.info("ouro construida pelo SQL do carga.py (comparacao com o dbt)")
    finally:
        con.close()  # libera o arquivo: o dbt precisa abrir o mesmo banco


if __name__ == "__main__":
    from config import configurar_log
    configurar_log()
    main(construir_com_sql="--sql" in sys.argv)
