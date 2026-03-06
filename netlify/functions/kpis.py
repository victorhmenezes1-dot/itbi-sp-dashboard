"""
Netlify Function — /api/kpis
Returns aggregate KPI metrics for the filtered dataset.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from _db import get_connection, respond, error, options_response, TABLE, build_where


def handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return options_response()

    try:
        qp = event.get("queryStringParameters") or {}

        anos      = json.loads(qp.get("anos", "[]"))
        meses     = json.loads(qp.get("meses", "[]"))
        bairros   = json.loads(qp.get("bairros", "[]"))
        naturezas = json.loads(qp.get("naturezas", "[]"))
        val_min   = float(qp.get("val_min", 0))
        val_max   = float(qp.get("val_max", 99_000_000_000))

        where = build_where(anos, meses, bairros, naturezas, val_min, val_max)

        sql = f"""
        SELECT
            COUNT(*)::BIGINT                    AS total_transacoes,
            SUM(valor_transacao)::DOUBLE        AS valor_total,
            AVG(valor_transacao)::DOUBLE        AS ticket_medio,
            MEDIAN(valor_transacao)::DOUBLE     AS mediana,
            MIN(data_transacao)::DATE::VARCHAR  AS data_inicio,
            MAX(data_transacao)::DATE::VARCHAR  AS data_fim
        FROM {TABLE}
        {where}
        """

        con = get_connection()
        row = con.execute(sql).fetchdf().iloc[0].to_dict()
        con.close()

        return respond(row)
    except Exception as e:
        return error(str(e))
