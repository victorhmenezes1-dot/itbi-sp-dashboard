#!/usr/bin/env python3
"""
baixar_dados.py
Baixa os xlsx de ITBI da Prefeitura de SP (2009–2025),
consolida e exporta como Parquet para uso com DuckDB.

Uso:
    python baixar_dados.py              # processa todos os anos
    python baixar_dados.py --anos 2023 2024 2025
"""

import argparse
import io
import time
from pathlib import Path

import pandas as pd
import requests

# ─── Configuração ─────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR  = DATA_DIR / "raw"

ARQUIVOS = {
    2009: "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/guias_de_itbi_pagas_2009.xlsx",
    2010: "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/guias_de_itbi_pagas_2010.xlsx",
    2011: "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/guias_de_itbi_pagas_2011.xlsx",
    2012: "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/guias_de_itbi_pagas_2012.xlsx",
    2013: "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/guias_de_itbi_pagas_2013.xlsx",
    2014: "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/guias_de_itbi_pagas_2014.xlsx",
    2015: "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/guias_de_itbi_pagas_2015.xlsx",
    2016: "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/guias_de_itbi_pagas_2016.xlsx",
    2017: "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/guias_de_itbi_pagas_2017.xlsx",
    2018: "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/guias_de_itbi_pagas_2018.xlsx",
    2019: "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/ITBI_Setembro_2022/GUIAS_DE_ITBI_PAGAS_(2019).xlsx",
    2020: "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/ITBI_Setembro_2022/GUIAS_DE_ITBI_PAGAS_(2020).xlsx",
    2021: "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/ITBI_Setembro_2022/GUIAS_DE_ITBI_PAGAS_(2021).xlsx",
    2022: "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/XLSX/GUIAS_DE_ITBI_PAGAS_12-2022.xlsx",
    2023: "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/XLSX/GUIAS-DE-ITBI-PAGAS-2023.xlsx",
    2024: "https://prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/GUIAS-DE-ITBI-PAGAS-2024.xlsx",
    2025: "https://prefeitura.sp.gov.br/cidade/secretarias/upload/fazenda/arquivos/itbi/GUIAS%20DE%20ITBI%20PAGAS%20%2828012026%29%20XLS.xlsx",
    2026: "https://prefeitura.sp.gov.br/documents/d/fazenda/guias-de-itbi-pagas-xlsx-1",
}

# Colunas posicionais — iguais em todos os anos (28 colunas)
COL_NAMES = [
    "sql", "logradouro", "numero", "complemento", "bairro", "referencia",
    "cep", "natureza_transacao", "valor_transacao", "data_transacao",
    "valor_venal_referencia", "proporcao_transmitida", "valor_venal_referencia_proporcional",
    "base_calculo", "tipo_financiamento", "valor_financiado", "cartorio",
    "matricula", "situacao_sql", "area_terreno", "testada", "fracao_ideal",
    "area_construida", "uso_codigo", "uso_descricao", "padrao_codigo",
    "padrao_descricao", "_col27",
]

# Colunas que serão mantidas no Parquet final
KEEP = [
    "ano", "mes",
    "sql", "logradouro", "numero", "complemento", "referencia", "bairro",
    "natureza_transacao", "valor_transacao", "data_transacao",
    "valor_venal_referencia", "proporcao_transmitida",
    "area_terreno", "area_construida",
    "uso_descricao", "padrao_descricao",
]

ABAS_SKIP = {"LEGENDA", "EXPLICACOES", "EXPLICAÇÕES", "TABELA DE USOS",
             "TABELA DE PADROES", "TABELA DE PADRÕES"}

MESES_PT = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
}

HTTP_HEADERS = {"User-Agent": "Mozilla/5.0"}

# ─── Download ─────────────────────────────────────────────────────────────────

