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

Com o ambiente virtual ativado (`pip install -r requirements.txt`):

    python src\pipeline.py                  # tudo, da API aos testes da Ouro
    python src\pipeline.py enriquecimento   # retoma desta etapa em diante

Etapas, em ordem: ingestao, transformacao, atributos, enriquecimento,
carga, modelagem (dbt run), testes (dbt test). Cada uma tambem roda sozinha (ex.: `python src\ingerir.py`).
O log sai na tela e em `pipeline.log` (nao versionado).

O src/explorar_bcb.py gera os relatorios de diagnostico e fica fora do
pipeline (e opcional). A bronze (JSONs brutos) nao e versionada:
recria-se com ingerir.py. O proveniencia.json da bronze e o da prata
ficam versionados.

## Estrutura do codigo

| Arquivo | Papel |
|---|---|
| src/config.py | caminhos, series, janela (ANOS_JANELA) e configuracao do log |
| src/ingerir.py | Bronze: JSON bruto datado, proveniencia, retry em timeout |
| src/transformar_bcb.py | Prata: tipos, chave, extremos (IQR e z-score) |
| src/atributos_bcb.py | Prata: atributos derivados |
| src/enriquecer_bcb.py | Prata: juncao mensal e juro_real_12m |
| src/carga.py | carrega a Prata no DuckDB e confere que chegou inteira |
| ecox14/models | projeto dbt: constroi a Ouro e descreve cada coluna (schema.yml) |
| ecox14/tests | testes de dado escritos a mao (SQL que devolve zero linhas) |
| src/pipeline.py | ordem das etapas, log, retomada |
| dashboard/consultas.py | todo o SQL de leitura do painel |
| dashboard/painel.py | so a tela (Streamlit), sem SQL |

config nao importa ninguem; as etapas importam o config; so o pipeline
importa as etapas. Segredo nenhum entra no repositorio, e o User-Agent
da ingestao e generico (sem e-mail).

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
Valores recentes (mar-out/2026) na faixa de 4,1% a 4,7%.

## Juncao
Selic, cambio e IPCA juntados por mes (chave 'mes'), com how=left a
partir da Selic e validate=one_to_one. Selic e cambio foram levados de
diario para mensal (ultimo valor do mes) antes da juncao.

- Linhas na Selic mensal: 121
- Linhas no resultado: 121
- Sem par no cambio: 0
- Sem par no IPCA: 0

### Quem nao casou
- nov/2026: o IPCA do mes corrente ainda nao foi divulgado. Mantido,
  com IPCA ausente.

Isso se repete a cada extracao: o mes em curso fica sem IPCA.
Os meses das pontas sao incompletos na Selic e no cambio, mas usamos o
ultimo valor disponivel do mes. Numeros da extracao de 18/11/2026.

### Atributo derivado apos a juncao
juro_real_12m: taxa real ex-post, (1 + Selic) / (1 + IPCA acumulado 12m)
- 1, em %. So existe depois da juncao, porque usa a Selic e o IPCA,
que vinham de tabelas separadas. Responde a pergunta norteadora: quanto
o investidor de renda fixa ganha acima da inflacao. Ausente nos
primeiros 11 meses, onde o IPCA acumulado nao existe.
Resultado: dados/prata/indicadores_mensais.parquet.

## Modelagem (camada Ouro)

A Ouro mora no DuckDB (`dados/ouro/projeto.duckdb`), em dois esquemas:
`prata` (os Parquet carregados como estao) e `ouro` (construida a partir
da prata). A camada deixa de ser so pasta e passa a ser esquema.

**Grao da fato: uma linha de `fato_indicador_mensal` e um mes.**
A chave e `mes` (primeiro dia do mes). Duplicata e o mesmo mes duas vezes.
Nao faz sentido somar Selic ou cambio entre meses: sao niveis, nao fluxos.

| Tabela | Natureza | Grao | O que guarda |
|---|---|---|---|
| ouro.fato_indicador_mensal | fato | um mes | selic_meta, cambio_fim_mes, cambio_variacao_mensal_pct, ipca_mensal, ipca_extremo, ipca_acumulado_12m, juro_real_12m |
| ouro.dim_tempo | dimensao | um mes | ano, mes_numero, trimestre, semestre, ano_mes |
| ouro.vw_indicador_completo | view | um mes | a tabela achatada: fato + dim_tempo |
| ouro.vw_correlacao_selic_dolar | view | uma linha | correlacoes que respondem a pergunta norteadora |

