"""
upload_motherduck.py
Faz upload do itbi_consolidado.parquet para o MotherDuck.
Execute uma vez (ou sempre que atualizar os dados):

    python upload_motherduck.py
"""

import duckdb
from pathlib import Path

# Cole seu token aqui ou defina a variável de ambiente MOTHERDUCK_TOKEN
import os
TOKEN = os.environ.get("MOTHERDUCK_TOKEN") or "cole_seu_token_aqui"

PARQUET = Path(__file__).parent / "data" / "itbi_consolidado.parquet"

print(f"Conectando ao MotherDuck...")
con = duckdb.connect(f"md:?motherduck_token={TOKEN}")

print("Criando banco itbi (se não existir)...")
con.execute("CREATE DATABASE IF NOT EXISTS itbi")
con.execute("USE itbi")

print(f"Importando {PARQUET} ({PARQUET.stat().st_size/1e6:.1f} MB)...")
con.execute(f"""
    CREATE OR REPLACE TABLE transacoes AS
    SELECT * FROM read_parquet('{PARQUET}')
""")

n = con.execute("SELECT COUNT(*) FROM transacoes").fetchone()[0]
print(f"Upload concluido: {n:,} linhas em itbi.main.transacoes")
con.close()
