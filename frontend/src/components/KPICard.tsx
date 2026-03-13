import type { KPISummary } from '../types/itbi';
import { fmtBRL, fmtNum } from '../types/itbi';

interface Props {
  kpi: KPISummary;
}

interface CardProps {
  label: string;
  value: string;
}

function Card({ label, value }: CardProps) {
  return (
    <div style={styles.card}>
      <span style={styles.label}>{label}</span>
      <span style={styles.value}>{value}</span>
    </div>
  );
}

export function KPICards({ kpi }: Props) {
  return (
    <div style={styles.grid}>
      <Card label="Total de Transações" value={fmtNum(kpi.total_transacoes)} />
      <Card label="Valor Total" value={fmtBRL(kpi.valor_total)} />
      <Card label="Ticket Médio" value={fmtBRL(kpi.ticket_medio)} />
      <Card label="Mediana" value={fmtBRL(kpi.mediana)} />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '1rem',
    margin: '1rem 0',
  },
  card: {
    background: '#fff',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    padding: '1rem 1.25rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.25rem',
    boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
  },
  label: {
    fontSize: '0.75rem',
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  value: {
    fontSize: '1.4rem',
    fontWeight: 700,
    color: '#1e293b',
  },
};
