// Board 4, Profile & agent: the active season, the profile, pending work, commands,
// what the agent always respects, and the job sites it uses. Read-mostly: the only
// writes are the provider switch and including or excluding a suggested title.
import { html, useState, useEffect } from '../vendor/preact-htm.js';
import { api } from '../api.js';
import { useUi, CommandChip, CopyButton, Menu } from '../components/shell.js';

const ACCESS = ['chrome-extension', 'playwright', 'scrapling', 'http', 'web-search'];

function commandFor(commands, id) {
  const found = (commands || []).find((c) => c.id === id);
  return found ? found.example : null;
}

// ── season ────────────────────────────────────────────────────────────────

function SeasonCard({ season, seasons, commands, onViewSeason }) {
  const { t, fmt } = useUi();
  const earlier = seasons.filter((s) => !s.active).reverse();
  const command = commandFor(commands, 'new-season');
  return html`
    <section class="card pa-season" aria-labelledby="pa-season-title">
      <span class="pa-eyebrow">${t('season.active')}</span>
      <h2 id="pa-season-title">${t('season.title', { number: season.number, date: fmt.longDate(season.started_at) })}</h2>
      ${season.label && html`<p class="pa-season-label">${season.label}</p>`}
      <p>${t('season.explain')}</p>
      <div class="pa-season-actions">
        ${command && html`<${CommandChip} command=${command} note=${false} />`}
        ${earlier.map((s) => html`
          <button type="button" class="link-btn pa-season-link" onClick=${() => onViewSeason(s.number)}>
            ${t('season.viewEarlier', { number: s.number })}</button>`)}
      </div>
    </section>`;
}

// ── profile ───────────────────────────────────────────────────────────────

function TitleChip({ item, onDecide }) {
  const { t } = useUi();
  if (item.state === 'suggested') {
    return html`<${Menu} buttonClass="pa-title suggested" menuLabel=${t('profile.suggestedMenu', { title: item.title })}
      label=${item.title}>
      ${(close) => html`
        ${item.reason && html`<p class="pa-menu-note">${item.reason}</p>`}
        <div class="pa-menu-actions">
          <button type="button" class="btn btn-sm btn-dark" onClick=${() => { close(); onDecide(item.title, 'included'); }}>
            ${t('profile.include')}</button>
          <button type="button" class="btn btn-sm" onClick=${() => { close(); onDecide(item.title, 'excluded'); }}>
            ${t('profile.exclude')}</button>
        </div>`}
    </${Menu}>`;
  }
  const text = item.state === 'under_review' ? t('profile.underReview', { title: item.title }) : item.title;
  return html`<span class=${'pa-title ' + item.state} title=${item.reason || undefined}>
    ${item.state === 'excluded' ? html`<s>${text}</s>` : text}
    <span class="sr-only">${' · ' + t('profile.state.' + item.state)}</span></span>`;
}

function needsRows(profile, t, fmt) {
  const rows = [];
  const add = (key, value) => { if (value !== null && value !== undefined && value !== '') rows.push([key, value]); };
  add('work_modes', profile.work_modes.length ? fmt.list(profile.work_modes.map((m) => t('mode.' + m))) : null);
  add('contract_types', profile.contract_types.length
    ? fmt.list(profile.contract_types.map((c) => t('contract.' + c))) : null);
  add('country', profile.country ? fmt.country(profile.country) : null);
  add('locations', profile.locations.length ? fmt.list(profile.locations) : null);
  if (profile.remote_scope) {
    add('remote_scope', t('profile.scope.' + profile.remote_scope)
      + (profile.remote_region ? ` · ${profile.remote_region}` : ''));
  }
  if (profile.minimum_salary) {
    const s = profile.minimum_salary;
    add('minimum_salary', t('profile.salary', { amount: fmt.money(s.amount, s.currency), basis: t('profile.basis.' + s.basis) }));
  }
  add('languages', profile.languages.length
    ? fmt.list(profile.languages.map((l) => (l.level ? `${l.language} ${l.level}` : l.language))) : null);
  add('seniority', profile.seniority);
  add('industries_preferred', profile.industries_preferred.length ? fmt.list(profile.industries_preferred) : null);
  add('industries_avoided', profile.industries_avoided.length ? fmt.list(profile.industries_avoided) : null);
  add('companies_excluded', profile.companies_excluded.length ? fmt.list(profile.companies_excluded) : null);
  add('availability', profile.availability);
  add('posting_age_days', t('profile.ageDays', { count: profile.posting_age_days }));
  return rows;
}

