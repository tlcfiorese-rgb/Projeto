"""Painel: so a tela. Nenhum SQL aqui, ele mora em consultas.py.

    streamlit run dashboard/painel.py

Feche o painel antes de rodar o pipeline: o DuckDB trava o arquivo."""

from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

import consultas

MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]

# Uma cor por entidade, em todas as telas (slots 1 a 3 da paleta validada).
CORES = {
    "claro":  {"selic": "#2a78d6", "dolar": "#eb6834", "juro_real": "#1baf7a"},
    "escuro": {"selic": "#3987e5", "dolar": "#d95926", "juro_real": "#199e70"},
}


def tema():
    try:
        return "escuro" if st.context.theme.type == "dark" else "claro"
    except Exception:
        return "claro"


def numero(x, casas=2):
    """Numero no formato brasileiro: 13,75."""
    return "—" if pd.isna(x) else f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def mes_ano(data):
    return f"{MESES[data.month - 1]}/{data.year}"


def forca(r):
    if pd.isna(r):
        return "sem dados"
    r = abs(r)
    if r < 0.1:
        return "desprezível"
    if r < 0.3:
        return "fraca"
    if r < 0.5:
        return "moderada"
    return "forte"


def grafico_linha(df, coluna, titulo, cor, unidade, casas=2, zero=False):
    """Uma serie, uma cor, linha fina, cruzeta com tooltip e o ultimo valor
    escrito ao lado da linha (rotulo direto)."""
    dados = df[["mes", coluna]].dropna().copy()
    dados["rotulo_mes"] = dados["mes"].map(mes_ano)
    dados["rotulo_valor"] = dados[coluna].map(lambda v: numero(v, casas)) + " " + unidade

    base = alt.Chart(dados).encode(
        x=alt.X("mes:T", title=None, axis=alt.Axis(format="%Y", tickCount="year", grid=False)),
        y=alt.Y(f"{coluna}:Q", title=unidade,
                scale=alt.Scale(zero=zero, nice=True)),
    )
    linha = base.mark_line(color=cor, strokeWidth=2)
    marcador = alt.selection_point(nearest=True, on="pointerover", fields=["mes"],
                                   empty=False, clear="pointerout")
    pontos = base.mark_point(color=cor, size=60, filled=True, opacity=0).encode(
        opacity=alt.condition(marcador, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip("rotulo_mes:N", title="Mês"),
                 alt.Tooltip("rotulo_valor:N", title=titulo)],
    ).add_params(marcador)
    regua = alt.Chart(dados).mark_rule(color="gray", strokeWidth=1).encode(
        x="mes:T").transform_filter(marcador)
    ultimo = dados.tail(1)
    rotulo = alt.Chart(ultimo).mark_text(align="left", dx=6, fontWeight="bold",
                                         color=cor).encode(
        x="mes:T", y=f"{coluna}:Q", text="rotulo_valor:N")
    camadas = [regua, linha, pontos, rotulo]
    if zero is False and coluna == "juro_real_12m":
        camadas.insert(0, alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
            color="gray", strokeDash=[4, 4]).encode(y="y:Q"))
    return alt.layer(*camadas).properties(height=210, title=titulo).configure_view(
        stroke=None).configure_axis(gridColor="#8883", domainColor="#8886")


st.set_page_config(page_title="Selic, câmbio e IPCA", layout="wide")
cor = CORES[tema()]

st.title("Selic, câmbio e IPCA")
st.markdown("**Existe correlação entre Selic alta e valorização do real frente ao dólar, "
            "e como isso afeta o investidor de renda fixa?**")

if not consultas.BANCO.exists():
    st.error("Não achei o banco da camada Ouro. Rode `python src\\pipeline.py` "
             "na raiz do projeto e abra o painel de novo.")
    st.stop()

# --- filtro
anos = consultas.anos_disponiveis().iloc[0]
ano_ini, ano_fim = st.sidebar.slider(
    "Período (anos)", int(anos["ano_min"]), int(anos["ano_max"]),
    (int(anos["ano_min"]), int(anos["ano_max"])))
st.sidebar.caption("O filtro vale para os gráficos, as correlações e a tabela. "
                   "Os quatro números do topo mostram sempre o dado mais recente.")

serie = consultas.serie_mensal(ano_ini, ano_fim)
atual = consultas.mes_mais_recente().iloc[0]
completo = consultas.ultimo_mes_completo().iloc[0]

# --- quatro numeros
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Selic meta ({mes_ano(atual['mes'])})", f"{numero(atual['selic_meta'])}% a.a.")
c2.metric(f"Dólar ({mes_ano(atual['mes'])}, mês em curso)", f"R$ {numero(atual['cambio_fim_mes'], 2)}")
c3.metric(f"IPCA 12 meses ({mes_ano(completo['mes'])})", f"{numero(completo['ipca_acumulado_12m'])}%")
c4.metric(f"Juro real 12 meses ({mes_ano(completo['mes'])})", f"{numero(completo['juro_real_12m'])}% a.a.")

