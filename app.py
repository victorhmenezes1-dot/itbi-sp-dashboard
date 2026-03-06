"""
app.py
Dashboard ITBI São Paulo — Tabela Dinâmica Interativa
Powered by Streamlit + DuckDB

Rodar: streamlit run app.py
"""

import time
from pathlib import Path
from urllib.parse import quote

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

# ─── Configuração ─────────────────────────────────────────────────────────────

# Fonte de dados: MotherDuck na nuvem ou Parquet local (fallback)
_LOCAL_PARQUET = Path(__file__).parent / "data" / "itbi_consolidado.parquet"
_USE_MOTHERDUCK = "MOTHERDUCK_TOKEN" in st.secrets

if _USE_MOTHERDUCK:
    TABLE = "itbi.main.transacoes"
else:
    TABLE = f"'{_LOCAL_PARQUET}'"

MESES_NOME = {
    1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun",
    7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def fmt_brl(v):
    if pd.isna(v): return "—"
    return f"R$ {v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_num(v):
    if pd.isna(v): return "—"
    return f"{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_resource
def get_connection():
    if _USE_MOTHERDUCK:
        token = st.secrets["MOTHERDUCK_TOKEN"]
        con = duckdb.connect(f"md:itbi?motherduck_token={token}")
    else:
        con = duckdb.connect()
    con.execute("SET memory_limit='400MB'")
    return con

def query(sql: str) -> pd.DataFrame:
    return get_connection().execute(sql).fetchdf()


@st.cache_data(show_spinner=False)
def carregar_opcoes():
    anos     = query(f"SELECT DISTINCT ano FROM {TABLE} WHERE ano IS NOT NULL ORDER BY ano")["ano"].tolist()
    bairros  = query(f"""
        SELECT bairro, COUNT(*) AS n FROM {TABLE}
        WHERE bairro IS NOT NULL
        GROUP BY bairro ORDER BY n DESC LIMIT 500
    """)["bairro"].tolist()
    naturezas = query(f"""
        SELECT DISTINCT natureza_transacao FROM {TABLE}
        WHERE natureza_transacao IS NOT NULL
        ORDER BY natureza_transacao
    """)["natureza_transacao"].tolist()
    val_range = query(f"""
        SELECT MIN(valor_transacao), MAX(valor_transacao) FROM {TABLE}
        WHERE valor_transacao > 0
    """).iloc[0].tolist()
    return anos, bairros, naturezas, val_range


def build_where(anos, meses, bairros, naturezas, val_min, val_max) -> str:
    conds = ["valor_transacao > 0"]
    if anos:
        conds.append(f"ano IN ({', '.join(str(a) for a in anos)})")
    if meses:
        conds.append(f"mes IN ({', '.join(str(m) for m in meses)})")
    if bairros:
        b_str = ", ".join(f"$${b}$$" for b in bairros)
        conds.append(f"bairro IN ({b_str})")
    if naturezas:
        n_str = ", ".join(f"$${n}$$" for n in naturezas)
        conds.append(f"natureza_transacao IN ({n_str})")
    conds.append(f"valor_transacao BETWEEN {val_min} AND {val_max}")
    return "WHERE " + " AND ".join(conds)


# ─── Layout ───────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ITBI São Paulo",
    page_icon="🏠",
    layout="wide",
)

st.title("🏠 ITBI São Paulo — Análise de Dados")
st.caption("Fonte: Prefeitura de São Paulo – Secretaria Municipal da Fazenda · 2009–2025")

# Verificar fonte de dados
if not _USE_MOTHERDUCK and not _LOCAL_PARQUET.exists():
    st.error(
        f"Arquivo não encontrado: `{_LOCAL_PARQUET}`\n\n"
        "Execute primeiro: `python baixar_dados.py`"
    )
    st.stop()

# ─── Sidebar: Filtros ─────────────────────────────────────────────────────────

