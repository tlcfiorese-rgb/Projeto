import pandas as pd

CAMINHO = "dados/bronze/cambio.csv"
df = pd.read_csv(CAMINHO)
print(df.shape)
for coluna in df.columns:
    print(f'"{coluna}"')

CAMINHO1 = "dados/bronze/ipca.csv"
df1 = pd.read_csv(CAMINHO1)
print(df1.shape)
for coluna in df1.columns:
    print(f'"{coluna}"')

CAMINHO2 = "dados/bronze/selic.csv"
df2 = pd.read_csv(CAMINHO2)
print(df2.shape)
for coluna in df2.columns:
    print(f'"{coluna}"')

# ESPERADAS = ["data", "valor"]
# faltando = [c for c in ESPERADAS if c not in df.columns]
# print("Nao encontradas:", faltando)

def carregar():
    return pd.read_csv(CAMINHO)

def conferir_estrutura(df):
    print(df.shape)
    print(df.dtypes)

if __name__ == "__main__":
    conferir_estrutura(carregar())