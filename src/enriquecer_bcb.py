"""Enriquecimento: junta Selic, cambio e IPCA numa unica tabela mensal.
Le a Prata (ja tipada e com atributos) e grava mais uma tabela na Prata.
Rode antes: transformar_bcb.py e atributos_bcb.py."""

import json
from datetime import datetime
from pathlib import Path
import pandas as pd

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
PRATA = RAIZ_PROJETO / "dados" / "prata"


def carregar(nome_serie):
    return pd.read_parquet(PRATA / f"{nome_serie}.parquet")


def chave_mes(serie_data):
    """Chave comum as tres tabelas: primeiro dia do mes, como data.
    O mesmo tipo dos tres lados evita o motivo 'tipo diferente'."""
    return serie_data.dt.to_period("M").dt.to_timestamp()


def selic_mensal(df):
    """Selic e diaria. Fica o ultimo valor de cada mes: a meta em vigor
    no fim do mes. A linha passa de 'um dia' para 'um mes'."""
    df = df.sort_values("data").copy()
    df["mes"] = chave_mes(df["data"])
    print("selic: de", df["data"].min().date(), "a", df["data"].max().date())
    return (df.groupby("mes", as_index=False)["valor"].last()
              .rename(columns={"valor": "selic_meta"}))


def cambio_mensal(df):
    """Cambio e diario (so dias uteis). Fica a cotacao do ultimo dia
    disponivel de cada mes, e a variacao mensal em cima dela."""
    df = df.sort_values("data").copy()
    df["mes"] = chave_mes(df["data"])
    print("cambio: de", df["data"].min().date(), "a", df["data"].max().date())
    mensal = (df.groupby("mes", as_index=False)["valor"].last()
                .rename(columns={"valor": "cambio_fim_mes"}))
    mensal["cambio_variacao_mensal_pct"] = (
        mensal["cambio_fim_mes"].pct_change() * 100)
    return mensal


def ipca_mensal(df):
    """IPCA ja e mensal. So troca o dia 01 pela chave de mes e renomeia."""
    if "valor_acumulado_12m" not in df.columns:
        raise ValueError(
            "ipca.parquet sem 'valor_acumulado_12m': rode atributos_bcb.py antes")
    df = df.copy()
    df["mes"] = chave_mes(df["data"])
    return df[["mes", "valor", "valor_extremo", "valor_acumulado_12m"]].rename(
        columns={
            "valor": "ipca_mensal",
            "valor_extremo": "ipca_extremo",
            "valor_acumulado_12m": "ipca_acumulado_12m",
        })


def conferir_chaves(esquerda, direita, nome):
    """Passo 1 da aula: a previsao do que a juncao vai fazer."""
    esq = set(esquerda["mes"])
    dir_ = set(direita["mes"])
    print(f"[selic x {nome}] so na selic: {len(esq - dir_)}"
          f" | so em {nome}: {len(dir_ - esq)} | nos dois: {len(esq & dir_)}")
    for mes in sorted(esq - dir_):
        print("   so na selic:", mes.strftime("%Y-%m"))
    for mes in sorted(dir_ - esq):
        print(f"   so em {nome}:", mes.strftime("%Y-%m"))


def juntar(esquerda, direita):
    """left primeiro; validate declara 'uma linha por mes dos dois lados'."""
    return esquerda.merge(direita, on="mes", how="left", validate="one_to_one")


def validar(esquerda, resultado, coluna_direita):
    """A conta que precisa fechar. Devolve os meses que nao casaram."""
    sem_par = resultado[coluna_direita].isna()
    print(f"   esquerda: {len(esquerda)} | resultado: {len(resultado)}"
          f" | sem par em '{coluna_direita}': {int(sem_par.sum())}")
    if len(resultado) != len(esquerda):
        print("   ATENCAO: o numero de linhas mudou.")
    return resultado[sem_par]


def juro_real(df):
    """Atributo que so existe depois da juncao: usa a Selic (uma fonte de
    series) e o IPCA acumulado (outra). Taxa real ex-post (Fisher):
    (1 + selic) / (1 + inflacao 12m) - 1, em %. Ausente onde o IPCA
    acumulado nao existe."""
    selic = df["selic_meta"] / 100
    inflacao = df["ipca_acumulado_12m"] / 100
    df["juro_real_12m"] = ((1 + selic) / (1 + inflacao) - 1) * 100
    return df


def salvar(df):
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "indicadores_mensais.parquet"
    df.to_parquet(destino, index=False)
    print("salvo em:", destino, df.shape)
    return destino


def registrar(destino, linhas_base, linhas_final, sem_par_cambio, sem_par_ipca):
    info = {
        "etapa": "enriquecimento",
        "arquivo_prata": destino.name,
        "juncao": "selic_mensal left cambio_mensal left ipca_mensal, chave 'mes'",
        "linhas_base": linhas_base,
        "linhas_resultado": linhas_final,
        "sem_par_cambio": sem_par_cambio,
        "sem_par_ipca": sem_par_ipca,
        "decisoes": [
            "selic e cambio levados de diario para mensal (ultimo valor do mes)",
            "ipca mantido mensal; chave 'mes' = primeiro dia do mes",
            "juncao left com validate one_to_one; nenhuma linha removida",
            "atributo juro_real_12m criado apos a juncao",
        ],
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
    }
    with (PRATA / "proveniencia.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")


def main():
    selic = selic_mensal(carregar("selic"))
    cambio = cambio_mensal(carregar("cambio"))
    ipca = ipca_mensal(carregar("ipca"))

    print("\n--- chaves antes da juncao ---")
    conferir_chaves(selic, cambio, "cambio")
    conferir_chaves(selic, ipca, "ipca")

    print("\n--- juncao ---")
    com_cambio = juntar(selic, cambio)
    sem_par_cambio = validar(selic, com_cambio, "cambio_fim_mes")
    resultado = juntar(com_cambio, ipca)
    sem_par_ipca = validar(selic, resultado, "ipca_mensal")
    if len(sem_par_ipca):
        print("   meses sem IPCA:",
              [m.strftime("%Y-%m") for m in sem_par_ipca["mes"]])

    # sem IPCA no mes, a marca de extremo fica ausente (nao 'False')
    resultado["ipca_extremo"] = resultado["ipca_extremo"].astype("boolean")

    resultado = juro_real(resultado)
    print("\njuro_real_12m (min, max):",
          round(resultado["juro_real_12m"].min(), 2),
          round(resultado["juro_real_12m"].max(), 2))

    destino = salvar(resultado)
    registrar(destino, len(selic), len(resultado),
              len(sem_par_cambio), len(sem_par_ipca))


if __name__ == "__main__":
    main()