"""
Netlify Function — /api/top_transacoes
Returns top N transactions filtered by anos, meses, bairros, naturezas, val range.
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
        top_n     = min(int(qp.get("top_n", 50)), 500)

        where = build_where(anos, meses, bairros, naturezas, val_min, val_max)

        sql = f"""
        SELECT
            STRFTIME(data_transacao, '%d/%m/%Y')        AS data,
            ano,
            mes,
            logradouro,
            numero,
            bairro,
            natureza_transacao                          AS natureza,
            valor_transacao::DOUBLE                     AS valor_transacao,
            valor_venal_referencia::DOUBLE              AS valor_venal_referencia,
            area_terreno::DOUBLE                        AS area_terreno,
            area_construida::DOUBLE                     AS area_construida,
            CASE WHEN area_construida > 0
                 THEN (valor_transacao / area_construida)::DOUBLE END AS preco_m2,
            uso_descricao,
            padrao_descricao,
            sql
        FROM {TABLE}
        {where}
        ORDER BY valor_transacao DESC
        LIMIT {top_n}
        """

        con = get_connection()
        df = con.execute(sql).fetchdf()
        con.close()

        return respond(df.to_dict(orient="records"))
    except Exception as e:
        return error(str(e))
