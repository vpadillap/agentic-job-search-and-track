// Board 1: the postings of a search run, their explanation, and what to do with them.
import { html, useState, useEffect, useMemo, useRef } from '../vendor/preact-htm.js';
import { ChanceCell, FitCell, EstimatePanel } from '../components/estimate.js';
import { useUi, CommandChip, EmptyState, Menu } from '../components/shell.js';
import { DataTable } from '../components/data-table.js';
import * as Icon from '../components/icons.js';
import { api } from '../api.js';
import { WorkModeEditor } from '../components/work-mode.js';
import { PostingDescription } from '../components/posting-description.js';
import { CoverageTag, CountryFilter, filterByCountry, defaultCountry, ALL } from '../components/coverage.js';

const MODES = ['remote', 'hybrid', 'onsite'];
const CONTRACTS = ['full-time', 'part-time', 'contractor'];
const SCORE_STEPS = [50, 60, 70, 80];
const DISMISS_REASONS = ['industry', 'low_salary', 'location', 'stack'];
const SORTS = ['score', 'chance', 'fit', 'published', 'salary', 'title', 'company', 'source'];
const LABEL_ORDER = { low: 0, medium: 1, high: 2 };

const fold = (text) => (text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const safeHref = (url) => (/^https?:\/\//i.test(url || '') ? url : undefined);
const tone = (score) => (score >= 80 ? 'high' : score >= 65 ? 'mid' : '');

function providerName(id, run) {
  const found = run && run.providers.find((p) => p.id === id);
  return found ? found.name : id.charAt(0).toUpperCase() + id.slice(1);
}

function commandFor(commands, id) {
  const found = (commands || []).find((c) => c.id === id);
  return found ? found.example : `/${id}`;
}

// ── filtering ─────────────────────────────────────────────────────────────

function emptyFilters(minScore) {
  return { q: '', modes: [], contracts: [], minScore: minScore ?? null, providers: [], hasSalary: false };
}

function filterChecks(filters, t) {
  const checks = [];
  if (filters.q.trim()) {
    const needle = fold(filters.q.trim());
    checks.push({ id: 'q', label: t('footer.hiddenSearch'),
      test: (r) => fold(`${r.title} ${r.company} ${r.description}`).includes(needle) });
  }
  if (filters.modes.length) {
    checks.push({ id: 'modes', label: t('filters.workMode', { value: filters.modes.map((m) => t('mode.' + m)).join(', ') }),
      test: (r) => filters.modes.includes(r.work_mode) });
  }
  if (filters.contracts.length) {
    checks.push({ id: 'contracts', label: t('filters.contract', { value: filters.contracts.map((c) => t('contract.' + c)).join(', ') }),
      test: (r) => filters.contracts.includes(r.contract_type) });
  }
  if (filters.minScore !== null) {
    checks.push({ id: 'minScore', label: t('filters.minScore', { value: filters.minScore }),
      test: (r) => r.score && r.score.total >= filters.minScore });
  }
  if (filters.providers.length) {
    checks.push({ id: 'providers', label: t('filters.provider', { value: filters.providers.join(', ') }),
      test: (r) => filters.providers.includes(r.provider) });
  }
  if (filters.hasSalary) {
    checks.push({ id: 'hasSalary', label: t('filters.hasSalary'),
      test: (r) => r.salary && r.salary.status === 'suggested' });
  }
  return checks;
}

function sortValue(row, key) {
  switch (key) {
    case 'score': return row.score ? row.score.total : -1;
    case 'chance': return row.estimate ? row.estimate.probability : -1;
    case 'fit': return row.fit ? LABEL_ORDER[row.fit.label] : -1;
    case 'salary': return row.salary && row.salary.amount ? row.salary.amount : -1;
    case 'published': return row.posted_at || '';
    case 'title': return fold(row.title);
    case 'company': return fold(row.company);
    case 'source': return row.provider;
    default: return 0;
  }
}

// ── run summary ───────────────────────────────────────────────────────────

function ProviderChips({ run, onOpenProviders }) {
  const { t } = useUi();
  return html`
    <div class="chips">
      ${run.providers.filter((p) => p.status === 'ok').map((p) => html`
        <span class="chip">${t('provider.found', { name: p.name, count: p.found })}</span>`)}
      ${run.providers.filter((p) => p.status === 'disabled').map((p) => html`
        <span class="chip off">${t('provider.off', { name: p.name })}</span>`)}
      <button type="button" class="link-btn" onClick=${onOpenProviders}>${t('run.providers')}</button>
      ${run.skipped.map((p) => html`
        <span class="chip warn" title=${p.detail || ''}>
          ${Icon.Alert()}
          ${t(p.status === 'failed' ? 'provider.failed' : 'provider.skipped',
            { name: p.name, reason: t('skip.' + p.reason) })}
          ${p.detail && html`<span class="sr-only">. ${p.detail}</span>`}
        </span>`)}
    </div>`;
}

function RunSummary({ data, runId, onRunChange, showFiltered, onToggleFiltered, commands, onOpenProviders }) {
  const { t, fmt } = useUi();
  const run = data.run;
  const isLatest = !runId || runId === data.runs[0].id;
  const counts = run.counts;
  return html`
    <section class="card run" aria-labelledby="run-title">
      <div class="run-main">
        <div class="stack" style=${{ gap: '4px' }}>
          <h1 id="run-title">${isLatest ? t('run.latest') : t('run.earlier', { date: fmt.dayMonth(run.started_at) })}</h1>
          <p class="run-meta">
            ${t('run.meta', { date: fmt.dateTime(run.started_at), days: run.posting_age_days,
              titles: t('run.titles', { count: run.title_count }) })}
            ${run.status === 'running' && html` · <strong>${t('run.running')}</strong>`}
          </p>
        </div>
        <div class="run-counts">
          <span><strong>${counts.found}</strong> ${t('run.found')}</span>
          <span><strong>${counts.new}</strong> ${t('run.new')}</span>
          <span class="muted"><strong>${counts.filtered}</strong> ${t('run.filtered')}</span>
          <span class="muted"><strong>${counts.duplicate_or_seen}</strong> ${t('run.duplicates')}</span>
          <button type="button" class="link-btn" aria-expanded=${String(showFiltered)}
            aria-controls="filtered-list" onClick=${onToggleFiltered}>
            ${showFiltered ? t('run.hideFiltered') : t('run.showFiltered')}</button>
        </div>
        <${ProviderChips} run=${run} onOpenProviders=${onOpenProviders} />
      </div>
      <div class="run-side">
        <${CommandChip} label=${t('run.newSearch')} command=${commandFor(commands, 'job-search')} />
        ${data.runs.length > 1 && html`
          <label class="run-select">
            ${t('run.select')}
            <select value=${String(run.id)} onChange=${(e) => onRunChange(Number(e.currentTarget.value))}>
              ${data.runs.map((r) => html`
                <option value=${String(r.id)}>${t('run.option', { date: fmt.shortDateTime(r.started_at), count: r.counts.new })}</option>`)}
            </select>
          </label>`}
      </div>
    </section>`;
}

function FilteredList({ data }) {
  const { t } = useUi();
  const run = data.run;
  return html`
    <section class="card filtered" id="filtered-list" aria-labelledby="filtered-title">
      <h2 id="filtered-title">${t('filtered.title')}</h2>
      ${data.filtered.length === 0 ? html`<p class="muted">${t('filtered.empty')}</p>` : html`
        <ul>
          ${data.filtered.map((p) => html`
            <li>
              <span class="reason">${t('reason.' + p.reason)}</span>
              <strong>${p.title}</strong>
              <span class="muted">${p.company} · ${providerName(p.provider, run)}</span>
              ${p.reason_detail && html`<span>${p.reason_detail}</span>`}
              ${safeHref(p.url) && html`<a href=${safeHref(p.url)} target="_blank" rel="noopener noreferrer">
                ${t('detail.open')}</a>`}
            </li>`)}
        </ul>`}
    </section>`;
}

function ProvidersDialog({ open, onClose }) {
  const { t } = useUi();
  const dialog = useRef(null);
  const [items, setItems] = useState(null);
  const [profileCountry, setProfileCountry] = useState(null);
  const [country, setCountry] = useState(ALL);
  useEffect(() => {
    if (!dialog.current) return;
    if (open && !dialog.current.open) {
      dialog.current.showModal();
      api.providers().then((r) => {
        setItems(r.providers);
        setProfileCountry(r.profile_country || null);
        setCountry(defaultCountry(r.profile_country));
      }).catch(() => setItems([]));
    } else if (!open && dialog.current.open) {
      dialog.current.close();
    }
  }, [open]);
  const toggle = async (id, enabled) => {
    const result = await api.setProvider(id, enabled);
    setItems(result.providers);
  };
  return html`
    <dialog class="dialog" ref=${dialog} onClose=${onClose} aria-labelledby="providers-title">
      <div class="dialog-body">
        <h2 id="providers-title">${t('providers.title')}</h2>
        ${items && items.length === 0 && html`<p class="muted">${t('providers.empty')}</p>`}
        ${items && items.length > 0 && html`<${CountryFilter} id="providers-country" providers=${items}
          profileCountry=${profileCountry} value=${country} onChange=${setCountry} />`}
        ${items && filterByCountry(items, country).map((p) => html`
          <div class="provider-row">
            <label>
              <input type="checkbox" checked=${p.enabled} onChange=${(e) => toggle(p.id, e.currentTarget.checked)} />
              ${p.name}
            </label>
            <${CoverageTag} provider=${p} />
            ${!p.valid && html`<span class="small">${t('providers.invalid')}</span>`}
          </div>`)}
        <div class="menu-actions">
          <button type="button" class="btn" onClick=${onClose}>${t('providers.close')}</button>
        </div>
      </div>
    </dialog>`;
}

// ── filter bar ────────────────────────────────────────────────────────────

function CheckMenu({ label, active, legend, options, values, onChange }) {
  return html`
    <${Menu} label=${label} active=${active}>
      <fieldset>
        <legend>${legend}</legend>
        ${options.map((option) => html`
          <label>
            <input type="checkbox" checked=${values.includes(option.value)}
              onChange=${(e) => onChange(e.currentTarget.checked
                ? [...values, option.value] : values.filter((v) => v !== option.value))} />
            ${option.label}
          </label>`)}
      </fieldset>
    </${Menu}>`;
}

function FilterBar({ filters, setFilters, sort, setSort, providers, selectedCount, onBulk, sorts = SORTS }) {
  const { t } = useUi();
  const set = (patch) => setFilters({ ...filters, ...patch });
  const modeValue = filters.modes.length ? filters.modes.map((m) => t('mode.' + m)).join(', ') : t('filters.all');
  const contractValue = filters.contracts.length ? filters.contracts.map((c) => t('contract.' + c)).join(', ') : t('filters.all');
  const providerValue = filters.providers.length ? filters.providers.join(', ') : t('filters.all');
  const sortLabel = t(sort.dir === 'asc' ? 'sort.ascending' : 'sort.descending', { column: t('sort.' + sort.key) });
  return html`
    <section class="filters" aria-label=${t('filters.label')}>
      <div class="filter-group">
        <label class="search-box">
          ${Icon.Search()}
          <span class="sr-only">${t('filters.search')}</span>
          <input type="search" value=${filters.q} placeholder=${t('filters.searchPlaceholder')}
            onInput=${(e) => set({ q: e.currentTarget.value })} />
        </label>
        <${CheckMenu} label=${t('filters.workMode', { value: modeValue })} active=${filters.modes.length > 0}
          legend=${t('column.conditions')} values=${filters.modes} onChange=${(modes) => set({ modes })}
          options=${MODES.map((m) => ({ value: m, label: t('mode.' + m) }))} />
        <${CheckMenu} label=${t('filters.contract', { value: contractValue })} active=${filters.contracts.length > 0}
          legend=${t('column.conditions')} values=${filters.contracts} onChange=${(contracts) => set({ contracts })}
          options=${CONTRACTS.map((c) => ({ value: c, label: t('contract.' + c) }))} />
        <${Menu} label=${filters.minScore === null ? t('filters.minScoreAny') : t('filters.minScore', { value: filters.minScore })}
          active=${filters.minScore !== null}>
          ${(close) => html`
            <fieldset>
              <legend>${t('column.score')}</legend>
              ${[null, ...SCORE_STEPS].map((step) => html`
                <label>
                  <input type="radio" name="min-score" checked=${filters.minScore === step}
                    onChange=${() => set({ minScore: step })} />
                  ${step === null ? t('filters.any') : `≥ ${step}`}
                </label>`)}
            </fieldset>`}
        </${Menu}>
        <${CheckMenu} label=${t('filters.provider', { value: providerValue })} active=${filters.providers.length > 0}
          legend=${t('column.source')} values=${filters.providers} onChange=${(list) => set({ providers: list })}
          options=${providers.map((p) => ({ value: p.id, label: p.name }))} />
        <button type="button" class="btn" aria-pressed=${String(filters.hasSalary)}
          onClick=${() => set({ hasSalary: !filters.hasSalary })}>${t('filters.hasSalary')}</button>
        <${Menu} label=${t('filters.sort', { value: sortLabel })} buttonClass="btn btn-ghost">
          ${(close) => html`
            <fieldset>
              <legend>${t('filters.sort', { value: '' })}</legend>
              ${sorts.flatMap((key) => ['desc', 'asc'].map((dir) => html`
                <label>
                  <input type="radio" name="sort" checked=${sort.key === key && sort.dir === dir}
                    onChange=${() => setSort({ key, dir })} />
                  ${t(dir === 'asc' ? 'sort.ascending' : 'sort.descending', { column: t('sort.' + key) })}
                </label>`))}
            </fieldset>`}
        </${Menu}>
      </div>
      ${selectedCount > 0 && html`
        <div class="filter-group">
          <span class="muted" role="status">${t('filters.selected', { count: selectedCount })}</span>
          <button type="button" class="btn btn-primary" onClick=${() => onBulk(false)}>${t('action.track')}</button>
          <button type="button" class="btn" onClick=${() => onBulk(true)}>${t('action.trackApplied')}</button>
        </div>`}
    </section>`;
}

// ── cells and detail ──────────────────────────────────────────────────────

function DuplicateMark({ row, run }) {
  const { t } = useUi();
  if (!row.possible_duplicates.length) return null;
  const list = row.possible_duplicates.map((d) => (d.job_id
    ? t('row.duplicateTracked', { site: providerName(d.provider, run), job: d.job_id })
    : t('row.duplicateHere', { site: providerName(d.provider, run) })));
  const text = t('row.possibleDuplicateOf', { list: list.join('; ') });
  return html`<span class="tag dup" title=${text}>${Icon.Duplicate()}<span>${text}</span></span>`;
}

function SalaryCell({ salary }) {
  const { t, fmt } = useUi();
  if (salary && salary.status === 'suggested') {
    return html`<div class="stack">
      <span class="money">${fmt.money(salary.amount, salary.currency)}</span>
      <span class="small">${t('row.salaryNote', { min: fmt.number(salary.range_min), max: fmt.number(salary.range_max), count: salary.source_count })}</span>
    </div>`;
  }
  if (salary && salary.status === 'no_data') {
    return html`<div class="stack">
      <span class="muted" style=${{ fontWeight: 500 }}>${t('row.noSalary')}</span>
      <span class="small">${t('row.noSalaryNote')}</span>
    </div>`;
  }
  return html`<span class="small">${t('row.notResearched')}</span>`;
}

function TrackedLink({ application }) {
  const { t } = useUi();
  return html`<a class="tracked" href="#applications">
    ${Icon.Check()}${application.applied_on ? t('action.trackedApplied') : t('action.tracked')}
    <span class="sr-only">· ${application.job_id}</span></a>`;
}

function DismissMenu({ row, onDismiss }) {
  const { t } = useUi();
  const [other, setOther] = useState(null);
  return html`
    <${Menu} label=${Icon.Close()} buttonClass="btn btn-icon" align="right" menuLabel=${t('action.dismiss')}>
      ${(close) => other === null ? html`
        <span class="small" style=${{ padding: '4px 8px' }}>${t('dismiss.label')}</span>
        ${DISMISS_REASONS.map((reason) => html`
          <button type="button" class="menu-item" onClick=${() => { close(); onDismiss([row.id], reason); }}>
            ${t('dismiss.' + reason)}</button>`)}
        <button type="button" class="menu-item" onClick=${() => setOther('')}>${t('dismiss.other')}</button>` : html`
        <label class="sr-only" for=${'other-' + row.id}>${t('dismiss.otherLabel')}</label>
        <textarea id=${'other-' + row.id} placeholder=${t('dismiss.otherLabel')} value=${other}
          onInput=${(e) => setOther(e.currentTarget.value)}></textarea>
        <div class="menu-actions">
          <button type="button" class="btn btn-sm" onClick=${() => { setOther(null); close(); }}>${t('dismiss.cancel')}</button>
          <button type="button" class="btn btn-sm btn-dark" disabled=${!other.trim()}
            onClick=${() => { close(); onDismiss([row.id], 'other', other.trim()); setOther(null); }}>
            ${t('dismiss.confirm')}</button>
        </div>`}
    </${Menu}>`;
}

function RowActions({ row, onTrack, onDismiss, onRestore }) {
  const { t } = useUi();
  if (row.application) return html`<div class="row-actions"><${TrackedLink} application=${row.application} /></div>`;
  if (row.dismissal) {
    return html`<div class="row-actions">
      <span class="small">${t('dismiss.' + row.dismissal.reason)}</span>
      <button type="button" class="btn btn-sm" onClick=${() => onRestore([row.id])}>${t('action.restore')}</button>
    </div>`;
  }
  return html`
    <div class="row-actions">
      <button type="button" class="btn btn-sm" onClick=${() => onTrack([row.id], false)}>${t('action.track')}</button>
      <button type="button" class="btn btn-sm" onClick=${() => onTrack([row.id], true)}
        aria-label=${`${t('action.applied')}: ${t('action.trackApplied')}`}>${t('action.applied')}</button>
      <${DismissMenu} row=${row} onDismiss=${onDismiss} />
    </div>`;
}

function Breakdown({ score }) {
  const { t } = useUi();
  if (!score) {
    return html`<div class="panel"><h2>${t('detail.notScored')}</h2></div>`;
  }
  return html`
    <div class="panel">
      <div class="panel-head">
        <h2>${t('detail.why', { score: score.total })}</h2>
        <span class="small">${t('detail.weights', { version: score.weights_version })}</span>
      </div>
      ${score.previous_total !== null && score.previous_total !== score.total && html`
        <span class="small">${t('detail.changed', { previous: score.previous_total })}</span>`}
      ${score.components.map((c) => html`
        <div class="component">
          <div class="component-head">
            <span>${t('component.' + c.component)}</span>
            <span class="mono">${c.points} / ${c.max}</span>
          </div>
          <div class=${'bar' + (c.neutral ? ' neutral' : '')} role="presentation">
            <div style=${{ width: `${c.max ? Math.round((c.points / c.max) * 100) : 0}%` }}></div>
          </div>
          <span class="note">${c.note}</span>
        </div>`)}
    </div>`;
}

function SalaryDetail({ salary }) {
  const { t, fmt } = useUi();
  if (!salary) {
    return html`<div class="panel"><h2>${t('detail.salary')}</h2><p class="note">${t('detail.notResearched')}</p></div>`;
  }
  if (salary.status === 'no_data') {
    return html`<div class="panel">
      <h2>${t('detail.salary')}</h2>
      <strong>${t('detail.noData')}</strong>
      ${salary.checked && html`<span class="small">${t('detail.checked')}</span>
        <ul class="checked">${salary.checked.map((item) => html`<li>${item}</li>`)}</ul>`}
      <span class="note">${t('detail.salaryRule')}</span>
    </div>`;
  }
  const criteria = salary.criteria || {};
  const chips = [
    fmt.country(criteria.country), criteria.level,
    criteria.work_mode ? t('mode.' + criteria.work_mode) : null, criteria.industry, criteria.company_size,
  ].filter(Boolean);
  return html`
    <div class="panel">
      <h2>${t('detail.salary')}</h2>
      <div class="stack" style=${{ gap: '2px' }}>
        <div style=${{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span class="big-money">${fmt.money(salary.amount, salary.currency)}</span>
          <span class="muted" style=${{ fontSize: '13px' }}>${t('detail.perMonth', { basis: t('basis.' + salary.basis) })}</span>
        </div>
        <span class="muted" style=${{ fontSize: '13px' }}>${t('detail.range', {
          min: fmt.money(salary.range_min, salary.currency), max: fmt.number(salary.range_max) })}</span>
      </div>
      <span class=${'confidence ' + salary.confidence}>
        ${t('detail.sources', { level: t('confidence.' + salary.confidence), count: salary.source_count })}</span>
      <div class="tags">${chips.map((chip) => html`<span class="criteria">${chip}</span>`)}</div>
      <div class="stack" style=${{ gap: '8px' }}>
        ${salary.evidence.map((e) => html`
          <a class="evidence" href=${safeHref(e.url)} target="_blank" rel="noopener noreferrer">
            <strong>${e.source}</strong>
            <span class="small">${[e.summary, fmt.money(e.amount_min, e.currency) + '–' + fmt.number(e.amount_max),
              e.sample_size ? t('detail.sample', { count: e.sample_size }) : null, fmt.monthYear(e.observed_on)]
              .filter(Boolean).join(' · ')}</span>
          </a>`)}
      </div>
      <span class="note">${t('detail.salaryRule')}</span>
    </div>`;
}

function RowDetail({ row, run, onTrack, onDismiss, onRestore }) {
  const { t, fmt } = useUi();
  const [other, setOther] = useState(null);
  return html`
    <div class="detail">
      <div class="detail-grid">
        <${PostingDescription} text=${row.description} url=${row.url} site=${providerName(row.provider, run)}
          capturedAt=${row.captured_at}>
          ${row.form_question_count > 0 && html`<span class="muted">${t('detail.questions', { count: row.form_question_count })}</span>`}
        </${PostingDescription}>
        <${Breakdown} score=${row.score} />
        <${SalaryDetail} salary=${row.salary} />
      </div>
      <${EstimatePanel} estimate=${row.estimate} fit=${row.fit} />
      ${!row.application && !row.dismissal && html`
        <div class="detail-actions">
          <div class="filter-group">
            <button type="button" class="btn btn-primary" onClick=${() => onTrack([row.id], false)}>${t('action.track')}</button>
            <button type="button" class="btn" onClick=${() => onTrack([row.id], true)}>${t('action.trackApplied')}</button>
          </div>
          ${other === null ? html`
            <div class="dismiss-chips" role="group" aria-label=${t('dismiss.label')}>
              <span class="muted" style=${{ fontSize: '13px' }} aria-hidden="true">${t('dismiss.label')}</span>
              ${DISMISS_REASONS.map((reason) => html`
                <button type="button" class="btn-chip" onClick=${() => onDismiss([row.id], reason)}>${t('dismiss.' + reason)}</button>`)}
              <button type="button" class="btn-chip" onClick=${() => setOther('')}>${t('dismiss.other')}</button>
            </div>` : html`
            <div class="dismiss-other">
              <label class="sr-only" for=${'why-' + row.id}>${t('dismiss.otherLabel')}</label>
              <input id=${'why-' + row.id} type="text" value=${other} placeholder=${t('dismiss.otherLabel')}
                onInput=${(e) => setOther(e.currentTarget.value)} ref=${(el) => el && !el.dataset.f && (el.dataset.f = '1', el.focus())} />
              <button type="button" class="btn btn-sm" onClick=${() => setOther(null)}>${t('dismiss.cancel')}</button>
              <button type="button" class="btn btn-sm btn-dark" disabled=${!other.trim()}
                onClick=${() => onDismiss([row.id], 'other', other.trim())}>${t('dismiss.confirm')}</button>
            </div>`}
        </div>`}
      ${row.application && html`<div class="detail-actions"><${TrackedLink} application=${row.application} /></div>`}
    </div>`;
}

// ── board ─────────────────────────────────────────────────────────────────

export function SearchBoard({ data, runId, onRunChange, commands, setupRequired, onAction }) {
  const { t, fmt } = useUi();
  const [filters, setFilters] = useState(() => emptyFilters(data && data.default_min_score));
  const [touched, setTouched] = useState(false);
  const [sort, setSort] = useState({ key: 'score', dir: 'desc' });
  const [selected, setSelected] = useState(new Set());
  const [expanded, setExpanded] = useState(new Set());
  const [showFiltered, setShowFiltered] = useState(false);
  const [showDismissed, setShowDismissed] = useState(false);
  const [providersOpen, setProvidersOpen] = useState(false);

  const defaultMin = data ? data.default_min_score : null;
  useEffect(() => {
    if (!touched) setFilters((f) => ({ ...f, minScore: defaultMin ?? null }));
  }, [defaultMin]);
  const changeFilters = (next) => { setTouched(true); setFilters(next); };

  const results = data ? data.results : [];
  const run = data && data.run;
  const providers = useMemo(() => {
    const ids = [...new Set(results.map((r) => r.provider))];
    return ids.map((id) => ({ id, name: providerName(id, run) }));
  }, [results, run]);

  const view = useMemo(() => {
    const dismissed = results.filter((r) => r.dismissal);
    const base = showDismissed ? results : results.filter((r) => !r.dismissal);
    const checks = filterChecks(filters, t);
    const shown = base.filter((row) => checks.every((check) => check.test(row)));
    const hidden = checks.map((check) => ({ label: check.label, count: base.filter((r) => !check.test(r)).length }))
      .filter((h) => h.count > 0);
    const dir = sort.dir === 'asc' ? 1 : -1;
    shown.sort((a, b) => {
      const x = sortValue(a, sort.key);
      const y = sortValue(b, sort.key);
      return (x < y ? -1 : x > y ? 1 : 0) * dir || a.id - b.id;
    });
    return { shown, hidden, total: base.length, dismissed: dismissed.length };
  }, [results, filters, sort, showDismissed, t]);

  // Keep the selection to rows that still exist and can be acted on.
  useEffect(() => {
    const valid = new Set(results.filter((r) => !r.application && !r.dismissal).map((r) => r.id));
    setSelected((current) => new Set([...current].filter((id) => valid.has(id))));
  }, [results]);

  if (!data) return html`<section class="card empty" aria-busy="true"></section>`;
  if (!run) {
    return html`
      <${EmptyState} title=${setupRequired ? t('setup.title') : t('empty.noRuns')}
        body=${setupRequired ? t('setup.body') : t('empty.noRunsBody')}
        command=${commandFor(commands, setupRequired ? 'setup' : 'job-search')} />`;
  }

  const track = (ids, applied) => onAction(async () => {
    const result = await api.track(ids, applied);
    setSelected(new Set());
    const job = result.applications[0] && result.applications[0].job_id;
    return {
      message: t(applied ? 'toast.trackedApplied' : 'toast.tracked', { count: ids.length, job }),
      undo: async () => { await api.untrack(ids); return t('toast.undone'); },
    };
  });
  const dismiss = (ids, reason, note) => onAction(async () => {
    await api.dismiss(ids, reason, note);
    setExpanded((current) => { const next = new Set(current); ids.forEach((id) => next.delete(id)); return next; });
    return {
      message: t('toast.dismissed', { count: ids.length, reason: t('dismiss.' + reason).replace('…', '') }),
      undo: async () => { await api.undismiss(ids); return t('toast.undone'); },
    };
  });
  const restore = (ids) => onAction(async () => {
    await api.undismiss(ids);
    return { message: t('toast.restored') };
  });

  const withEstimates = results.some((r) => r.estimate || r.fit);
  const columns = [
    { key: 'score', label: t('column.score'), sortable: true, width: withEstimates ? '84px' : '72px',
      render: (r) => html`<div class="stack chance-fit">
        ${r.score ? html`<span class=${'score ' + tone(r.score.total)}>${r.score.total}</span>`
          : html`<span class="score none">–</span>`}
        ${r.estimate && html`<${ChanceCell} estimate=${r.estimate} compact />`}
        ${r.fit && html`<${FitCell} fit=${r.fit} compact />`}
      </div>` },
    { key: 'title', label: t('column.job'), sortable: true,
      render: (r) => html`
        <div class="job">
          <span class="job-title">${r.title}</span>
          <span class="job-company">${r.company}</span>
          <div class="tags">
            ${r.form_question_count > 0 && html`<span class="tag info">${t('row.form', { count: r.form_question_count })}</span>`}
            ${r.flags.map((flag) => html`<span class="tag warn">${flag}</span>`)}
            <${DuplicateMark} row=${r} run=${run} />
          </div>
        </div>` },
    { key: 'conditions', label: t('column.conditions'),
      render: (r) => html`
        <div class="tags">
          ${r.contract_type && html`<span class="cond">${t('contract.' + r.contract_type)}</span>`}
          <${WorkModeEditor} posting=${r} onAction=${onAction} />
          ${(r.location || r.country) && html`<span class="cond">${r.work_mode === 'remote'
            ? (fmt.country(r.country) || r.location) : r.location}</span>`}
        </div>` },
    { key: 'salary', label: t('column.salary'), sortable: true, render: (r) => html`<${SalaryCell} salary=${r.salary} />` },
    { key: 'published', label: t('column.published'), sortable: true, width: '96px',
      render: (r) => (r.posted_at ? html`<div class="stack">
        <span>${fmt.ago(r.posted_at)}</span><span class="small">${fmt.dayMonth(r.posted_at)}</span></div>`
        : html`<span class="small">${t('row.dateUnknown')}</span>`) },
    { key: 'source', label: t('column.source'), sortable: true, width: '120px',
      render: (r) => html`<div class="stack">
        ${safeHref(r.url) ? html`<a class="source" href=${safeHref(r.url)} target="_blank"
          rel="noopener noreferrer" aria-label=${t('row.openSource', { site: providerName(r.provider, run) })}>
          ${providerName(r.provider, run)}${Icon.External()}</a>` : providerName(r.provider, run)}
        ${r.source_site && html`<span class="small source-site" title=${t('row.sourceSite')}>${r.source_site}</span>`}
      </div>` },
    { key: 'actions', label: t('column.actions'), width: '250px',
      render: (r) => html`<${RowActions} row=${r} onTrack=${track} onDismiss=${dismiss} onRestore=${restore} />` },
  ];

  const rows = view.shown.map((r) => Object.assign(r, { __noSelect: Boolean(r.application || r.dismissal) }));

  return html`
    <${RunSummary} data=${data} runId=${runId} onRunChange=${(id) => { setExpanded(new Set()); onRunChange(id); }}
      showFiltered=${showFiltered} onToggleFiltered=${() => setShowFiltered(!showFiltered)}
      commands=${commands} onOpenProviders=${() => setProvidersOpen(true)} />
    ${showFiltered && html`<${FilteredList} data=${data} />`}
    <${FilterBar} sorts=${SORTS.filter((key) => (key !== 'chance' || results.some((r) => r.estimate))
      && (key !== 'fit' || results.some((r) => r.fit)))} filters=${filters} setFilters=${changeFilters} sort=${sort} setSort=${setSort}
      providers=${providers} selectedCount=${selected.size} onBulk=${(applied) => track([...selected], applied)} />
    <section class="card results" aria-label=${t('tabs.search')}>
      ${rows.length === 0 ? html`
        <div class="empty">
          <p>${results.length === 0 ? t('empty.noResults') : t('empty.noRows')}</p>
          ${results.length > 0 && html`<button type="button" class="btn"
            onClick=${() => changeFilters(emptyFilters(null))}>${t('filters.clear')}</button>`}
        </div>` : html`
        <${DataTable} columns=${columns} rows=${rows} rowKey=${(r) => r.id}
          rowLabel=${(r) => `${r.title} · ${r.company}`} caption=${t('run.latest')}
          sort=${sort} onSort=${(key) => setSort(sort.key === key
            ? { key, dir: sort.dir === 'asc' ? 'desc' : 'asc' }
            : { key, dir: key === 'title' || key === 'company' || key === 'source' ? 'asc' : 'desc' })}
          selected=${selected}
          onSelect=${(id, on) => { const next = new Set(selected); on ? next.add(id) : next.delete(id); setSelected(next); }}
          onSelectAll=${(on) => setSelected(on ? new Set(rows.filter((r) => !r.__noSelect).map((r) => r.id)) : new Set())}
          expanded=${expanded}
          onExpand=${(id) => { const next = new Set(expanded); next.has(id) ? next.delete(id) : next.add(id); setExpanded(next); }}
          renderDetail=${(r) => html`<${RowDetail} row=${r} run=${run} onTrack=${track} onDismiss=${dismiss} onRestore=${restore} />`}
          rowClass=${(r) => (r.dismissal ? 'dismissed' : '')} />`}
    </section>
    <p class="footer" role="status">
      <span>${t('footer.showing', { shown: view.shown.length, total: view.total })}</span>
      ${view.hidden.map((h) => html`<span>· ${t('footer.hiddenBy', { count: h.count, filter: h.label })}</span>`)}
      ${view.dismissed > 0 && html`<span>· ${t('footer.dismissed', { count: view.dismissed })}</span>
        <button type="button" class="link-btn" onClick=${() => setShowDismissed(!showDismissed)}>
          ${showDismissed ? t('footer.hideDismissed') : t('footer.showDismissed')}</button>`}
    </p>
    <${ProvidersDialog} open=${providersOpen} onClose=${() => setProvidersOpen(false)} />`;
}
