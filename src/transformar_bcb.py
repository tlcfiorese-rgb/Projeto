import json
from datetime import datetime
from pathlib import Path
import pandas as pd

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
BRONZE = RAIZ_PROJETO / "dados" / "bronze" / "bcb"
PRATA = RAIZ_PROJETO / "dados" / "prata"

SERIES = ["selic", "cambio", "ipca"]


def carregar(nome_serie):
    """Acha o arquivo mais recente da serie e le o JSON bruto da bronze."""
    padrao = f"{nome_serie}_*.json"
    arquivos = sorted(BRONZE.glob(padrao))
    if not arquivos:
        raise FileNotFoundError(f"nada em {BRONZE} para '{nome_serie}'")
    caminho = arquivos[-1]

    dados = json.loads(caminho.read_text())
    df = pd.DataFrame(dados)

    print(f"\n--- {nome_serie} ---")
    print("lido:", caminho.name, df.shape)
    print(df.columns.tolist())
    print(df.isna().sum())

    return df, caminho


def converter_tipos(df):
    """A API devolve 'valor' e 'data' como texto. Converte para os tipos reais.
    errors='coerce' vira ausente o que nao for convertivel, em vez de
    derrubar o script - decisao registrada, nao um detalhe."""
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="coerce")
    return df


def conferir_chave(df, chave="data"):
    """Numa serie temporal, a chave e a propria data: um valor por dia.
    Chave repetida aqui seria sintoma de erro na extracao, nao normalidade."""
    repetidas = df[chave].duplicated().sum()
    print("datas repetidas:", repetidas)
    if repetidas:
        print(df[df[chave].duplicated(keep=False)])
    return df.drop_duplicates(subset=chave)


def limites_iqr(serie):
    q1 = serie.quantile(0.25)
    q3 = serie.quantile(0.75)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def marcar_extremos(df, coluna):
    """Marca extremos por IQR. Nao remove - Selic e IPCA tem historico de
    juros muito altos (ex: crise de 2015-16) e isso e dado real, nao erro."""
    baixo, alto = limites_iqr(df[coluna])
    df[coluna + "_extremo"] = (df[coluna] < baixo) | (df[coluna] > alto)
    print(coluna, "extremos (IQR):", df[coluna + "_extremo"].sum())
    return df


def marcar_zscore(df, coluna, limite=3):
    """Segundo metodo, para comparar com o IQR. Onde os dois discordam
    vale olhar a linha antes de decidir."""
    z = (df[coluna] - df[coluna].mean()) / df[coluna].std()
    df[coluna + "_z"] = z.abs() > limite
    print(coluna, "z acima de", limite, ":", df[coluna + "_z"].sum())
    return df


def salvar(df, nome_serie):
    """Grava a Prata em Parquet. Sem data no nome: a Prata e reconstruivel,
    cada execucao substitui a anterior."""
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / f"{nome_serie}.parquet"
    df.to_parquet(destino, index=False)
    print("salvo em:", destino, df.shape)
    return destino


def registrar(nome_serie, origem, destino, antes, depois, decisoes):
    """Registra as decisoes tomadas, nao so o resultado final."""
    info = {
        "serie": nome_serie,
        "origem": origem.name,
        "arquivo_prata": destino.name,
        "linhas_antes": antes,
        "linhas_depois": depois,
        "decisoes": decisoes,
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
    }
    caminho = PRATA / "proveniencia.jsonl"
    with caminho.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")


def processar(nome_serie):
    df, origem = carregar(nome_serie)
    antes = len(df)

    df = converter_tipos(df)
    df = conferir_chave(df)
    df = marcar_extremos(df, "valor")
    df = marcar_zscore(df, "valor")

    destino = salvar(df, nome_serie)
    registrar(nome_serie, origem, destino, antes, len(df), [
        "coluna 'valor' convertida de texto para numero (float)",
        "coluna 'data' convertida de texto para data",
        "chave 'data' conferida, sem duplicatas removidas" if df["data"].duplicated().sum() == 0
            else "duplicatas em 'data' removidas",
        "extremos marcados por IQR e z-score, nada removido (ver README)",
    ])


def main():
    for nome_serie in SERIES:
        processar(nome_serie)
    print("\nTodas as series processadas!")


if __name__ == "__main__":
    main()