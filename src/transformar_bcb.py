"""Prata: tipos, chave e extremos (IQR e z-score, marcados e nao removidos)."""

import json
import logging
from datetime import datetime
import pandas as pd

from config import BRONZE, PRATA, SERIES

log = logging.getLogger(__name__)

    # Lê o arquivo mais recente da bronze
def carregar(nome_serie):
    """Acha o arquivo mais recente da serie e le o JSON bruto da bronze."""
    padrao = f"{nome_serie}_*.json"
    arquivos = sorted(BRONZE.glob(padrao))
    if not arquivos:
        raise FileNotFoundError(f"nada em {BRONZE} para '{nome_serie}'")
    caminho = arquivos[-1]

    dados = json.loads(caminho.read_text())
    df = pd.DataFrame(dados)

    log.info("%s: lido %s %s", nome_serie, caminho.name, df.shape)
    log.debug("%s: colunas %s", nome_serie, df.columns.tolist())
    log.debug("%s: ausentes por coluna %s", nome_serie, df.isna().sum().to_dict())

    return df, caminho

    # Transforma 'valor' e 'data' de texto para numero e data, respectivamente
def converter_tipos(df):
    """A API devolve 'valor' e 'data' como texto. Converte para os tipos reais.
    errors='coerce' vira ausente o que nao for convertivel, em vez de
    derrubar o script - decisao registrada, nao um detalhe."""
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="coerce")
    return df

    # Confirma que não existe data duplicada
def conferir_chave(df, chave="data"):
    """Numa serie temporal, a chave e a propria data: um valor por dia.
    Chave repetida aqui seria sintoma de erro na extracao, nao normalidade."""
    repetidas = df[chave].duplicated().sum()
    if repetidas:
        log.warning("%d datas repetidas, mantida a primeira de cada", repetidas)
        log.warning("repetidas:\n%s", df[df[chave].duplicated(keep=False)])
    return df.drop_duplicates(subset=chave)


def limites_iqr(serie):
    q1 = serie.quantile(0.25)
    q3 = serie.quantile(0.75)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr

    # Identifica pontos fora do padrão pelo método IQR - sem remover
def marcar_extremos(df, coluna):
    """Marca extremos por IQR. Nao remove - Selic e IPCA tem historico de
    juros muito altos (ex: crise de 2015-16) e isso e dado real, nao erro."""
    baixo, alto = limites_iqr(df[coluna])
    df[coluna + "_extremo"] = (df[coluna] < baixo) | (df[coluna] > alto)
    log.info("%s: %d extremos (IQR)", coluna, df[coluna + "_extremo"].sum())
    return df

    # Refaz a mesma checagem por outro método, para comparar divergências
def marcar_zscore(df, coluna, limite=3):
    """Segundo metodo, para comparar com o IQR. Onde os dois discordam
    vale olhar a linha antes de decidir."""
    z = (df[coluna] - df[coluna].mean()) / df[coluna].std()
    df[coluna + "_z"] = z.abs() > limite
    log.info("%s: %d com |z| acima de %s", coluna, df[coluna + "_z"].sum(), limite)
    return df

    # Grava a tabela tratada em Parquet, na camada prata
def salvar(df, nome_serie):
    """Grava a Prata em Parquet. Sem data no nome: a Prata e reconstruivel,
    cada execucao substitui a anterior."""
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / f"{nome_serie}.parquet"
    df.to_parquet(destino, index=False)
    log.info("salvo em %s %s", destino, df.shape)
    return destino

    # Registra as decisões tomadas, não só o resultado final
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

    # Realiza a chamada das funções na ordem correta, para cada série
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
    log.info("todas as series processadas")


if __name__ == "__main__":
    from config import configurar_log
    configurar_log()
    main()