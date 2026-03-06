"""
Netlify Function — /api/busca
Searches transactions by street name, number, and/or reference.
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

        termo  = qp.get("termo", "").strip().upper()
        numero = qp.get("numero", "").strip()
        ref    = qp.get("ref", "").strip().upper()
        anos   = json.loads(qp.get("anos", "[]"))
        limit  = min(int(qp.get("limit", 200)), 2000)

        if not termo and not ref:
            return respond([])

        conds = ["valor_transacao > 0"]
        if termo:
            conds.append(f"logradouro ILIKE '%{safe_str(termo)}%'")
        if numero:
            conds.append(f"CAST(numero AS VARCHAR) = '{safe_str(numero)}'")
        if ref:
            conds.append(f"referencia ILIKE '%{safe_str(ref)}%'")
        if anos:
            anos_int = [int(a) for a in anos]
            conds.append(f"ano IN ({', '.join(str(a) for a in anos_int)})")

        sql = f"""
        SELECT
            logradouro,
            numero,
            complemento,
            referencia,
            bairro,
            ano,
            mes,
            natureza_transacao,
            data_transacao::DATE::VARCHAR       AS data_transacao,
            valor_transacao::DOUBLE             AS valor_transacao,
            valor_venal_referencia::DOUBLE      AS valor_venal_referencia,
            proporcao_transmitida,
            area_terreno::DOUBLE                AS area_terreno,
            area_construida::DOUBLE             AS area_construida,
            CASE WHEN area_construida > 0
                 THEN (valor_transacao / area_construida)::DOUBLE END AS preco_m2,
            sql
        FROM {TABLE}
        WHERE {' AND '.join(conds)}
        ORDER BY data_transacao DESC
        LIMIT {limit}
        """

        con = get_connection()
        df = con.execute(sql).fetchdf()
        con.close()

        return respond(df.to_dict(orient="records"))
    except Exception as e:
        return error(str(e))
