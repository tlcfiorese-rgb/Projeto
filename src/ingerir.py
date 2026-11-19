"""Ingestao (Bronze): baixa as series do SGS e grava o JSON bruto, datado."""

import json
import logging
import time
from datetime import date, datetime, timedelta

import requests

from config import ANOS_JANELA, BRONZE, SERIES

log = logging.getLogger(__name__)

URL_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

# Sem um User-Agent de navegador a API responde 200 com corpo vazio.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

TENTATIVAS = 3
ESPERA_BASE_S = 2


def anos_antes(d, anos):
    """Mesmo dia, 'anos' anos atras (29/02 vira 28/02)."""
    try:
        return d.replace(year=d.year - anos)
    except ValueError:
        return d.replace(year=d.year - anos, day=28)


def periodo(hoje=None):
    """Janela movel: de (hoje - ANOS_JANELA + 1 dia) ate hoje, em dd/mm/aaaa."""
    hoje = hoje or date.today()
    inicial = anos_antes(hoje, ANOS_JANELA) + timedelta(days=1)
    return inicial.strftime("%d/%m/%Y"), hoje.strftime("%d/%m/%Y")


def buscar(codigo, data_inicial, data_final):
    """Busca uma serie na API do Banco Central, sem alterar nada.
    Repete em caso de timeout, com espera crescente; outros erros sobem."""
    params = {
        "formato": "json",
        "dataInicial": data_inicial,
        "dataFinal": data_final,
    }
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            r = requests.get(
                URL_BASE.format(codigo=codigo),
                params=params,
                headers=HEADERS,
                timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            if tentativa == TENTATIVAS:
                log.error("serie %s: timeout nas %d tentativas", codigo, TENTATIVAS)
                raise
            espera = ESPERA_BASE_S * 2 ** (tentativa - 1)
            log.warning("serie %s: timeout (tentativa %d/%d), nova tentativa em %ds",
                        codigo, tentativa, TENTATIVAS, espera)
            time.sleep(espera)


def conferir(dados, nome_serie):
    """Confere se a resposta veio como esperado antes de salvar."""
    log.info("%s: %d registros recebidos", nome_serie, len(dados))
    if len(dados) == 0:
        raise ValueError(f"{nome_serie} veio vazia, verifique a URL/datas")
    return dados


def salvar(dados, nome_serie):
    """Salva o JSON bruto na bronze, exatamente como veio da fonte."""
    BRONZE.mkdir(parents=True, exist_ok=True)
    hoje = date.today().strftime("%Y%m%d")
    destino = BRONZE / f"{nome_serie}_{hoje}.json"
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    log.info("%s: salvo em %s", nome_serie, destino)
    return destino


def registrar(arquivos_gerados, data_inicial, data_final):
    """Registra a proveniencia de toda a extracao (as tres series juntas)."""
    info = {
        "fonte": "Banco Central do Brasil - Sistema Gerenciador de Series Temporais (SGS)",
        "url_base": URL_BASE,
        "series": SERIES,
        "periodo_consultado": {
            "data_inicial": data_inicial,
            "data_final": data_final,
        },
        "arquivos_bronze": [a.name for a in arquivos_gerados],
        "extraido_em": datetime.now().isoformat(),
    }
    destino = BRONZE / "proveniencia.json"
    destino.write_text(json.dumps(info, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    log.info("proveniencia registrada em %s", destino)


def main():
    data_inicial, data_final = periodo()
    log.info("janela: %s a %s", data_inicial, data_final)
    arquivos_gerados = []
    for nome_serie, codigo in SERIES.items():
        dados = buscar(codigo, data_inicial, data_final)
        dados = conferir(dados, nome_serie)
        arquivos_gerados.append(salvar(dados, nome_serie))
    registrar(arquivos_gerados, data_inicial, data_final)


if __name__ == "__main__":
    from config import configurar_log
    configurar_log()
    main()