function ProfileCard({ profile, resumes, rescoreSince, onDecide }) {
  const { t, fmt } = useUi();
  if (!profile) {
    return html`<section class="card pa-card"><h2>${t('profile.none')}</h2></section>`;
  }
  const groups = ['included', 'under_review', 'excluded'];
  const shown = profile.titles.filter((item) => groups.includes(item.state))
    .sort((a, b) => groups.indexOf(a.state) - groups.indexOf(b.state));
  const suggested = profile.titles.filter((item) => item.state === 'suggested');
  return html`
    <section class="card pa-card" aria-labelledby="pa-profile-title">
      <div class="pa-head">
        <h2 id="pa-profile-title">${t('profile.title', { version: profile.version })}</h2>
        <span class="small">${t('profile.byAgent')}</span>
      </div>
      ${resumes.length === 0 ? html`<p class="note">${t('profile.noResume')}</p>` : resumes.map((r) => html`
        <div class="pa-resume">
          <div class="pa-resume-text">
            <span class="mono">${r.original_name}</span>
            <span class="small">${t('profile.resumeUpdated', { date: fmt.dayMonth(r.imported_at), language: (r.language || '').toUpperCase() })}
              ${rescoreSince && r.imported_at >= rescoreSince ? ' · ' + t('profile.rescored') : ''}</span>
          </div>
          <a class="small-link" href=${api.resumeUrl(r.id)} download>${t('profile.open')}</a>
        </div>`)}
      <h3 class="pa-subhead">${t('profile.titles')}</h3>
      <div class="chips pa-titles">
        ${shown.length === 0 ? html`<span class="small">${t('profile.noTitles')}</span>`
          : shown.map((item) => html`<${TitleChip} item=${item} />`)}
      </div>
      ${suggested.length > 0 && html`
        <div class="chips pa-titles">
          <span class="small">${t('profile.suggested')}</span>
          ${suggested.map((item) => html`<${TitleChip} item=${item} onDecide=${onDecide} />`)}
        </div>`}
      <dl class="pa-needs">
        ${needsRows(profile, t, fmt).map(([key, value]) => html`
          <dt>${t('profile.field.' + key)}</dt><dd>${value}</dd>`)}
      </dl>
      <p class="small pa-foot">${t('profile.howToChange')}</p>
    </section>`;
}

// ── pending ───────────────────────────────────────────────────────────────

/** One line per posting, with everything pending on it. */
function groupByPosting(items) {
  const groups = new Map();
  for (const item of items) {
    if (!groups.has(item.posting_id)) groups.set(item.posting_id, { ...item, items: [] });
    groups.get(item.posting_id).items.push(item);
  }
  return [...groups.values()];
}

function PendingCard({ items, commands }) {
  const { t } = useUi();
  const batch = commandFor(commands, 'prepare-documents');
  const count = items ? items.length : 0;
  return html`
    <section class=${'card pa-card' + (count ? ' pa-pending' : '')} aria-labelledby="pa-pending-title">
      <div class="pa-head">
        <h2 id="pa-pending-title">${t('pa.pendingTitle', { count })}</h2>
        <span class="small">${t('pa.pendingSource')}</span>
      </div>
      ${items === null ? html`<p class="note">${t('pending.loading')}</p>`
        : count === 0 ? html`<p class="note">${t('pending.none')}</p>`
        : html`<ul class="pa-list">${groupByPosting(items).map((group) => html`
            <li class="pa-item">
              <strong>${group.items.map((item) => t('pending.kind.' + item.kind, { missing: item.missing || 0 })).join(' · ')}</strong>
              <span class="small">${group.job_id ? group.job_id + ' · ' : ''}${group.title} · ${group.company}</span>
            </li>`)}</ul>`}
      ${batch && count > 0 && html`<${CommandChip} command=${batch} note=${false} />`}
    </section>`;
}

// ── commands ──────────────────────────────────────────────────────────────

function CommandsCard({ commands }) {
  const { t } = useUi();
  const available = (commands || []).filter((c) => c.available);
  return html`
    <section class="card pa-card" aria-labelledby="pa-commands-title">
      <h2 id="pa-commands-title">${t('pa.commandsTitle')}</h2>
      <ul class="pa-list pa-commands">
        ${available.map((c) => html`
          <li class="pa-command">
            <div class="pa-command-text">
              <code>${c.example}</code>
              <span class="small">${c.description}</span>
            </div>
            <${CopyButton} text=${c.example} label=${t('pa.copyCommand', { command: c.example })} />
          </li>`)}
      </ul>
      <p class="small pa-foot">${t('command.note')}</p>
    </section>`;
}

// ── memory ────────────────────────────────────────────────────────────────

function originBadge(rule, t, fmt) {
  if (rule.origin === 'system') {
    return html`<span class="pa-origin system">${t('memory.system', { date: fmt.dayMonth(rule.created_at) })}</span>`;
  }
  if (rule.origin === 'user') {
    return html`<span class="pa-origin user">${t('memory.user', { date: fmt.dayMonth(rule.created_at) })}</span>`;
  }
  return html`<span class="pa-origin learned">${t('memory.learned', { date: fmt.dayMonth(rule.applied_at || rule.updated_at) })}</span>
    ${rule.earlier_season && html`<span class="pa-origin earlier">${t('memory.earlierSeason')}</span>`}`;
}

