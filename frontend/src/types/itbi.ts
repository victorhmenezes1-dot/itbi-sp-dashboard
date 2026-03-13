/**
 * Core ITBI (Imposto sobre Transmissão de Bens Imóveis) data types
 * for the São Paulo municipal property transfer tax dataset.
 */

/** A single property transfer transaction record */
export interface Transaction {
  data: string;
  ano: number;
  mes: number;
  logradouro: string;
  numero: string | null;
  bairro: string;
  natureza: string;
  valor_transacao: number;
  valor_venal_referencia: number | null;
  area_terreno: number | null;
  area_construida: number | null;
  preco_m2: number | null;
  uso_descricao: string | null;
  padrao_descricao: string | null;
  sql: string | null;
}

/** A transaction enriched with a Google Maps URL */
export interface TransactionWithMap extends Transaction {
  mapa_url: string;
}

/** Aggregated price-per-m² data for charting */
export interface PriceM2Row {
  bairro: string;
  ano: number;
  preco_m2_mediana: number;
  n_transacoes: number;
}

/** KPI summary for the currently filtered dataset */
export interface KPISummary {
  total_transacoes: number;
  valor_total: number;
  ticket_medio: number;
  mediana: number;
  data_inicio: string | null;
  data_fim: string | null;
}

/** Sidebar / global filter state */
export interface Filters {
  anos: number[];
  meses: number[];
  bairros: string[];
  naturezas: string[];
  val_min: number;
  val_max: number;
}

/** Available filter options loaded from the dataset */
export interface FilterOptions {
  anos: number[];
  bairros: string[];
  naturezas: string[];
  val_range: [number, number];
}

/** Month name mapping (Portuguese) */
export const MESES_NOME: Record<number, string> = {
  1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
  7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez',
};

/** Format a number as Brazilian Real currency string */
export function fmtBRL(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return '—';
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  }).format(value);
}

/** Format a number with Brazilian thousand separators */
export function fmtNum(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return '—';
  return new Intl.NumberFormat('pt-BR').format(value);
}

/** Build a Google Maps search URL from address parts */
export function buildMapsUrl(logradouro: string, numero: string | null, bairro: string): string {
  const parts = [logradouro, numero ?? '', bairro, 'São Paulo SP'].filter(Boolean);
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(parts.join(' '))}`;
}
