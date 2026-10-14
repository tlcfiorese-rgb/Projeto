## Defeitos conhecidos das fontes

### Banco Central (BCB)
- A coluna 'valor' vem como texto (string) em todas as tres series
  (selic, cambio, ipca), pois a API devolve os numeros entre aspas.
  Isso faz o perfilador tratar 'valor' como categorico, gerando um
  grafico de dispersao ilegivel em vez de histograma.
- IPCA tem valores negativos em alguns meses, o que e esperado
  (representa deflacao), nao e erro do dado.

## Decisões de tratamento

### Banco Central (BCB) — IPCA
- Coluna 'valor' convertida de texto para numero (float).
- 6 valores marcados como extremos pelo metodo IQR (apenas 1 tambem
  pelo z-score). A diferenca e esperada: o corte do IQR e
  mais apertado, e o IPCA tem picos altos que alongam a
  cauda para cima.
- Nenhum foi removido: cada um foi investigado e corresponde a evento
  economico real. Mantidos e sinalizados na coluna 'valor_extremo':
  - 06/2018 (1,26%): greve dos caminhoneiros.
  - 12/2020 (1,35%) e 10/2021 (1,25%): picos inflacionarios da
    pandemia.
  - 03/2022 (1,62%): inicio da guerra na Ucrania.
  - 07/2022 (-0,68%): corte do ICMS sobre combustiveis, que gerou
    deflacao.
  - 02/2025 (1,31%): fim do desconto do bonus de Itaipu na conta de
    luz. A energia eletrica residencial caiu 14,21% em janeiro e
    subiu 16,80% em fevereiro, o que gerou um salto na comparacao
    mes a mes. Foi o maior IPCA de um mes de fevereiro desde 2003
    (fonte: IBGE, divulgacao de 12/03/2025).

### Banco Central (BCB) — Selic e Cambio
- Coluna 'valor' convertida de texto para numero (float).
- Nenhum extremo detectado por IQR ou z-score no periodo
  analisado (2016-2026).

## Atributos derivados

### valor_variacao_pct (selic.parquet e cambio.parquet)
Variacao percentual em relacao ao dia anterior. Serve para identificar
dias de mudanca de patamar (entrada em vigor de nova meta da Selic apos
reunioes do COPOM; valorizacao/desvalorizacao do real no cambio) em vez
de olhar so o nivel. Ausente na primeira linha de cada serie, por
definicao.
Exemplo: a coluna capturou o ciclo de alta da Selic entre 11/2024 e
06/2025 (11,25% -> 15,00%) e o inicio do ciclo de corte a partir de
03/2026.

### valor_acumulado_12m (ipca.parquet)
Inflacao acumulada em 12 meses (juros compostos), a metrica padrao de
mercado para comparar com a Selic. Ausente nos primeiros 11 meses da
serie, por definicao (nao ha 12 meses anteriores para acumular).
Valores recentes (mar-jul/2026) na faixa de 4,1% a 4,7%.