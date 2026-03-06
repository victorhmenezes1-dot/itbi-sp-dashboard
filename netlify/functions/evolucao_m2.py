"""
Netlify Function — /api/evolucao_m2
Returns median price/m² per bairro per year for the price evolution chart.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from _db import get_connection, respond, error, options_response, TABLE, safe_str


def handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return options_response()

    try:
        qp = event.get("queryStringParameters") or {}

        bairros = json.loads(qp.get("bairros", "[]"))
        anos    = json.loads(qp.get("anos", "[]"))
        min_n   = int(qp.get("min_n", 30))

        if not bairros:
            return respond([])

        b_str = ", ".join(f"'{safe_str(b)}'" for b in bairros)

        anos_filter = ""
        if anos:
            anos_int = [int(a) for a in anos]
            anos_filter = f"AND ano IN ({', '.join(str(a) for a in anos_int)})"

        sql = f"""
        SELECT
            bairro,
            ano,
            MEDIAN(valor_transacao / area_construida)::DOUBLE AS preco_m2_mediana,
            COUNT(*) AS n_transacoes
        FROM {TABLE}
        WHERE bairro IN ({b_str})
          AND area_construida > 0
          AND valor_transacao > 0
          {anos_filter}
        GROUP BY bairro, ano
        HAVING COUNT(*) >= {min_n}
        ORDER BY bairro, ano
        """

        con = get_connection()
        df = con.execute(sql).fetchdf()
        con.close()

        return respond(df.to_dict(orient="records"))
    except Exception as e:
        return error(str(e))
