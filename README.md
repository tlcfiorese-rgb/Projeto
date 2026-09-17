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
- 6 valores marcados como extremos pelo metodo IQR (1 tambem
  pelo z-score). Nenhum foi removido: correspondem a eventos
  economicos reais e documentados (greve dos caminhoneiros
  em 06/2018, pico inflacionario pos-pandemia em 12/2020 e
  10/2021, choque da guerra na Ucrania em 03/2022, corte do
  ICMS sobre combustiveis gerando deflacao em 07/2022).
  Mantidos e sinalizados na coluna 'valor_extremo'.

### Banco Central (BCB) — Selic e Cambio
- Coluna 'valor' convertida de texto para numero (float).
- Nenhum extremo detectado por IQR ou z-score no periodo
  analisado (2016-2026).

## Atributos derivados

### selic_variacao_pct / cambio_variacao_pct
Variacao percentual diaria em relacao ao dia anterior. Serve para
identificar dias de mudanca de patamar (reunioes do COPOM na Selic,
valorizacao/desvalorizacao do real no cambio) em vez de olhar so o nivel.
Exemplo: a coluna capturou corretamente o ciclo de alta da Selic entre
11/2024 e 06/2025 (11,25% -> 15,00%) e o inicio do ciclo de corte a
partir de 03/2026, com os dias de variacao coincidindo com as datas
de reuniao do COPOM.

### ipca_acumulado_12m
Inflacao acumulada em 12 meses (juros compostos), a metrica padrao de
mercado para comparar com a Selic. Ausente nos primeiros 11 meses da
serie, por definicao (nao ha 12 meses anteriores para acumular).
Valores recentes (mar-jul/2026) na faixa de 4,1% a 4,7%.