def baixar(ano: int, url: str) -> Path:
    dest = RAW_DIR / f"itbi_{ano}.xlsx"
    if dest.exists():
        print(f"  [{ano}] Arquivo já existe ({dest.stat().st_size/1e6:.1f} MB), pulando download.")
        return dest

    print(f"  [{ano}] Baixando... ", end="", flush=True)
    t0 = time.time()
    r = requests.get(url, timeout=240, headers=HTTP_HEADERS)
    r.raise_for_status()
    dest.write_bytes(r.content)
    print(f"{len(r.content)/1e6:.1f} MB em {time.time()-t0:.0f}s")
    return dest

# ─── Leitura e padronização ───────────────────────────────────────────────────

def _tem_header(primeira_celula) -> bool:
    """Retorna True se a primeira célula da planilha é texto (= tem cabeçalho)."""
    if not isinstance(primeira_celula, str):
        return False
    # Se for numérico disfarçado de string, não é header
    try:
        float(str(primeira_celula).replace(".", "").replace(",", ""))
        return False
    except ValueError:
        return True


def processar_xlsx(path: Path, ano: int) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    frames = []

    for sheet in xls.sheet_names:
        # Ignorar abas auxiliares
        sheet_norm = sheet.strip().upper()
        sheet_norm_clean = (
            sheet_norm.replace("Ç", "C").replace("Ã", "A").replace("Õ", "O")
            .replace("É", "E").replace("Ê", "E").replace("Á", "A")
        )
        if any(skip in sheet_norm_clean for skip in ABAS_SKIP):
            continue

        # Extrair mês do nome da aba (ex: "JAN-2024" → 1)
        parts = sheet_norm.split("-")
        mes = MESES_PT.get(parts[0].strip(), None)
        if mes is None:
            continue  # aba não é de mês (ex: "Tabela de USOS")

        # Detectar se tem header lendo apenas a primeira linha
        df_peek = pd.read_excel(xls, sheet_name=sheet, header=None, nrows=1)
        if df_peek.empty:
            continue
        has_header = _tem_header(df_peek.iloc[0, 0])

        # Ler planilha sem header (sempre positional)
        df = pd.read_excel(
            xls, sheet_name=sheet,
            header=None,
            skiprows=1 if has_header else 0,
        )
        if df.empty:
            continue

        # Aplicar nomes posicionais
        n = min(len(df.columns), len(COL_NAMES))
        df.columns = list(COL_NAMES[:n]) + [f"_extra{i}" for i in range(len(df.columns) - n)]

        df["ano"] = ano
        df["mes"] = mes
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


# ─── Limpeza ──────────────────────────────────────────────────────────────────

