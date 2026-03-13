import { useEffect, useState } from 'react';
import { fetchFilterOptions, fetchKPIs, fetchPriceM2, fetchTopTransactions } from './api/itbi';
import { KPICards } from './components/KPICard';
import { PriceChart } from './components/PriceChart';
import { TransactionTable, withMapUrls } from './components/TransactionTable';
import type { FilterOptions, Filters, KPISummary, PriceM2Row, TransactionWithMap } from './types/itbi';

const DEFAULT_FILTERS: Filters = {
  anos: [],
  meses: [],
  bairros: [],
  naturezas: [],
  val_min: 0,
  val_max: 99_000_000_000,
};

export default function App() {
  const [options, setOptions] = useState<FilterOptions | null>(null);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [topN, setTopN] = useState(50);
  const [transactions, setTransactions] = useState<TransactionWithMap[]>([]);
  const [kpi, setKpi] = useState<KPISummary | null>(null);
  const [priceData, setPriceData] = useState<PriceM2Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load filter options on mount
  useEffect(() => {
    fetchFilterOptions()
      .then(opts => {
        setOptions(opts);
        // Default to last 3 years
        const defaultAnos = opts.anos.slice(-3);
        setFilters(f => ({ ...f, anos: defaultAnos }));
      })
      .catch(e => setError(String(e)));
  }, []);

  // Reload data whenever filters change
  useEffect(() => {
    if (!options) return;
    setLoading(true);
    setError(null);
    Promise.all([
      fetchTopTransactions(filters, topN),
      fetchKPIs(filters),
    ])
      .then(([txs, kpis]) => {
        setTransactions(withMapUrls(txs));
        setKpi(kpis);
      })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, [filters, topN, options]);

  // Load price chart for top 5 bairros
  useEffect(() => {
    if (!options || options.bairros.length === 0) return;
    const top5 = options.bairros.slice(0, 5);
    fetchPriceM2(top5, filters.anos, 30)
      .then(setPriceData)
      .catch(() => setPriceData([]));
  }, [options, filters.anos]);

  return (
    <div style={styles.app}>
      {/* Header */}
      <header style={styles.header}>
        <h1 style={styles.title}>🏠 ITBI São Paulo — Análise de Dados</h1>
        <p style={styles.subtitle}>
          Fonte: Prefeitura de São Paulo – Secretaria Municipal da Fazenda · 2009–2025
        </p>
      </header>

      <main style={styles.main}>
        {error && (
          <div style={styles.errorBox}>
            <strong>Erro:</strong> {error}
          </div>
        )}

        {/* KPIs */}
        {kpi && <KPICards kpi={kpi} />}

        {/* Top Transactions */}
        <section style={styles.section}>
          <div style={styles.sectionHeader}>
            <h2 style={styles.sectionTitle}>🏆 Maiores Transações (top {topN})</h2>
            <label style={styles.label}>
              Exibir&nbsp;
              <select
                value={topN}
                onChange={e => setTopN(Number(e.target.value))}
                style={styles.select}
              >
                {[10, 25, 50, 100, 200].map(n => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
              &nbsp;registros
            </label>
          </div>
          {loading ? (
            <p style={styles.loading}>Carregando…</p>
          ) : (
            <TransactionTable transactions={transactions} />
          )}
        </section>

        {/* Price Chart */}
        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>📈 Evolução de Preço por m²</h2>
          <p style={styles.caption}>
            Mediana do preço por m² construído ao longo dos anos (top 5 bairros por volume).
          </p>
          <PriceChart data={priceData} />
        </section>
      </main>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
    minHeight: '100vh',
    background: '#f8fafc',
    color: '#1e293b',
  },
  header: {
    background: 'linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)',
    color: '#fff',
    padding: '1.5rem 2rem',
  },
  title: {
    margin: 0,
    fontSize: '1.75rem',
    fontWeight: 700,
  },
  subtitle: {
    margin: '0.25rem 0 0',
    opacity: 0.8,
    fontSize: '0.85rem',
  },
  main: {
    maxWidth: '1280px',
    margin: '0 auto',
    padding: '1.5rem 1.5rem 3rem',
  },
  section: {
    background: '#fff',
    borderRadius: '12px',
    border: '1px solid #e2e8f0',
    padding: '1.25rem 1.5rem',
    marginTop: '1.5rem',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: '0.5rem',
    marginBottom: '1rem',
  },
  sectionTitle: {
    margin: 0,
    fontSize: '1.15rem',
    fontWeight: 600,
  },
  caption: {
    color: '#64748b',
    fontSize: '0.85rem',
    margin: '0 0 1rem',
  },
  label: {
    fontSize: '0.85rem',
    color: '#475569',
    display: 'flex',
    alignItems: 'center',
  },
  select: {
    border: '1px solid #cbd5e1',
    borderRadius: '6px',
    padding: '0.25rem 0.5rem',
    fontSize: '0.85rem',
    cursor: 'pointer',
  },
  loading: {
    color: '#64748b',
    fontStyle: 'italic',
  },
  errorBox: {
    background: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '8px',
    padding: '0.75rem 1rem',
    color: '#b91c1c',
    marginBottom: '1rem',
  },
};
