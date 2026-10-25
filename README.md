# Selic, cambio e IPCA: juros e o investidor de renda fixa

Pergunta norteadora: existe correlacao entre Selic alta e valorizacao
do real frente ao dolar, e como isso afeta o investidor de renda fixa
que aplica em CDB/Tesouro?

## Fontes

| Fonte | Formato | Acesso | Series |
|---|---|---|---|
| Banco Central do Brasil (SGS) | JSON | API aberta, sem chave | Selic meta (432), cambio USD/BRL (1), IPCA mensal (433) |

Janela de extracao: ultimos 10 anos ate a data em que o script roda.
Fonte secundaria candidata: CVM Dados Abertos (Informe Diario de
fundos), ainda nao ingerida.

## Como rodar

    python src/ingerir.py
    python src/transformar_bcb.py
    python src/atributos_bcb.py
    python src/enriquecer_bcb.py

O src/explorar_bcb.py gera os relatorios de diagnostico e e opcional.
A bronze (JSONs brutos) nao e versionada: recria-se com ingerir.py.
O proveniencia.json da bronze e o da prata ficam versionados.

## Defeitos conhecidos das fontes

### Banco Central (BCB)
- A coluna 'valor' vem como texto (string) em todas as tres series
  (selic, cambio, ipca), pois a API devolve os numeros entre aspas.
  Isso faz o perfilador tratar 'valor' como categorico, gerando um
  grafico de dispersao ilegivel em vez de histograma.
- IPCA tem valores negativos em alguns meses, o que e esperado
  (representa deflacao), nao e erro do dado.
- A API devolve resposta vazia (status 200, sem corpo) quando a
  requisicao nao traz um User-Agent de navegador. O ingerir.py envia
  esse cabecalho.
- A consulta por periodo e limitada a 10 anos por chamada.

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

## Juncao
Selic, cambio e IPCA juntados por mes (chave 'mes'), com how=left a
partir da Selic e validate=one_to_one. Selic e cambio foram levados de
diario para mensal (ultimo valor do mes) antes da juncao.

- Linhas na Selic mensal: 121
- Linhas no resultado: 121
- Sem par no cambio: 0
- Sem par no IPCA: 0

### Quem nao casou
- out/2026: o IPCA do mes corrente ainda nao foi divulgado. Mantido,
  com IPCA ausente.

Isso se repete a cada extracao: o mes em curso fica sem IPCA.
Os meses das pontas sao incompletos na Selic e no cambio, mas usamos o
ultimo valor disponivel do mes. Numeros da extracao de 25/10/2026.

### Atributo derivado apos a juncao
juro_real_12m: taxa real ex-post, (1 + Selic) / (1 + IPCA acumulado 12m)
- 1, em %. So existe depois da juncao, porque usa a Selic e o IPCA,
que vinham de tabelas separadas. Responde a pergunta norteadora: quanto
o investidor de renda fixa ganha acima da inflacao. Ausente nos
primeiros 11 meses, onde o IPCA acumulado nao existe.
Resultado: dados/prata/indicadores_mensais.parquet.