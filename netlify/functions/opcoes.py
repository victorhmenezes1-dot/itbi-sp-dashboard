"""
Netlify Function — /api/opcoes
Returns filter options: anos, bairros, naturezas, val_min, val_max.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from _db import get_connection, respond, error, options_response, TABLE


def handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return options_response()

    try:
        con = get_connection()

        anos = con.execute(
            f"SELECT DISTINCT ano FROM {TABLE} WHERE ano IS NOT NULL ORDER BY ano"
        ).fetchdf()["ano"].tolist()

        bairros = con.execute(f"""
            SELECT bairro FROM {TABLE}
            WHERE bairro IS NOT NULL
            GROUP BY bairro ORDER BY COUNT(*) DESC LIMIT 500
        """).fetchdf()["bairro"].tolist()

        naturezas = con.execute(f"""
            SELECT DISTINCT natureza_transacao FROM {TABLE}
            WHERE natureza_transacao IS NOT NULL ORDER BY natureza_transacao
        """).fetchdf()["natureza_transacao"].tolist()

        val_range = con.execute(f"""
            SELECT MIN(valor_transacao)::DOUBLE, MAX(valor_transacao)::DOUBLE
            FROM {TABLE} WHERE valor_transacao > 0
        """).fetchdf().values[0].tolist()

        con.close()

        return respond({
            "anos":      [int(a) for a in anos if a is not None],
            "bairros":   [str(b) for b in bairros if b is not None],
            "naturezas": [str(n) for n in naturezas if n is not None],
            "val_min":   float(val_range[0] or 0),
            "val_max":   float(val_range[1] or 99_000_000_000),
        })
    except Exception as e:
        return error(str(e))
