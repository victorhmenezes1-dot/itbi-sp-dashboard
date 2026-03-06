"""
Shared helper for Netlify Functions — DuckDB/MotherDuck connection.
Files prefixed with _ are NOT deployed as Netlify Functions.
"""

import json
import os

import duckdb

TABLE = "itbi.main.transacoes"

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Content-Type": "application/json",
}


def get_connection():
    token = os.environ.get("MOTHERDUCK_TOKEN")
    if not token:
        raise RuntimeError("MOTHERDUCK_TOKEN environment variable not set")
    con = duckdb.connect(f"md:itbi?motherduck_token={token}")
    con.execute("SET memory_limit='400MB'")
    return con


def respond(data, status=200):
    return {
        "statusCode": status,
        "headers": CORS_HEADERS,
        "body": json.dumps(data, default=str),
    }


def error(msg, status=500):
    return respond({"error": msg}, status)


def options_response():
    return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}


def safe_str(s):
    """Escape single quotes for SQL string literals."""
    return str(s).replace("'", "''")


def build_where(anos, meses, bairros, naturezas, val_min, val_max):
    conds = ["valor_transacao > 0"]
    if anos:
        anos_int = [int(a) for a in anos]
        conds.append(f"ano IN ({', '.join(str(a) for a in anos_int)})")
    if meses:
        meses_int = [int(m) for m in meses]
        conds.append(f"mes IN ({', '.join(str(m) for m in meses_int)})")
    if bairros:
        b_str = ", ".join(f"'{safe_str(b)}'" for b in bairros)
        conds.append(f"bairro IN ({b_str})")
    if naturezas:
        n_str = ", ".join(f"'{safe_str(n)}'" for n in naturezas)
        conds.append(f"natureza_transacao IN ({n_str})")
    conds.append(f"valor_transacao BETWEEN {float(val_min)} AND {float(val_max)}")
    return "WHERE " + " AND ".join(conds)