function MemoryCard({ rules }) {
  const { t, fmt } = useUi();
  return html`
    <section class="card pa-card" aria-labelledby="pa-memory-title">
      <div class="pa-head">
        <h2 id="pa-memory-title">${t('memory.title')}</h2>
        <span class="small">${t('memory.sub')}</span>
      </div>
      <ul class="pa-list">
        ${rules.map((rule) => html`
          <li class="pa-rule">
            <span>${rule.text}</span>
            <span class="pa-origins">${originBadge(rule, t, fmt)}</span>
          </li>`)}
      </ul>
      <p class="small pa-foot">${t('memory.how')}</p>
    </section>`;
}

// ── providers ─────────────────────────────────────────────────────────────

function providerStatus(p, t, fmt) {
  if (!p.enabled) {
    return { tone: 'off', text: p.switched_at ? t('prov.disabledOn', { date: fmt.dayMonth(p.switched_at) }) : t('prov.disabled') };
  }
  if (!p.valid) return { tone: 'warn', text: t('prov.invalid') };
  if (p.live_walk) return { tone: 'warn', text: t('prov.presence') };
  if (p.last_status === 'ok') return { tone: 'ok', text: t('prov.ok', { date: fmt.dayMonth(p.last_run_at) }) };
  if (p.last_status === 'failed') return { tone: 'bad', text: t('prov.failed', { date: fmt.dayMonth(p.last_run_at) }) };
  if (p.last_status === 'skipped') return { tone: 'warn', text: t('prov.skipped', { date: fmt.dayMonth(p.last_run_at) }) };
  return { tone: 'idle', text: t('prov.unused') };
}

function ProvidersCard({ providers, onToggle }) {
  const { t, fmt } = useUi();
  return html`
    <section class="card pa-card" aria-labelledby="pa-providers-title">
      <div class="pa-head">
        <h2 id="pa-providers-title">${t('providers.title')}</h2>
        <span class="small">${t('prov.sub')}</span>
      </div>
      ${providers.length === 0 ? html`<p class="note">${t('providers.empty')}</p>` : html`
        <ul class="pa-list">
          ${providers.map((p) => {
            const status = providerStatus(p, t, fmt);
            const access = ACCESS.includes(p.access) ? t('access.' + p.access) : p.access;
            return html`
              <li class="pa-provider">
                <div class="pa-provider-name">
                  <strong>${p.name}</strong>
                  <span class="small">${access}${p.requires_login ? ' · ' + t('prov.login') : ''}</span>
                </div>
                <div class="pa-provider-state">
                  <span class=${'pa-status ' + status.tone} title=${p.last_error || undefined}>
                    <span class="doc-dot" aria-hidden="true"></span>${status.text}</span>
                  <span class="mono small">${p.file}</span>
                </div>
                <button type="button" role="switch" class="pa-switch" aria-checked=${String(p.enabled)}
                  aria-label=${t('prov.switch', { name: p.name })} onClick=${() => onToggle(p, !p.enabled)}>
                  <span class="pa-knob"></span></button>
              </li>`;
          })}
        </ul>`}
    </section>`;
}

// ── board ─────────────────────────────────────────────────────────────────

export function ProfileBoard({ version, onAction, onViewSeason }) {
  const { t } = useUi();
  const [data, setData] = useState(null);
  const [pending, setPending] = useState(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true;
    api.profileBoard().then((r) => { if (live) { setData(r); setFailed(false); } })
      .catch(() => live && setFailed(true));
    api.pending().then((r) => live && setPending(r.pending)).catch(() => live && setPending([]));
    return () => { live = false; };
  }, [version]);

  if (failed && !data) return html`<section class="card empty"><p>${t('pending.failed')}</p></section>`;
  if (!data) return html`<section class="card empty" aria-busy="true"></section>`;

  const decide = (title, state) => onAction(async () => {
    await api.decideSuggestedTitle(title, state);
    return { message: t(state === 'included' ? 'profile.included' : 'profile.excluded', { title }) };
  });
  const toggle = (p, enabled) => onAction(async () => {
    await api.setProvider(p.id, enabled);
    return { message: t(enabled ? 'prov.enabledToast' : 'prov.disabledToast', { name: p.name }) };
  });

  return html`
    <div class="pa-grid">
      <div class="pa-col">
        <${SeasonCard} season=${data.season} seasons=${data.seasons} commands=${data.commands}
          onViewSeason=${onViewSeason} />
        <${ProfileCard} profile=${data.profile} resumes=${data.base_resumes}
          rescoreSince=${data.rescore_since} onDecide=${decide} />
      </div>
      <div class="pa-col">
        <${PendingCard} items=${pending} commands=${data.commands} />
        <${CommandsCard} commands=${data.commands} />
      </div>
      <div class="pa-col">
        <${MemoryCard} rules=${data.rules} />
        <${ProvidersCard} providers=${data.providers} onToggle=${toggle} />
      </div>
    </div>`;
}
