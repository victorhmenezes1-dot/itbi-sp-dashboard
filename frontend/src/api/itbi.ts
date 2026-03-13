/**
 * API client for the ITBI São Paulo dataset.
 *
 * In development, data is fetched via the Vite proxy to the Streamlit backend.
 * In production, point BASE_URL to your deployed API.
 */

import type { FilterOptions, Filters, KPISummary, PriceM2Row, Transaction } from '../types/itbi';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

async function fetchJSON<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

/** Load the available filter options (years, districts, transaction types, value range). */
export async function fetchFilterOptions(): Promise<FilterOptions> {
  return fetchJSON<FilterOptions>('/filter-options');
}

/** Load the top-N transactions matching the given filters. */
export async function fetchTopTransactions(
  filters: Filters,
  limit: number,
): Promise<Transaction[]> {
  return fetchJSON<Transaction[]>('/top-transactions', {
    anos: filters.anos.join(','),
    meses: filters.meses.join(','),
    bairros: filters.bairros.join(','),
    naturezas: filters.naturezas.join(','),
    val_min: String(filters.val_min),
    val_max: String(filters.val_max),
    limit: String(limit),
  });
}

/** Load price-per-m² series for charting. */
export async function fetchPriceM2(
  bairros: string[],
  anos: number[],
  minTransactions: number,
): Promise<PriceM2Row[]> {
  return fetchJSON<PriceM2Row[]>('/price-m2', {
    bairros: bairros.join(','),
    anos: anos.join(','),
    min_n: String(minTransactions),
  });
}

/** Load KPI totals for the current filter set. */
export async function fetchKPIs(filters: Filters): Promise<KPISummary> {
  return fetchJSON<KPISummary>('/kpis', {
    anos: filters.anos.join(','),
    meses: filters.meses.join(','),
    bairros: filters.bairros.join(','),
    naturezas: filters.naturezas.join(','),
    val_min: String(filters.val_min),
    val_max: String(filters.val_max),
  });
}
