"""Profiling opcional: gera relatorios/<serie>.html. Fora do pipeline."""

import json
import logging
import pandas as pd
from data_profiling import ProfileReport

from config import BRONZE, RELATORIOS, SERIES

log = logging.getLogger(__name__)

    # Acha o arquivo mais novo da série dentro da bronze
def mais_recente(nome_serie):
    """Acha o arquivo mais recente de uma serie, pelo nome no arquivo."""
    padrao = f"{nome_serie}_*.json"
    arquivos = sorted(BRONZE.glob(padrao))
    if not arquivos:
        raise FileNotFoundError(f"nenhum arquivo encontrado para '{nome_serie}' em {BRONZE}")
    return arquivos[-1]

    # Lê o JSON bruto da bronze e transforma em DataFrame (tabela), sem tratar nada
def carregar(caminho):
    """Le o JSON bruto da bronze e transforma em DataFrame, sem tratar nada."""
    dados = json.loads(caminho.read_text())
    return pd.DataFrame(dados)

    # Gera o relatório de perfil da série (HTML), com estatísticas, gráficos e alertas
def gerar(df, nome_serie):
    """Gera o relatorio de perfil para uma serie."""
    RELATORIOS.mkdir(exist_ok=True)
    perfil = ProfileReport(df, title=f"BCB - {nome_serie}")
    saida = RELATORIOS / f"{nome_serie}.html"
    perfil.to_file(saida)
    return saida


def main():
    for nome_serie in SERIES:
        caminho = mais_recente(nome_serie)
        log.info("perfilando: %s", caminho.name)
        df = carregar(caminho)
        saida = gerar(df, nome_serie)
        log.info("relatorio salvo em %s", saida)


if __name__ == "__main__":
    from config import configurar_log
    configurar_log()
    main()