with st.sidebar:
    st.header("🔍 Filtros")

    with st.spinner("Carregando opções..."):
        anos_opts, bairros_opts, nat_opts, val_range = carregar_opcoes()

    sel_anos = st.multiselect(
        "Ano", anos_opts,
        default=anos_opts[-3:] if len(anos_opts) >= 3 else anos_opts,
        help="Deixe vazio para todos os anos",
    )

    sel_meses = st.multiselect(
        "Mês", list(range(1, 13)),
        format_func=lambda m: MESES_NOME[m],
        help="Deixe vazio para todos os meses",
    )

    sel_bairros = st.multiselect(
        "Bairro / Distrito",
        bairros_opts,
        help="Top 500 bairros por volume. Deixe vazio para todos.",
    )

    sel_naturezas = st.multiselect(
        "Natureza de Transação",
        nat_opts,
        help="Deixe vazio para todas.",
    )

    val_min_raw = int(val_range[0] or 0)
    val_max_raw = 99_000_000_000

    col_a, col_b = st.columns(2)
    with col_a:
        val_min = st.number_input("Valor mín. (R$)", 0, val_max_raw, 0, step=50_000)
    with col_b:
        val_max = st.number_input("Valor máx. (R$)", 0, val_max_raw, val_max_raw, step=50_000)

    st.divider()
    top_n = st.slider("Quantidade de transações exibidas", 10, 500, 50)


# ─── Maiores Transações ───────────────────────────────────────────────────────

st.subheader(f"🏆 Maiores Transações (top {top_n})")

where = build_where(sel_anos, sel_meses, sel_bairros, sel_naturezas, val_min, val_max)

sql_top = f"""
SELECT
    STRFTIME(data_transacao, '%d/%m/%Y')                        AS data,
    ano,
    mes,
    logradouro,
    numero,
    bairro,
    natureza_transacao                                          AS natureza,
    valor_transacao,
    valor_venal_referencia,
    area_terreno,
    area_construida,
    CASE WHEN area_construida > 0
         THEN valor_transacao / area_construida END             AS preco_m2,
    uso_descricao,
    padrao_descricao,
    sql
FROM {TABLE}
{where}
ORDER BY valor_transacao DESC
LIMIT {top_n}
"""

t0 = time.perf_counter()
try:
    df_top = query(sql_top)
    elapsed = time.perf_counter() - t0
except Exception as e:
    st.error(f"Erro na consulta: {e}")
    st.stop()

st.caption(
    f"⏱ {elapsed:.3f}s · "
    f"Filtros: anos={sel_anos or 'todos'} · "
    f"meses={[MESES_NOME[m] for m in sel_meses] if sel_meses else 'todos'}"
)

if df_top.empty:
    st.info("Nenhuma transação encontrada com os filtros selecionados.")