Ligacao: `fato_indicador_mensal.mes` aponta para `dim_tempo.mes`.
Escolha de projeto: ha uma unica dimensao, o tempo, porque as tres series
descrevem a mesma entidade (o Brasil, mes a mes). Nao ha cadastro de pais
ou de produto para virar dimensao; inventar uma seria enfeite. A fato ja
vem pronta da juncao da camada Prata (`indicadores_mensais.parquet`).

A tabela achatada nao e mantida a mao: `vw_indicador_completo` e derivada
da estrela, entao existe uma origem so.

## dbt

A construcao da Ouro e feita pelo dbt (projeto `ecox14/`, adaptador
dbt-duckdb). O dbt nao baixa dado nem le arquivo: isso continua em Python
(`carga.py` carrega a Prata no banco). Os modelos sao SELECT em
`ecox14/models`; a ordem de execucao sai dos `ref()`. O SQL de
`construir_ouro` em `carga.py` foi mantido, sem ser chamado, para comparar
os dois resultados (`python src\carga.py --sql`): as duas formas produzem
tabelas identicas.

O `profiles.yml` fica dentro de `ecox14/` (sem segredo) com caminho
relativo ao banco. Rodar so a Ouro, a mao:

    cd ecox14
    dbt run --profiles-dir .
    dbt run --select dim_tempo+ --profiles-dir .
    dbt test --profiles-dir .

Se aparecer "file is locked", outra conexao esta com o `projeto.duckdb`
aberto (VS Code, outro terminal): feche e rode de novo.

## Testes

Uma regra escrita que o computador confere sozinho, a cada execucao. Os
testes rodam na etapa `testes` do pipeline (`dbt test`): se algum falhar o
pipeline para e a Ouro nao deve ser usada. A conferencia que antes era um
`print` no `carga.py` virou teste; o `carga.py` so confere que a Prata
chegou inteira ao banco (mesma contagem de linhas que cada Parquet).

**Testes prontos**, declarados em `ecox14/models/schema.yml` e `sources.yml`:

- `unique` e `not_null` na chave de cada tabela (`mes` na fato e na
  `dim_tempo`; `data` nas tres series da Prata).
- `relationships`: todo `mes` da fato existe em `dim_tempo` (nenhuma fato
  orfa).
- `accepted_values`: mes de 1 a 12, trimestre de 1 a 4, semestre 1 ou 2,
  `ipca_extremo` verdadeiro ou falso.
- `not_null` em `selic_meta` e `cambio_fim_mes`. IPCA e juro real nao tem
  esse teste de proposito: o mes em curso fica sem IPCA.

**Testes proprios**, em `ecox14/tests` (cada um devolve as linhas que violam
a regra; passa quando devolve zero):

| Teste | O que garante |
|---|---|
| `fato_cobre_prata` | a fato tem o mesmo numero de meses que a tabela da juncao |
| `meses_sem_buraco` | nenhum mes some no meio da serie |
| `ipca_ausente_so_no_mes_corrente` | so o ultimo mes pode estar sem IPCA (regra da secao "Quem nao casou") |
| `juro_real_confere_com_fisher` | o juro real bate com a formula e so falta onde falta o IPCA 12m |
| `valores_plausiveis` | Selic, dolar e IPCA dentro de faixas largas, para pegar erro de unidade |

O grao da fato e um mes, chave simples: `unique` em `mes` ja prova que nao ha
mes repetido, sem precisar de teste proprio para chave composta.

Para ver quais linhas falharam: `dbt test --select meses_sem_buraco
--store-failures --profiles-dir .` (a partir de `ecox14/`). O dbt grava as
linhas no esquema `ouro_dbt_test__audit` do `projeto.duckdb`.

Verificado quebrando o dado de proposito (um mes apagado, um IPCA nulo no
meio, a Selic multiplicada por 100): os testes `meses_sem_buraco`,
`ipca_ausente_so_no_mes_corrente`, `fato_cobre_prata`, `valores_plausiveis` e
`juro_real_confere_com_fisher` falharam.

