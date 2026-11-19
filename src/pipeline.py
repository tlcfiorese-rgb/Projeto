"""Ponto de entrada: roda o pipeline inteiro, ou a partir de uma etapa.

    python src/pipeline.py                 # tudo, da API a camada Ouro
    python src/pipeline.py enriquecimento  # retoma desta etapa em diante

Falhou no meio, conserta e retoma: nao precisa baixar tudo da API de novo."""

import logging
import subprocess
import sys
import time

import config

log = logging.getLogger("pipeline")


# Os imports ficam dentro das funcoes: erro de import em uma etapa nao
# impede as demais de rodar, e o config nao depende de ninguem.
def etapa_ingestao():
    import ingerir
    ingerir.main()


def etapa_transformacao():
    import transformar_bcb
    transformar_bcb.main()


def etapa_atributos():
    import atributos_bcb
    atributos_bcb.main()


def etapa_enriquecimento():
    import enriquecer_bcb
    enriquecer_bcb.main()


def etapa_carga():
    import carga
    carga.main()


def _dbt(comando):
    """Chama o dbt a partir de ecox14/. check=True: se o dbt falhar o pipeline
    para, em vez de dizer que terminou bem com a Ouro quebrada."""
    subprocess.run(
        [sys.executable, "-W", "ignore::RuntimeWarning",
         "-m", "dbt.cli.main", comando, "--profiles-dir", "."],
        cwd=config.RAIZ / "ecox14",
        check=True,
    )


def etapa_modelagem():
    _dbt("run")


def etapa_testes():
    """dbt test: se algum teste falhar, o pipeline para e a Ouro nao deve ser
    usada. Passando, registra o resumo (contagens e correlacoes) no log."""
    import carga
    _dbt("test")
    carga.resumir_ouro()


ETAPAS = [
    ("ingestao", etapa_ingestao),
    ("transformacao", etapa_transformacao),
    ("atributos", etapa_atributos),
    ("enriquecimento", etapa_enriquecimento),
    ("carga", etapa_carga),
    ("modelagem", etapa_modelagem),
    ("testes", etapa_testes),
]


def executar(nome, funcao):
    log.info("etapa %s: inicio", nome)
    inicio = time.time()
    try:
        funcao()
    except Exception:
        log.exception("etapa %s falhou", nome)
        raise
    log.info("etapa %s: fim em %.0fs", nome, time.time() - inicio)


def main(a_partir_de=None):
    config.configurar_log()
    nomes = [nome for nome, _ in ETAPAS]
    if a_partir_de is not None and a_partir_de not in nomes:
        raise SystemExit(f"etapa '{a_partir_de}' nao existe. Opcoes: {', '.join(nomes)}")
    comecou = a_partir_de is None
    for nome, funcao in ETAPAS:
        if nome == a_partir_de:
            comecou = True
        if not comecou or funcao is None:
            log.info("etapa %s: pulada", nome)
            continue
        executar(nome, funcao)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