else:
    df_top_exib = df_top.copy()
    df_top_exib["mes"] = df_top_exib["mes"].map(MESES_NOME).fillna(df_top_exib["mes"])

    def maps_url(row):
        parts = [
            str(row.get("logradouro") or ""),
            str(row.get("numero") or ""),
            str(row.get("bairro") or ""),
            "São Paulo SP",
        ]
        query = quote(" ".join(p for p in parts if p and p != "None"))
        return f"https://www.google.com/maps/search/?api=1&query={query}"

    df_top_exib["mapa"] = df_top_exib.apply(maps_url, axis=1)

    df_top_exib = df_top_exib.rename(columns={
        "data":                   "Data",
        "ano":                    "Ano",
        "mes":                    "Mês",
        "logradouro":             "Logradouro",
        "numero":                 "Número",
        "bairro":                 "Bairro",
        "natureza":               "Natureza",
        "valor_transacao":        "Valor Transação (R$)",
        "valor_venal_referencia": "Valor Venal Ref. (R$)",
        "area_terreno":           "Área Terreno (m²)",
        "area_construida":        "Área Construída (m²)",
        "preco_m2":               "R$/m²",
        "uso_descricao":          "Uso",
        "padrao_descricao":       "Padrão",
        "sql":                    "SQL",
        "mapa":                   "Mapa",
    })

    fmt_cols = {}
    if "Valor Transação (R$)" in df_top_exib.columns:
        fmt_cols["Valor Transação (R$)"] = lambda v: fmt_brl(v) if pd.notna(v) else "—"
    if "Valor Venal Ref. (R$)" in df_top_exib.columns:
        fmt_cols["Valor Venal Ref. (R$)"] = lambda v: fmt_brl(v) if pd.notna(v) else "—"
    if "R$/m²" in df_top_exib.columns:
        fmt_cols["R$/m²"] = lambda v: fmt_brl(v) if pd.notna(v) else "—"
    if "Área Terreno (m²)" in df_top_exib.columns:
        fmt_cols["Área Terreno (m²)"] = lambda v: f"{v:,.1f}" if pd.notna(v) else "—"
    if "Área Construída (m²)" in df_top_exib.columns:
        fmt_cols["Área Construída (m²)"] = lambda v: f"{v:,.1f}" if pd.notna(v) else "—"

    col_order_top = [
        "Mapa", "Data", "Ano", "Mês", "Logradouro", "Número", "Bairro",
        "Valor Transação (R$)", "R$/m²", "Área Construída (m²)", "Natureza",
        "Valor Venal Ref. (R$)", "Área Terreno (m²)", "Padrão", "Uso", "SQL",
    ]
    col_order_top = [c for c in col_order_top if c in df_top_exib.columns]
    df_top_exib = df_top_exib[col_order_top]

    st.dataframe(
        df_top_exib.style.format(fmt_cols),
        use_container_width=True,
        height=600,
        column_config={
            "Mapa": st.column_config.LinkColumn(
                "Mapa",
                display_text="🗺️",
                help="Abrir no Google Maps",
            ),
        },
    )

    csv_top = df_top.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        "⬇️ Exportar CSV",
        csv_top,
        file_name="itbi_maiores_transacoes.csv",
        mime="text/csv",
    )


# ─── Gráfico: Evolução de Preço por m² ───────────────────────────────────────

st.divider()
st.subheader("📈 Evolução de Preço por m² (R$/m²)")
st.caption("Mediana do preço por m² construído ao longo dos anos, por bairro.")

with st.expander("Filtros do gráfico", expanded=True):
    gc1, gc2, gc3 = st.columns([3, 2, 2])
    with gc1:
        g_bairros = st.multiselect(
            "Bairros", bairros_opts,
            default=bairros_opts[:5] if len(bairros_opts) >= 5 else bairros_opts,
            key="g_bairros",
            help="Selecione os bairros para comparar. Top 500 por volume.",
        )
    with gc2:
        g_anos = st.multiselect(
            "Anos", anos_opts,
            default=anos_opts,
            key="g_anos",
            help="Deixe vazio para todos os anos.",
        )
    with gc3:
        g_min_n = st.slider(
            "Mínimo de transações (por bairro/ano)", 1, 500, 30,
            key="g_min_n",
            help="Oculta bairros com menos de N transações naquele ano.",
        )

if g_bairros:
    bairros_str = ", ".join(f"$${b}$$" for b in g_bairros)
    anos_str_g  = (
        f"AND ano IN ({', '.join(str(a) for a in g_anos)})" if g_anos else ""
    )
    sql_m2 = f"""
    SELECT
        bairro,
        ano,
        MEDIAN(valor_transacao / area_construida) AS preco_m2_mediana,
        COUNT(*) AS n_transacoes
    FROM {TABLE}
    WHERE bairro IN ({bairros_str})
      AND area_construida > 0
      AND valor_transacao > 0
      {anos_str_g}
    GROUP BY bairro, ano
    HAVING COUNT(*) >= {g_min_n}
    ORDER BY bairro, ano
    """
    try:
        df_m2 = query(sql_m2)
        if df_m2.empty:
            st.info("Nenhum bairro atende aos filtros selecionados. Reduza o mínimo de transações ou selecione mais bairros.")
        else:
            fig_m2 = px.line(
                df_m2,
                x="ano",
                y="preco_m2_mediana",
                color="bairro",
                markers=True,
                title="Evolução da Mediana do Preço por m² por Bairro",
                labels={
                    "ano": "Ano",
                    "preco_m2_mediana": "R$/m² (mediana)",
                    "bairro": "Bairro",
                },
                template="plotly_white",
            )
            fig_m2.update_yaxes(tickprefix="R$ ", tickformat=",.0f")
            fig_m2.update_xaxes(dtick=1)
            fig_m2.update_layout(height=520, legend_title_text="Bairro")
            st.plotly_chart(fig_m2, use_container_width=True)

            csv_m2 = df_m2.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                "⬇️ Exportar dados do gráfico (CSV)",
                csv_m2,
                file_name="itbi_preco_m2.csv",
                mime="text/csv",
                key="export_m2",
            )
    except Exception as e:
        st.warning(f"Erro ao gerar gráfico: {e}")
