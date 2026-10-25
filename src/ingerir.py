from pathlib import Path
from datetime import date, datetime, timedelta
import json
import requests

URL_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

BRONZE = Path("dados/bronze/bcb")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

SERIES = {
    "selic": 432,
    "cambio": 1,
    "ipca": 433,
}

HOJE = date.today()

def dez_anos_antes(d):
    """Mesmo dia, 10 anos atras (29/02 vira 28/02)."""
    try:
        return d.replace(year=d.year - 10)
    except ValueError:
        return d.replace(year=d.year - 10, day=28)


DATA_FINAL = HOJE.strftime("%d/%m/%Y")
DATA_INICIAL = (dez_anos_antes(HOJE) + timedelta(days=1)).strftime("%d/%m/%Y")

    # Chama a API do BC e traz os dados brutos
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


    # Confere se a resposta não veio vazia, antes de salvar
def conferir(dados, nome_serie): 
    """Confere se a resposta veio como esperado antes de salvar."""
    print(f"{nome_serie}: {len(dados)} registros recebidos")
    if len(dados) == 0:
        raise ValueError(f"{nome_serie} veio vazia, verifique a URL/datas")
    return dados

    # Grava o JSON bruto, com data no nome do arquivo
def salvar(dados, nome_serie):
    """Salva o JSON bruto na bronze, exatamente como veio da fonte."""
    BRONZE.mkdir(parents=True, exist_ok=True)
    hoje = date.today().strftime("%Y%m%d")
    destino = BRONZE / f"{nome_serie}_{hoje}.json"
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2))
    print(f"{nome_serie}: salvo em {destino}")
    return destino

    # Escreve o arquivo de proveniencia: de onde veio, quando foi extraído
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