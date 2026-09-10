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