else:
    st.info("Selecione ao menos um bairro nos filtros do gráfico.")

# ─── KPIs rápidos ─────────────────────────────────────────────────────────────

st.divider()
st.subheader("📌 Totais do período filtrado")

kpi_sql = f"""
SELECT
    COUNT(*)                    AS total_transacoes,
    SUM(valor_transacao)        AS valor_total,
    AVG(valor_transacao)        AS ticket_medio,
    MEDIAN(valor_transacao)     AS mediana,
    MIN(data_transacao)::DATE   AS data_inicio,
    MAX(data_transacao)::DATE   AS data_fim
FROM {TABLE}
{where}
"""
kpi = query(kpi_sql).iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de Transações", fmt_num(kpi["total_transacoes"]))
c2.metric("Valor Total",          fmt_brl(kpi["valor_total"]))
c3.metric("Ticket Médio",         fmt_brl(kpi["ticket_medio"]))
c4.metric("Mediana",              fmt_brl(kpi["mediana"]))

st.caption(
    f"Período: {kpi['data_inicio']} → {kpi['data_fim']}"
    if pd.notna(kpi.get("data_inicio")) else ""
)

# ─── Busca por Logradouro ─────────────────────────────────────────────────────

st.divider()
st.subheader("🔎 Busca por Logradouro")
st.caption("Digite parte do nome da rua para ver todas as transações registradas.")

row1_c1, row1_c2, row1_c3 = st.columns([3, 1, 3])
with row1_c1:
    termo = st.text_input("Nome da rua (parcial)", placeholder="Ex: PAULISTA, AUGUSTA, FARIA LIMA")
with row1_c2:
    numero_busca = st.text_input("Número", placeholder="Ex: 1000", help="Deixe vazio para todos os números")
with row1_c3:
    ref_busca = st.text_input("Referência (parcial)", placeholder="Ex: TORRE A, BLOCO, APTO", help="Busca no campo referência do imóvel")

row2_c1, row2_c2 = st.columns([3, 1])
with row2_c1:
    anos_busca = st.multiselect(
        "Filtrar por ano", anos_opts, key="busca_anos",
        help="Deixe vazio para todos os anos",
    )
with row2_c2:
    limite = st.number_input("Máx. linhas", 10, 2000, 200, key="busca_lim")

