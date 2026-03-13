import type { TransactionWithMap } from '../types/itbi';
import { buildMapsUrl, fmtBRL } from '../types/itbi';

interface Props {
  transactions: TransactionWithMap[];
}

export function TransactionTable({ transactions }: Props) {
  if (transactions.length === 0) {
    return <p style={styles.empty}>Nenhuma transação encontrada com os filtros selecionados.</p>;
  }

  return (
    <div style={styles.wrapper}>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Mapa</th>
            <th style={styles.th}>Data</th>
            <th style={styles.th}>Logradouro</th>
            <th style={styles.th}>Bairro</th>
            <th style={styles.th}>Valor (R$)</th>
            <th style={styles.th}>R$/m²</th>
            <th style={styles.th}>Área (m²)</th>
            <th style={styles.th}>Natureza</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((t, i) => {
            const url = buildMapsUrl(t.logradouro, t.numero, t.bairro);
            return (
              <tr key={i} style={i % 2 === 0 ? styles.rowEven : styles.rowOdd}>
                <td style={styles.td}>
                  <a href={url} target="_blank" rel="noopener noreferrer" style={styles.mapLink}>
                    🗺️
                  </a>
                </td>
                <td style={styles.td}>{t.data}</td>
                <td style={styles.td}>
                  {t.logradouro}{t.numero ? `, ${t.numero}` : ''}
                </td>
                <td style={styles.td}>{t.bairro}</td>
                <td style={{ ...styles.td, textAlign: 'right' }}>{fmtBRL(t.valor_transacao)}</td>
                <td style={{ ...styles.td, textAlign: 'right' }}>{fmtBRL(t.preco_m2)}</td>
                <td style={{ ...styles.td, textAlign: 'right' }}>
                  {t.area_construida != null ? `${t.area_construida.toFixed(1)}` : '—'}
                </td>
                <td style={styles.td}>{t.natureza}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Helper: convert a Transaction[] to TransactionWithMap[] */
export function withMapUrls(transactions: import('../types/itbi').Transaction[]): TransactionWithMap[] {
  return transactions.map(t => ({
    ...t,
    mapa_url: buildMapsUrl(t.logradouro, t.numero, t.bairro),
  }));
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    overflowX: 'auto',
    borderRadius: '8px',
    border: '1px solid #e2e8f0',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.85rem',
  },
  th: {
    background: '#f8fafc',
    color: '#475569',
    padding: '0.6rem 0.75rem',
    textAlign: 'left',
    fontWeight: 600,
    borderBottom: '2px solid #e2e8f0',
    whiteSpace: 'nowrap',
  },
  td: {
    padding: '0.55rem 0.75rem',
    borderBottom: '1px solid #f1f5f9',
    color: '#334155',
    whiteSpace: 'nowrap',
  },
  rowEven: { background: '#fff' },
  rowOdd: { background: '#f8fafc' },
  mapLink: { textDecoration: 'none', fontSize: '1rem' },
  empty: { color: '#64748b', fontStyle: 'italic', padding: '1rem 0' },
};