def limpar(df: pd.DataFrame, ano: int) -> pd.DataFrame:
    # Manter apenas colunas necessárias
    cols_presentes = [c for c in KEEP if c in df.columns]
    df = df[cols_presentes].copy()

    # SQL: numérico obrigatório
    df["sql"] = pd.to_numeric(df["sql"], errors="coerce")
    df = df.dropna(subset=["sql"])
    df["sql"] = df["sql"].astype("int64")

    # valor_transacao: numérico positivo
    df["valor_transacao"] = pd.to_numeric(df["valor_transacao"], errors="coerce")
    df = df[df["valor_transacao"].fillna(0) > 0]

    # data_transacao
    df["data_transacao"] = pd.to_datetime(df["data_transacao"], errors="coerce")

    # valor_venal_referencia
    if "valor_venal_referencia" in df.columns:
        df["valor_venal_referencia"] = pd.to_numeric(df["valor_venal_referencia"], errors="coerce").clip(lower=0)

    # proporcao_transmitida
    if "proporcao_transmitida" in df.columns:
        df["proporcao_transmitida"] = pd.to_numeric(df["proporcao_transmitida"], errors="coerce").clip(0, 100)

    # Áreas
    for col in ["area_terreno", "area_construida"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").clip(lower=0)

    # Logradouro: string maiúscula limpa
    if "logradouro" in df.columns:
        df["logradouro"] = (
            df["logradouro"].astype(str).str.strip().str.upper()
            .replace({"NAN": None, "": None, "NONE": None, "<NA>": None})
        )

    # Bairro: string maiúscula limpa
    if "bairro" in df.columns:
        df["bairro"] = (
            df["bairro"].astype(str).str.strip().str.upper()
            .replace({"NAN": None, "": None, "NONE": None, "<NA>": None})
        )

    # Natureza: remover código numérico do início "1.Compra e venda" → "Compra e venda"
    if "natureza_transacao" in df.columns:
        df["natureza_transacao"] = (
            df["natureza_transacao"].astype(str).str.strip()
            .str.replace(r"^\d+\.\s*", "", regex=True)
            .replace({"nan": None, "": None, "None": None})
        )

    # Garantir tipos consistentes — converter todas as colunas object para string
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).replace({"nan": None, "None": None, "<NA>": None, "": None})

    # Remover duplicatas
    antes = len(df)
    df = df.drop_duplicates()
    removidas = antes - len(df)

    return df, removidas


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--anos", nargs="+", type=int, default=sorted(ARQUIVOS.keys()))
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    relatorio = {}
    parquets = []

    for ano in sorted(args.anos):
        if ano not in ARQUIVOS:
            print(f"  [{ano}] URL não configurada, ignorando.")
            continue

        print(f"\n[{ano}]")
        path = baixar(ano, ARQUIVOS[ano])

        print(f"  [{ano}] Processando... ", end="", flush=True)
        t0 = time.time()
        df_raw = processar_xlsx(path, ano)

        if df_raw.empty:
            print("nenhuma linha encontrada!")
            relatorio[ano] = {"linhas": 0, "removidas": 0}
            continue

        df, removidas = limpar(df_raw, ano)
        elapsed = time.time() - t0

        # Salvar Parquet intermediário por ano
        pq_path = DATA_DIR / f"itbi_{ano}.parquet"
        df.to_parquet(pq_path, index=False, compression="snappy")
        parquets.append(pq_path)

        relatorio[ano] = {
            "linhas": len(df),
            "removidas": removidas,
            "bairros": df["bairro"].nunique() if "bairro" in df.columns else 0,
            "naturezas": df["natureza_transacao"].nunique() if "natureza_transacao" in df.columns else 0,
            "valor_total": df["valor_transacao"].sum() if "valor_transacao" in df.columns else 0,
        }
        print(f"{len(df):,} linhas em {elapsed:.1f}s")

    # Consolidar todos os Parquets em um único
    print("\n[Consolidando]")
    t0 = time.time()

    import duckdb
    out = DATA_DIR / "itbi_consolidado.parquet"
    arquivos_str = ", ".join(f"'{p}'" for p in parquets)
    duckdb.execute(
        f"COPY (SELECT * FROM read_parquet([{arquivos_str}], union_by_name=true)) "
        f"TO '{out}' (FORMAT PARQUET, COMPRESSION SNAPPY)"
    )
    print(f"Parquet consolidado: {out} ({out.stat().st_size/1e6:.1f} MB) em {time.time()-t0:.1f}s")

    # Relatório final
    total_linhas = sum(r["linhas"] for r in relatorio.values())
    total_removidas = sum(r["removidas"] for r in relatorio.values())

    print("\n" + "="*70)
    print(f"{'ANO':<6} {'LINHAS':>10} {'REMOVIDAS':>10} {'BAIRROS':>8} {'VALOR TOTAL (R$)':>20}")
    print("-"*70)
    for ano in sorted(relatorio):
        r = relatorio[ano]
        print(
            f"{ano:<6} {r['linhas']:>10,} {r['removidas']:>10,} "
            f"{r.get('bairros',0):>8,} {r.get('valor_total',0):>20,.0f}"
        )
    print("="*70)
    print(f"{'TOTAL':<6} {total_linhas:>10,} {total_removidas:>10,}")
    print(f"\nParquet final: {out}")


if __name__ == "__main__":
    main()
