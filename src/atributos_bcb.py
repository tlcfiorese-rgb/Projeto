"""Atributos derivados para as series do BCB.
Le a Prata (ja tipada e conferida na aula passada), cria colunas
que respondem melhor a pergunta norteadora, e regrava a Prata."""

import json
from datetime import datetime
from pathlib import Path
import pandas as pd

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PRATA = RAIZ_PROJETO / "dados" / "prata"


def variacao_pct(df, coluna):
    """Variacao percentual em relacao ao registro anterior, na mesma serie.
    O sort_values garante que a variacao e calculada contra o dia
    anterior de verdade, nao contra a ordem em que o arquivo veio."""
    df = df.sort_values("data")
    df[coluna + "_variacao_pct"] = df[coluna].pct_change() * 100
    return df


def acumulado_12m(df, coluna):
    """Inflacao acumulada nos ultimos 12 meses (juros compostos).
    So faz sentido para series mensais, como o IPCA."""
    df = df.sort_values("data")
    fator = 1 + df[coluna] / 100
    df[coluna + "_acumulado_12m"] = (
        fator.rolling(window=12).apply(lambda x: x.prod(), raw=True) - 1
    ) * 100
    return df


def processar_selic():
    df = pd.read_parquet(PRATA / "selic.parquet")
    antes = df.shape[1]
    df = variacao_pct(df, "valor")
    df.to_parquet(PRATA / "selic.parquet", index=False)
    return df, antes


def processar_cambio():
    df = pd.read_parquet(PRATA / "cambio.parquet")
    antes = df.shape[1]
    df = variacao_pct(df, "valor")
    df.to_parquet(PRATA / "cambio.parquet", index=False)
    return df, antes


def processar_ipca():
    df = pd.read_parquet(PRATA / "ipca.parquet")
    antes = df.shape[1]
    df = acumulado_12m(df, "valor")
    df.to_parquet(PRATA / "ipca.parquet", index=False)
    return df, antes


def registrar(decisoes):
    info = {
        "etapa": "atributos_derivados",
        "decisoes": decisoes,
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
    }
    caminho = PRATA / "proveniencia.jsonl"
    with caminho.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")


def main():
    df_selic, cols_antes = processar_selic()
    print("selic: colunas", cols_antes, "->", df_selic.shape[1])

    df_cambio, cols_antes = processar_cambio()
    print("cambio: colunas", cols_antes, "->", df_cambio.shape[1])

    df_ipca, cols_antes = processar_ipca()
    print("ipca: colunas", cols_antes, "->", df_ipca.shape[1])
    print(df_ipca[["data", "valor", "valor_acumulado_12m"]].tail(5))

    registrar([
        "selic: coluna 'valor_variacao_pct' criada (variacao diaria, "
        "picos marcam dias de reuniao do COPOM que mudaram a taxa)",
        "cambio: coluna 'valor_variacao_pct' criada (variacao diaria "
        "do USD/BRL, valorizacao/desvalorizacao do real)",
        "ipca: coluna 'valor_acumulado_12m' criada (inflacao acumulada "
        "em 12 meses, juros compostos; ausente nos primeiros 11 meses "
        "da serie, por definicao)",
    ])
    print("\nAtributos derivados registrados na proveniencia.")


if __name__ == "__main__":
    main()