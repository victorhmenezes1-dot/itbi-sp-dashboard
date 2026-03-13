import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { PriceM2Row } from '../types/itbi';
import { fmtBRL } from '../types/itbi';

interface Props {
  data: PriceM2Row[];
}

/** Group rows by neighbourhood so Recharts can draw one line per bairro. */
function pivotData(rows: PriceM2Row[]): Record<string, unknown>[] {
  const byYear = new Map<number, Record<string, unknown>>();
  for (const row of rows) {
    if (!byYear.has(row.ano)) byYear.set(row.ano, { ano: row.ano });
    byYear.get(row.ano)![row.bairro] = row.preco_m2_mediana;
  }
  return [...byYear.values()].sort((a, b) => (a.ano as number) - (b.ano as number));
}

const COLOURS = [
  '#3b82f6', '#ef4444', '#10b981', '#f59e0b',
  '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16',
];

export function PriceChart({ data }: Props) {
  if (data.length === 0) {
    return <p style={{ color: '#64748b', fontStyle: 'italic' }}>Sem dados para o gráfico com os filtros atuais.</p>;
  }

  const bairros = [...new Set(data.map(d => d.bairro))];
  const pivoted = pivotData(data);

  return (
    <ResponsiveContainer width="100%" height={420}>
      <LineChart data={pivoted} margin={{ top: 8, right: 24, left: 16, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="ano" tick={{ fontSize: 12 }} />
        <YAxis
          tickFormatter={v => fmtBRL(v as number)}
          tick={{ fontSize: 11 }}
          width={110}
        />
        <Tooltip formatter={(v: unknown) => fmtBRL(v as number)} />
        <Legend />
        {bairros.map((b, i) => (
          <Line
            key={b}
            type="monotone"
            dataKey={b}
            stroke={COLOURS[i % COLOURS.length]}
            dot={{ r: 3 }}
            strokeWidth={2}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