st.divider()

# --- Selic e dolar: dois graficos, nunca dois eixos no mesmo
esq, dir_ = st.columns(2)
with esq:
    st.altair_chart(grafico_linha(serie, "selic_meta", "Selic meta (% ao ano)",
                                  cor["selic"], "% a.a.", zero=True),
                    width="stretch")
with dir_:
    st.altair_chart(grafico_linha(serie, "cambio_fim_mes", "Dólar no fim do mês (R$)",
                                  cor["dolar"], "R$"),
                    width="stretch")

# --- juro real e dispersao
esq, dir_ = st.columns(2)
with esq:
    st.altair_chart(grafico_linha(serie, "juro_real_12m",
                                  "Juro real em 12 meses (% ao ano)",
                                  cor["juro_real"], "% a.a."),
                    width="stretch")
    st.caption("Juro real = (1 + Selic) / (1 + IPCA acumulado em 12 meses) − 1. "
               "É quanto o investidor de renda fixa ganha acima da inflação. "
               "Fica de fora o mês em curso, sem IPCA divulgado.")
with dir_:
    pares = serie.dropna(subset=["selic_meta", "cambio_variacao_mensal_pct"]).copy()
    pares["rotulo_mes"] = pares["mes"].map(mes_ano)
    pontos = alt.Chart(pares).mark_point(color=cor["selic"], filled=True, size=40,
                                         opacity=0.6).encode(
        x=alt.X("selic_meta:Q", title="Selic meta (% a.a.)", scale=alt.Scale(zero=False)),
        y=alt.Y("cambio_variacao_mensal_pct:Q", title="Dólar no mês (%)"),
        tooltip=[alt.Tooltip("rotulo_mes:N", title="Mês"),
                 alt.Tooltip("selic_meta:Q", title="Selic (% a.a.)", format=".2f"),
                 alt.Tooltip("cambio_variacao_mensal_pct:Q", title="Dólar (%)", format=".2f")])
    tendencia = pontos.transform_regression("selic_meta", "cambio_variacao_mensal_pct"
                                            ).mark_line(color="gray", strokeWidth=2)
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
        color="gray", strokeDash=[4, 4]).encode(y="y:Q")
    st.altair_chart(alt.layer(zero, pontos, tendencia).properties(
        height=300, title=alt.TitleParams("Selic × variação mensal do dólar", anchor="start")
    ).configure_view(stroke=None).configure_axis(gridColor="#8883", domainColor="#8886"),
        width="stretch")
    st.caption("Abaixo da linha tracejada, o dólar caiu no mês: o real se valorizou.")

# --- correlacoes
st.subheader("Correlações no período")
corr = consultas.correlacoes(ano_ini, ano_fim)
corr["leitura"] = corr["correlacao"].map(forca)
corr["correlacao"] = corr["correlacao"].map(lambda r: numero(r, 2))
st.dataframe(
    corr.rename(columns={"relacao": "Relação", "correlacao": "Correlação (r)",
                         "pares": "Meses", "leitura": "Força"}),
    hide_index=True, width="stretch")
st.markdown(
    "Valorização do real é queda do dólar, ou seja, variação mensal **negativa**. "
    "Um r negativo entre a Selic e a variação do dólar vai na direção da hipótese, "
    "mas um r perto de zero explica pouco. Correlação também não é causalidade, e "
    "a correlação entre os **níveis** das duas séries é dominada pela tendência de "
    "longo prazo, por isso não serve de evidência.")

# --- tabela e fonte
with st.expander("Ver os dados do período em tabela"):
    st.dataframe(
        serie.drop(columns=["mes"]).rename(columns={
            "ano_mes": "Mês", "selic_meta": "Selic meta (% a.a.)",
            "cambio_fim_mes": "Dólar (R$)", "cambio_variacao_mensal_pct": "Variação do dólar (%)",
            "ipca_mensal": "IPCA no mês (%)", "ipca_acumulado_12m": "IPCA 12m (%)",
            "juro_real_12m": "Juro real 12m (% a.a.)"}),
        hide_index=True, width="stretch")

prov = consultas.proveniencia()
if prov:
    extraido = datetime.fromisoformat(prov["extraido_em"]).strftime("%d/%m/%Y %H:%M")
    periodo = prov["periodo_consultado"]
    st.caption(
        f"Fonte: Banco Central do Brasil, SGS (séries {', '.join(str(c) for c in prov['series'].values())}: "
        f"Selic meta, dólar comercial e IPCA). Janela {periodo['data_inicial']} a {periodo['data_final']}, "
        f"extraída em {extraido}. {len(serie)} meses no período filtrado. "
        "Selic e dólar do mês em curso vão até a data da extração. "
        "Dados públicos e agregados, sem dado pessoal.")
else:
    st.caption("Fonte: Banco Central do Brasil, SGS. Proveniência não encontrada na Bronze.")
