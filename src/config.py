"""Configuracao central do pipeline: caminhos, series e log.

Aqui entra so o que mudaria se alguem rodasse o projeto em outra maquina
ou com outra janela. Logica de transformacao e segredo ficam de fora.
config nao importa nenhum outro modulo do projeto."""

import logging
from pathlib import Path

# RAIZ vem da localizacao deste arquivo, entao o caminho nao depende de
# onde o terminal esta aberto (src/ ou a raiz do projeto).
RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
BRONZE = DADOS / "bronze" / "bcb"
PRATA = DADOS / "prata"
OURO = DADOS / "ouro"
BANCO = OURO / "projeto.duckdb"
RELATORIOS = RAIZ / "relatorios"

# Codigos das series no SGS do Banco Central.
SERIES = {
    "selic": 432,   # meta Selic
    "cambio": 1,    # dolar comercial (venda), USD/BRL
    "ipca": 433,    # IPCA, variacao mensal
}

# Janela movel contada a partir de hoje. A API do SGS limita a consulta
# por periodo a 10 anos por chamada: valores maiores exigem pedir em partes.
ANOS_JANELA = 10

# Tabelas da Prata que entram no banco, em ordem de dependencia.
TABELAS_PRATA = ["selic", "cambio", "ipca", "indicadores_mensais"]


def configurar_log():
    """Log na tela e em pipeline.log (que fica no .gitignore)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(RAIZ / "pipeline.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
