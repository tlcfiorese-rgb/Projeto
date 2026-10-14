from pathlib import Path
import json
import pandas as pd
from data_profiling import ProfileReport

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
BRONZE = RAIZ_PROJETO / "dados" / "bronze" / "bcb"
RELATORIOS = RAIZ_PROJETO / "relatorios"

SERIES = ["selic", "cambio", "ipca"]

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
        print("perfilando:", caminho.name)
        df = carregar(caminho)
        saida = gerar(df, nome_serie)
        print("relatorio salvo em:", saida)
        print()


if __name__ == "__main__":
    main()