if termo.strip() or ref_busca.strip():
    termo_upper = termo.strip().upper()
    ref_upper   = ref_busca.strip().upper()

    conds_busca = ["valor_transacao > 0"]
    if termo_upper:
        conds_busca.append(f"logradouro ILIKE '%{termo_upper}%'")
    if numero_busca.strip():
        conds_busca.append(f"CAST(numero AS VARCHAR) = '{numero_busca.strip()}'")
    if ref_upper:
        conds_busca.append(f"referencia ILIKE '%{ref_upper}%'")
    if anos_busca:
        conds_busca.append(f"ano IN ({', '.join(str(a) for a in anos_busca)})")

    sql_busca = f"""
    SELECT
        logradouro,
        numero,
        complemento,
        referencia,
        bairro,
        ano,
        mes,
        natureza_transacao,
        data_transacao::DATE        AS data_transacao,
        valor_transacao,
        valor_venal_referencia,
        proporcao_transmitida,
        area_terreno,
        area_construida,
        sql
    FROM {TABLE}
    WHERE {' AND '.join(conds_busca)}
    ORDER BY data_transacao DESC
    LIMIT {limite}
    """

    t0 = time.perf_counter()
    try:
        df_busca = query(sql_busca)
        elapsed_busca = time.perf_counter() - t0
    except Exception as e:
        st.error(f"Erro na busca: {e}")
        df_busca = pd.DataFrame()

    if df_busca.empty:
        desc = termo_upper or ref_upper
        st.info(f"Nenhuma transação encontrada para **{desc}**.")
    else:
        # Totais do resultado
        total_b = len(df_busca)
        soma_b  = df_busca["valor_transacao"].sum()
        media_b = df_busca["valor_transacao"].mean()

        kb1, kb2, kb3, kb4 = st.columns(4)
        kb1.metric("Transações encontradas", fmt_num(total_b))
        kb2.metric("Valor total", fmt_brl(soma_b))
        kb3.metric("Ticket médio", fmt_brl(media_b))
        kb4.metric("Ruas únicas", fmt_num(df_busca["logradouro"].nunique()))

        st.caption(f"⏱ {elapsed_busca:.3f}s · mostrando até {limite} registros mais recentes")

        # Calcular R$/m²
        df_busca["preco_m2"] = df_busca.apply(
            lambda r: r["valor_transacao"] / r["area_construida"]
            if pd.notna(r["area_construida"]) and r["area_construida"] > 0
            else None,
            axis=1,
        )

        # Formatar para exibição
        df_exib = df_busca.copy()
        df_exib["mes"] = df_exib["mes"].map(MESES_NOME).fillna(df_exib["mes"])
        df_exib["valor_transacao"]      = df_exib["valor_transacao"].apply(fmt_brl)
        df_exib["valor_venal_referencia"] = df_exib["valor_venal_referencia"].apply(
            lambda v: fmt_brl(v) if pd.notna(v) else "—"
        )
        df_exib["preco_m2"] = df_exib["preco_m2"].apply(
            lambda v: fmt_brl(v) if pd.notna(v) else "—"
        )

        df_exib = df_exib.rename(columns={
            "logradouro":             "Logradouro",
            "numero":                 "Número",
            "complemento":            "Complemento",
            "referencia":             "Referência",
            "bairro":                 "Bairro",
            "ano":                    "Ano",
            "mes":                    "Mês",
            "natureza_transacao":     "Natureza",
            "data_transacao":         "Data",
            "valor_transacao":        "Valor Transação",
            "valor_venal_referencia": "Valor Venal Ref.",
            "proporcao_transmitida":  "% Transmitido",
            "area_terreno":           "Área Terreno (m²)",
            "area_construida":        "Área Construída (m²)",
            "preco_m2":               "R$/m²",
            "sql":                    "SQL",
        })

        # Ordenar colunas: R$/m² logo após Valor Transação
        col_order = [
            "Logradouro", "Número", "Complemento", "Referência", "Bairro",
            "Ano", "Mês", "Natureza", "Data",
            "Valor Transação", "R$/m²", "Valor Venal Ref.", "% Transmitido",
            "Área Terreno (m²)", "Área Construída (m²)", "SQL",
        ]
        col_order = [c for c in col_order if c in df_exib.columns]
        df_exib = df_exib[col_order]

        st.dataframe(df_exib, use_container_width=True, height=450)

        # Export
        csv_busca = df_busca.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            "⬇️ Exportar resultado da busca (CSV)",
            csv_busca,
            file_name=f"itbi_rua_{termo_upper.replace(' ', '_')}.csv",
            mime="text/csv",
            key="export_busca",
        )
else:
    st.info("Digite o nome de uma rua ou uma referência acima para pesquisar.")
