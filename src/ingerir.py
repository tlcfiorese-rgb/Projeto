from pathlib import Path
from datetime import date, datetime
import json
import requests

URL_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
# Este script roda de DENTRO de dados/bronze, entao o caminho eh so ate "bcb"
BRONZE = Path("bcb")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

SERIES = {
    "selic": 432,
    "cambio": 1,
    "ipca": 433,
}

DATA_INICIAL = "16/08/2016"
DATA_FINAL = "15/08/2026"


def buscar(codigo):
    """Busca uma serie na API do Banco Central, sem alterar nada."""
    params = {
        "formato": "json",
        "dataInicial": DATA_INICIAL,
        "dataFinal": DATA_FINAL,
    }
    r = requests.get(
        URL_BASE.format(codigo=codigo),
        params=params,
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def conferir(dados, nome_serie):
    """Confere se a resposta veio como esperado antes de salvar."""
    print(f"{nome_serie}: {len(dados)} registros recebidos")
    if len(dados) == 0:
        raise ValueError(f"{nome_serie} veio vazia, verifique a URL/datas")
    return dados


def salvar(dados, nome_serie):
    """Salva o JSON bruto na bronze, exatamente como veio da fonte."""
    BRONZE.mkdir(parents=True, exist_ok=True)
    hoje = date.today().strftime("%Y%m%d")
    destino = BRONZE / f"{nome_serie}_{hoje}.json"
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2))
    print(f"{nome_serie}: salvo em {destino}")
    return destino


def registrar(arquivos_gerados):
    """Registra a proveniencia de toda a extracao (as tres series juntas)."""
    info = {
        "fonte": "Banco Central do Brasil - Sistema Gerenciador de Series Temporais (SGS)",
        "url_base": URL_BASE,
        "series": SERIES,
        "periodo_consultado": {
            "data_inicial": DATA_INICIAL,
            "data_final": DATA_FINAL,
        },
        "arquivos_bronze": [a.name for a in arquivos_gerados],
        "extraido_em": datetime.now().isoformat(),
    }
    (BRONZE / "proveniencia.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2)
    )
    print("proveniencia registrada em", BRONZE / "proveniencia.json")


def main():
    arquivos_gerados = []
    for nome_serie, codigo in SERIES.items():
        dados = buscar(codigo)
        dados = conferir(dados, nome_serie)
        destino = salvar(dados, nome_serie)
        arquivos_gerados.append(destino)
    registrar(arquivos_gerados)


if __name__ == "__main__":
    main()