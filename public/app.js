'use strict';

/* ── Constants ──────────────────────────────────────────────────────────── */

const API = '/.netlify/functions';

const MESES = {
  1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun',
  7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez',
};

/* ── Formatters ─────────────────────────────────────────────────────────── */

function fmtBRL(v) {
  if (v === null || v === undefined || v === '' || isNaN(Number(v))) return '—';
  return 'R$\u00a0' + Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 0 });
}

function fmtNum(v) {
  if (v === null || v === undefined || v === '' || isNaN(Number(v))) return '—';
  return Number(v).toLocaleString('pt-BR');
}

function fmtArea(v) {
  if (v === null || v === undefined || v === '' || isNaN(Number(v))) return '—';
  return Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 1 });
}

function fmtVal(v) {
  if (v === null || v === undefined || v === 'null' || v === 'None') return '—';
  return v;
}

/* ── Utilities ───────────────────────────────────────────────────────────── */

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

function buildQuery(obj) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(obj)) {
    p.set(k, Array.isArray(v) ? JSON.stringify(v) : String(v));
  }
  return p.toString();
}

async function apiFetch(endpoint, params = {}) {
  const url = `${API}/${endpoint}?${buildQuery(params)}`;
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function mapsUrl(row) {
  const parts = [row.logradouro, row.numero, row.bairro, 'São Paulo SP']
    .filter(p => p && p !== 'null' && p !== 'None' && p !== 'undefined')
    .join(' ');
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(parts)}`;
}

function makeCSV(data) {
  if (!data || !data.length) return '';
  const keys = Object.keys(data[0]);
  const escape = v => {
    const s = String(v ?? '');
    return s.includes(',') || s.includes('"') || s.includes('\n')
      ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return '\ufeff' + [keys.join(','), ...data.map(r => keys.map(k => escape(r[k])).join(','))].join('\n');
}

function csvDownloadBtn(data, filename, label = '⬇️ Exportar CSV') {
  const csv = makeCSV(data);
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
  return `<a href="${url}" download="${filename}" class="btn btn-outline-secondary btn-sm mt-2">${label}</a>`;
}

/* ── State ───────────────────────────────────────────────────────────────── */

let appOptions = null;
const ts = {};   // Tom Select instances

/* ── Init ────────────────────────────────────────────────────────────────── */

async function init() {
  document.getElementById('loading-overlay').style.display = 'flex';
  try {
    appOptions = await apiFetch('opcoes');
    setupUI();
    await Promise.all([loadKPIs(), loadTopTransactions()]);
    loadChart();
  } catch (e) {
    document.getElementById('loading-overlay').style.display = 'none';
    document.querySelector('.main-content').insertAdjacentHTML('afterbegin',
      `<div class="alert alert-danger">Erro ao inicializar: ${e.message}</div>`);
  } finally {
    document.getElementById('loading-overlay').style.display = 'none';
  }
}

function makeTomSelect(selector, opts, onChange, initialValue) {
  const el = document.querySelector(selector);
  if (!el) return null;
  const instance = new TomSelect(el, {
    options: opts,
    plugins: ['remove_button'],
    maxOptions: 1000,
    onChange: onChange || (() => {}),
  });
  if (initialValue !== undefined) instance.setValue(initialValue, true);
  return instance;
}

function setupUI() {
  const { anos, bairros, naturezas, val_max } = appOptions;

  const anosOpts   = anos.map(a => ({ value: String(a), text: String(a) }));
  const bairrOpts  = bairros.map(b => ({ value: b, text: b }));
  const natOpts    = naturezas.map(n => ({ value: n, text: n }));
  const mesesOpts  = Object.entries(MESES).map(([v, t]) => ({ value: v, text: t }));

  const onFilterChange = debounce(applyFilters, 700);

  ts.anos      = makeTomSelect('#sel-anos',      anosOpts,  onFilterChange, anos.slice(-3).map(String));
  ts.meses     = makeTomSelect('#sel-meses',     mesesOpts, onFilterChange);
  ts.bairros   = makeTomSelect('#sel-bairros',   bairrOpts, onFilterChange);
  ts.naturezas = makeTomSelect('#sel-naturezas', natOpts,   onFilterChange);

  // Chart selects
  ts.chartBairros = makeTomSelect('#sel-chart-bairros', bairrOpts,
    debounce(loadChart, 700), bairros.slice(0, 5));
  ts.chartAnos = makeTomSelect('#sel-chart-anos', anosOpts,
    debounce(loadChart, 700), anos.map(String));

  // Search anos
  ts.searchAnos = makeTomSelect('#search-anos', anosOpts, null);

  // Value inputs
  document.getElementById('val-max').value = Math.min(val_max, 99e9);
  ['val-min', 'val-max'].forEach(id => {
    document.getElementById(id).addEventListener('change', debounce(applyFilters, 700));
  });

  // top-n slider
  const topN    = document.getElementById('top-n');
  const topNVal = document.getElementById('top-n-val');
  topN.addEventListener('input',  () => { topNVal.textContent = topN.value; });
  topN.addEventListener('change', debounce(applyFilters, 700));

  // min-n slider
  const minN    = document.getElementById('min-n');
  const minNVal = document.getElementById('min-n-val');
  minN.addEventListener('input',  () => { minNVal.textContent = minN.value; });
  minN.addEventListener('change', debounce(loadChart, 700));

  // Search
  document.getElementById('btn-search').addEventListener('click', runSearch);
  document.getElementById('search-termo').addEventListener('keypress', e => {
    if (e.key === 'Enter') runSearch();
  });
}

function getFilters() {
  return {
    anos:      ts.anos?.getValue()      || [],
    meses:     ts.meses?.getValue()     || [],
    bairros:   ts.bairros?.getValue()   || [],
    naturezas: ts.naturezas?.getValue() || [],
    val_min:   parseFloat(document.getElementById('val-min').value) || 0,
    val_max:   parseFloat(document.getElementById('val-max').value) || 99e9,
    top_n:     parseInt(document.getElementById('top-n').value)     || 50,
  };
}

async function applyFilters() {
  await Promise.all([loadKPIs(), loadTopTransactions()]);
}

/* ── KPIs ────────────────────────────────────────────────────────────────── */

async function loadKPIs() {
  const container = document.getElementById('kpis-container');
  container.innerHTML = '<div class="col-12 text-center py-3"><div class="spinner-border text-primary"></div></div>';

  try {
    const d = await apiFetch('kpis', getFilters());
    renderKPIs(d);
  } catch (e) {
    container.innerHTML = `<div class="col-12"><div class="alert alert-danger">${e.message}</div></div>`;
  }
}

function renderKPIs(d) {
  const items = [
    { label: 'Total de Transações', value: fmtNum(d.total_transacoes) },
    { label: 'Valor Total',         value: fmtBRL(d.valor_total) },
    { label: 'Ticket Médio',        value: fmtBRL(d.ticket_medio) },
    { label: 'Mediana',             value: fmtBRL(d.mediana) },
  ];

  document.getElementById('kpis-container').innerHTML = items.map(item => `
    <div class="col-6 col-md-3">
      <div class="kpi-card">
        <div class="kpi-value">${item.value}</div>
        <div class="kpi-label">${item.label}</div>
      </div>
    </div>
  `).join('');

  const cap = document.getElementById('periodo-caption');
  if (cap && d.data_inicio && d.data_fim) {
    cap.textContent = `Período: ${d.data_inicio} → ${d.data_fim}`;
  }
}

/* ── Top Transactions ────────────────────────────────────────────────────── */

async function loadTopTransactions() {
  const container = document.getElementById('table-container');
  const timing    = document.getElementById('table-timing');
  container.innerHTML = `
    <div class="text-center py-4">
      <div class="spinner-border text-primary"></div>
      <div class="mt-2 text-muted">Carregando…</div>
    </div>`;

  const filters = getFilters();
  const t0 = performance.now();

  try {
    const data    = await apiFetch('top_transacoes', filters);
    const elapsed = ((performance.now() - t0) / 1000).toFixed(3);

    document.getElementById('top-title').textContent =
      `🏆 Maiores Transações (top ${filters.top_n})`;
    timing.textContent =
      `⏱ ${elapsed}s · anos=${filters.anos.length ? filters.anos.join(', ') : 'todos'}`;

    renderTopTable(data, container);
  } catch (e) {
    timing.textContent = '';
    container.innerHTML = `<div class="alert alert-danger">${e.message}</div>`;
  }
}

const TOP_COLS = [
  { key: '_mapa',                label: 'Mapa',             fmt: (_, r) => `<a href="${mapsUrl(r)}" target="_blank" rel="noopener">🗺️</a>` },
  { key: 'data',                 label: 'Data' },
  { key: 'bairro',              label: 'Bairro' },
  { key: 'logradouro',          label: 'Logradouro' },
  { key: 'numero',              label: 'Número' },
  { key: 'valor_transacao',     label: 'Valor Transação',    fmt: fmtBRL },
  { key: 'preco_m2',            label: 'R$/m²',              fmt: fmtBRL },
  { key: 'area_construida',     label: 'Área Constr. (m²)',  fmt: fmtArea },
  { key: 'natureza',            label: 'Natureza' },
  { key: 'valor_venal_referencia', label: 'Valor Venal Ref.', fmt: fmtBRL },
  { key: 'padrao_descricao',    label: 'Padrão' },
  { key: 'uso_descricao',       label: 'Uso' },
];

function renderTopTable(data, container) {
  if (!data || !data.length) {
    container.innerHTML = '<div class="alert alert-info">Nenhuma transação encontrada com os filtros selecionados.</div>';
    return;
  }
  container.innerHTML = buildTableHTML(data, TOP_COLS) + csvDownloadBtn(data, 'itbi_maiores_transacoes.csv');
}

/* ── Chart ───────────────────────────────────────────────────────────────── */

async function loadChart() {
  const container = document.getElementById('chart-container');
  const bairros   = ts.chartBairros?.getValue() || [];
  const anos      = ts.chartAnos?.getValue()    || [];
  const min_n     = parseInt(document.getElementById('min-n').value) || 30;

  if (!bairros.length) {
    container.innerHTML = '<div class="alert alert-info">Selecione ao menos um bairro para visualizar o gráfico.</div>';
    return;
  }

  container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div></div>';

  try {
    const data = await apiFetch('evolucao_m2', { bairros, anos, min_n });

    if (!data.length) {
      container.innerHTML = '<div class="alert alert-info">Nenhum bairro atende aos filtros. Reduza o mínimo de transações ou selecione mais bairros.</div>';
      return;
    }

    container.innerHTML = '';
    renderChart(data, container);
  } catch (e) {
    container.innerHTML = `<div class="alert alert-danger">${e.message}</div>`;
  }
}

function renderChart(data, container) {
  // Group rows by bairro
  const byBairro = {};
  for (const row of data) {
    if (!byBairro[row.bairro]) byBairro[row.bairro] = { x: [], y: [] };
    byBairro[row.bairro].x.push(row.ano);
    byBairro[row.bairro].y.push(row.preco_m2_mediana);
  }

  const traces = Object.entries(byBairro).map(([bairro, d]) => ({
    type:   'scatter',
    mode:   'lines+markers',
    name:   bairro,
    x:      d.x,
    y:      d.y,
    hovertemplate: '<b>%{fullData.name}</b><br>Ano: %{x}<br>R$/m²: R$ %{y:,.0f}<extra></extra>',
  }));

  Plotly.newPlot(container, traces, {
    title:    { text: 'Evolução da Mediana do Preço por m² por Bairro', font: { size: 14 } },
    xaxis:    { title: 'Ano', dtick: 1, tickformat: 'd' },
    yaxis:    { title: 'R$/m² (mediana)', tickprefix: 'R$\u00a0', tickformat: ',.0f' },
    height:   520,
    template: 'plotly_white',
    legend:   { title: { text: 'Bairro' } },
    margin:   { t: 60, r: 20, b: 60, l: 80 },
  }, { responsive: true });
}

/* ── Address Search ──────────────────────────────────────────────────────── */

async function runSearch() {
  const termo  = document.getElementById('search-termo').value.trim();
  const numero = document.getElementById('search-numero').value.trim();
  const ref    = document.getElementById('search-ref').value.trim();
  const anos   = ts.searchAnos?.getValue() || [];
  const limit  = parseInt(document.getElementById('search-limit').value) || 200;

  const container = document.getElementById('search-container');

  if (!termo && !ref) {
    container.innerHTML = '<div class="alert alert-warning">Digite o nome de uma rua ou uma referência para pesquisar.</div>';
    return;
  }

  container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div></div>';

  const t0 = performance.now();
  try {
    const data    = await apiFetch('busca', { termo, numero, ref, anos, limit });
    const elapsed = ((performance.now() - t0) / 1000).toFixed(3);
    renderSearch(data, container, elapsed, limit);
  } catch (e) {
    container.innerHTML = `<div class="alert alert-danger">${e.message}</div>`;
  }
}

const SEARCH_COLS = [
  { key: 'logradouro',          label: 'Logradouro' },
  { key: 'numero',              label: 'Número' },
  { key: 'complemento',        label: 'Complemento' },
  { key: 'referencia',         label: 'Referência' },
  { key: 'bairro',             label: 'Bairro' },
  { key: 'ano',                label: 'Ano' },
  { key: 'mes',                label: 'Mês',               fmt: v => MESES[v] || v },
  { key: 'natureza_transacao', label: 'Natureza' },
  { key: 'data_transacao',     label: 'Data' },
  { key: 'valor_transacao',    label: 'Valor Transação',   fmt: fmtBRL },
  { key: 'preco_m2',           label: 'R$/m²',             fmt: fmtBRL },
  { key: 'area_construida',    label: 'Área Constr. (m²)', fmt: fmtArea },
  { key: 'proporcao_transmitida', label: '% Transmitido' },
];

function renderSearch(data, container, elapsed, limit) {
  if (!data || !data.length) {
    container.innerHTML = '<div class="alert alert-info">Nenhuma transação encontrada.</div>';
    return;
  }

  const total = data.length;
  const soma  = data.reduce((s, r) => s + (Number(r.valor_transacao) || 0), 0);
  const media = soma / total;
  const ruas  = new Set(data.map(r => r.logradouro)).size;

  const kpiHtml = `
    <div class="row g-3 mb-3">
      ${[
        { label: 'Transações encontradas', value: fmtNum(total) },
        { label: 'Valor total',            value: fmtBRL(soma) },
        { label: 'Ticket médio',           value: fmtBRL(media) },
        { label: 'Ruas únicas',            value: fmtNum(ruas) },
      ].map(item => `
        <div class="col-6 col-md-3">
          <div class="kpi-card">
            <div class="kpi-value">${item.value}</div>
            <div class="kpi-label">${item.label}</div>
          </div>
        </div>`).join('')}
    </div>
    <p class="text-muted small">⏱ ${elapsed}s · mostrando até ${limit} registros mais recentes</p>
  `;

  container.innerHTML = kpiHtml + buildTableHTML(data, SEARCH_COLS) + csvDownloadBtn(data, 'itbi_busca.csv');
}

/* ── Table Builder ───────────────────────────────────────────────────────── */

function buildTableHTML(data, cols) {
  const headers = cols.map(c => `<th>${c.label}</th>`).join('');

  const rows = data.map(row => {
    const cells = cols.map(col => {
      let val;
      if (col.fmt) {
        val = col.fmt(row[col.key], row);
      } else {
        val = row[col.key];
        if (val === null || val === undefined || val === 'null' || val === 'None') val = '—';
      }
      return `<td>${val}</td>`;
    }).join('');
    return `<tr>${cells}</tr>`;
  }).join('');

  return `
    <div class="table-responsive">
      <table class="table table-sm table-hover table-bordered">
        <thead class="table-light"><tr>${headers}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

/* ── Bootstrap ───────────────────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', init);