## Documentacao

A descricao de cada tabela e coluna fica no `schema.yml`, ao lado do teste:
nao e escrita duas vezes. Para gerar o site com o grafo dos modelos:

    cd ecox14
    dbt docs generate --profiles-dir .
    dbt docs serve --profiles-dir .

Para ver o dado em si (as linhas), o DuckDB tem uma interface no navegador.
Baixe o `duckdb.exe` para Windows em duckdb.org, descompacte na raiz do
projeto (ele esta no `.gitignore`) e rode, com o painel e o pipeline fechados:

    .\duckdb.exe -ui dados/ouro/projeto.duckdb

## Painel

    streamlit run dashboard/painel.py

O painel e consumidor da Ouro, fica fora do pipeline e abre o banco com
`read_only=True`: nao altera nada e nao trava o dbt. Feche o painel antes de
rodar o pipeline (o DuckDB trava o arquivo). O SQL esta todo em
`dashboard/consultas.py`, com valores da tela como parametro (`?`); o
`painel.py` nao tem SQL.

Mostra a Selic, o dolar e o juro real, uma dispersao entre a Selic e a
variacao mensal do dolar, as correlacoes do periodo escolhido, a tabela
dos dados e a fonte. Selic e dolar ficam em graficos separados, cada um
com seu eixo: duas escalas no mesmo grafico sugerem relacao que nao existe.

## Governanca

- **De onde veio:** cada numero tem origem registrada (`proveniencia.json`
  da Bronze e `proveniencia.jsonl` da Prata) e o rodape do painel a mostra.
- **Dado pessoal:** nenhum. As tres series sao publicas e agregadas
  (Banco Central), entao a LGPD nao se aplica ao projeto. Foi escolha de
  projeto: com dado pessoal seria preciso coletar so o necessario, dizer
  para que serve, definir prazo de descarte e controlar acesso.
- **Se o numero estiver errado:** da para reconstruir o calculo ate a
  fonte: JSON bruto datado na Bronze, decisoes de tratamento na Prata
  (proveniencia e README), SQL versionado no dbt e testes que falham antes
  de o dado chegar ao painel.

## Resultado para a pergunta norteadora

Numeros da extracao de 18/11/2026 (121 meses, 11/2016 a 11/2026). Os
valores saem de `ouro.vw_correlacao_selic_dolar` e aparecem no
`pipeline.log` ao fim da etapa testes. Valorizacao do real e queda
do USD/BRL, ou seja, variacao mensal negativa do cambio.

| Correlacao (Pearson) | Valor | Pares |
|---|---|---|
| Selic (nivel) x cambio (nivel) | 0,19 | 121 |
| Selic (nivel) x variacao mensal do cambio | -0,14 | 120 |
| Selic do mes anterior x variacao mensal do cambio | -0,13 | 120 |
| juro real 12m x variacao mensal do cambio | -0,09 | 109 |

Leitura: o sinal das tres correlacoes com a variacao do cambio e negativo,
na direcao da hipotese (Selic mais alta, dolar subindo menos ou caindo),
mas todas sao fracas: com r de -0,14, a Selic explica cerca de 2% da
variacao mensal do cambio. Os tres numeros nao sao independentes
(a Selic muda devagar, entao meses vizinhos repetem quase o mesmo valor),
e a correlacao entre os niveis (positiva, 0,19) e dominada pela tendencia
de longo prazo das duas series, por isso nao serve de evidencia. Correlacao
nao e causalidade: o cambio reage a muitos outros fatores (cenario
externo, fiscal, commodities) que a Selic sozinha nao captura.

Para o investidor de renda fixa, o ponto da pergunta e o juro real
(`juro_real_12m`): na janela, ele variou de -4,35% a 10,78% ao ano.

Limite da pergunta: nao ha no projeto serie de CDB nem de Tesouro. A Selic
serve de aproximacao do que o investidor recebe: o CDB pos-fixado paga um
percentual do CDI, que anda colado na Selic, e o Tesouro Selic paga a propria
Selic. O juro real e ex-post (usa a inflacao ja ocorrida) e antes de imposto e
taxas, entao e um teto do ganho real, nao o ganho liquido.
