---
title: ITBI São Paulo Dashboard
emoji: 🏠
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: "1.35.0"
app_file: app.py
pinned: false
secrets:
  - MOTHERDUCK_TOKEN
  - ANTHROPIC_API_KEY
---

# ITBI São Paulo — Análise de Dados

Dashboard interativo para análise do ITBI (Imposto sobre Transmissão de Bens Imóveis) de São Paulo, cobrindo 2009–2025.

## Stack

- **Python + Streamlit** — interface web
- **DuckDB** — consultas rápidas diretamente no Parquet (sem carregar tudo em memória)
- **Pandas** — apenas para exibir resultados já agregados
- **Plotly** — gráficos interativos

---

## 1. Instalação

```bash
pip install -r requirements.txt
```

---

## 2. Baixar e processar os dados

```bash
python baixar_dados.py
```

O script irá:
- Baixar os arquivos xlsx de 2009 a 2025 para `data/raw/` (~500 MB no total)
- Processar e padronizar cada ano
- Consolidar tudo em `data/itbi_consolidado.parquet` (~150–200 MB, ~2,4M linhas)
- Imprimir um relatório por ano com contagem de linhas, bairros únicos e valor total

Se um arquivo já foi baixado, o download é pulado automaticamente.

Para processar apenas anos específicos:
```bash
python baixar_dados.py --anos 2023 2024 2025
```

---

## 3. Rodar o dashboard

```bash
streamlit run app.py
```

Acesse em: [http://localhost:8501](http://localhost:8501)

---

## Estrutura de arquivos

```
02. ITBI/
├── baixar_dados.py          # Download e processamento dos dados
├── app.py                   # Dashboard Streamlit
├── requirements.txt         # Dependências Python
├── README.md
└── data/
    ├── raw/                 # Arquivos xlsx originais (um por ano)
    │   ├── itbi_2009.xlsx
    │   └── ...
    ├── itbi_2009.parquet    # Parquet intermediário por ano
    └── itbi_consolidado.parquet  # Parquet final consolidado
```

---

## Funcionalidades do Dashboard

### Sidebar — Filtros
- Anos (multiselect)
- Bairro / Distrito (top 500 por volume)
- Natureza de Transação
- Faixa de valor (mínimo e máximo)

### Tabela Dinâmica
- Escolha as **linhas**, **colunas** e **métrica** (contagem, soma, média, mediana)
- Resultado exibido como pivot table formatada
- Botão para exportar em CSV

### Gráfico
- Barras agrupadas, empilhadas, horizontais ou linha
- Gerado automaticamente a partir da tabela dinâmica atual

### KPIs
- Total de transações, valor total, ticket médio e mediana do período filtrado

---

## Performance

Todas as consultas usam DuckDB direto no arquivo Parquet — sem carregar os 2,4M de linhas em memória. O tempo de consulta típico é de **0,1–0,5s** mesmo com todos os anos selecionados.
