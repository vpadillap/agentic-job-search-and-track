// The panel frame: header, tabs, command chip, empty states, toast.
import { html, createContext, useContext, useState, useEffect, useLayoutEffect, useRef } from '../vendor/preact-htm.js';
import * as Icon from './icons.js';
import { api } from '../api.js';

/** {t, fmt, lang}: translator, formatter, and the panel language. */
export const Ui = createContext(null);
export const useUi = () => useContext(Ui);

export const TABS = ['search', 'applications', 'learning', 'profile'];

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (error) {
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand('copy');
    area.remove();
    return ok;
  }
}

/** A command to paste into Claude Code, with a copy control that confirms. */
export function CommandChip({ command, label, note = true }) {
  const { t } = useUi();
  const [copied, setCopied] = useState(false);
  const timer = useRef(null);
  useEffect(() => () => clearTimeout(timer.current), []);
  const copy = async () => {
    if (await copyText(command)) {
      setCopied(true);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 2000);
    }
  };
  return html`
    <div class="command">
      ${label && html`<span class="command-label">${label}</span>`}
      <div class="command-box">
        <code>${command}</code>
        <button type="button" class="command-copy" onClick=${copy}
          aria-label=${copied ? t('command.copied') : t('command.copy')}>
          ${copied ? html`${Icon.Check(16)}<span>${t('command.copied')}</span>` : Icon.Copy()}
        </button>
      </div>
      <span class="sr-only" role="status" aria-live="polite">${copied ? t('command.copied') : ''}</span>
      ${note && html`<span class="command-note">${t('command.note')}</span>`}
    </div>`;
}

export function EmptyState({ title, body, command, heading = 'h1' }) {
  const Heading = heading;
  return html`
    <section class="card empty" aria-live="polite">
      <${Heading}>${title}</${Heading}>
      ${body && html`<p>${body}</p>`}
      ${command && html`<${CommandChip} command=${command} />`}
    </section>`;
}

export function Placeholder({ tab }) {
  const { t } = useUi();
  return html`<${EmptyState} title=${t('placeholder.title', { board: t('tabs.' + tab) })}
    body=${t('placeholder.' + tab)} />`;
}

/** What the agent has to do, item by item, and the one command that does it all. */
function PendingList({ commands, count, changes }) {
  const { t } = useUi();
  const [items, setItems] = useState(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true;
    api.pending().then((r) => { if (live) setItems(r.pending); }).catch(() => live && setFailed(true));
    return () => { live = false; };
  }, [count, changes && changes.counter]);
  const batch = commands.find((c) => c.id === 'prepare-documents');
  return html`
    <div class="pending-list" role="region" aria-label=${t('pending.title')}>
      <h2>${t('pending.title')}</h2>
      ${failed ? html`<p class="note">${t('pending.failed')}</p>`
        : items === null ? html`<p class="note">${t('pending.loading')}</p>`
        : items.length === 0 ? html`<p class="note">${t('pending.none')}</p>`
        : html`<ul>${items.map((item) => html`
            <li>
              <span class="pending-what">${t('pending.kind.' + item.kind, { missing: item.missing || 0 })}</span>
              <span class="pending-job">${item.job_id ? item.job_id + ' · ' : ''}${item.title} · ${item.company}</span>
            </li>`)}</ul>`}
      ${batch && items && items.length > 0 && html`<${CommandChip} command=${batch.example}
        label=${t('pending.command')} />`}
    </div>`;
}

export function Header({ state, lang, onLanguage, onReload, tab, counts }) {
  const { t, fmt } = useUi();
  const header = state && state.header;
  const profile = header && header.profile;
  const pending = header ? header.pending : 0;
  const changes = state && state.changes;
  return html`
    <header class="header">
      <div class="header-top">
        <div class="brand">
          ${Icon.Radar()}
          <div class="brand-text">
            <span class="brand-name">${t('brand')}</span>
            <span class="brand-sub">${t('header.local', { host: location.host })}</span>
          </div>
        </div>
        <div class="header-tools">
          ${state && state.initialized && html`
            <a class="header-chip" href="#profile">
              ${profile
                ? (profile.title ? t('header.profile', profile) : t('header.profileNoTitle', profile))
                : t('header.noProfile')}
            </a>
            <${Menu} buttonClass="header-chip raised" align="right"
              label=${html`<span class=${'dot' + (pending ? '' : ' idle')}></span>${t('header.pending', { count: pending })}`}>
              <${PendingList} commands=${state.commands || []} count=${pending} changes=${changes} />
            </${Menu}>`}
          <span class="header-meta">
            ${changes ? t('header.updated', { time: fmt.shortDateTime(changes.updated_at) }) : t('header.noData')}
            <button type="button" class="header-icon-btn" onClick=${onReload} aria-label=${t('header.reload')}
              title=${t('header.reload')}>${Icon.Reload()}</button>
          </span>
          <span class="header-meta" id="lang-label">${t('header.language')}</span>
          <div class="lang" role="group" aria-labelledby="lang-label">
            ${['es', 'en'].map((code) => html`
              <button type="button" lang=${code} aria-pressed=${String(lang === code)}
                onClick=${() => lang !== code && onLanguage(code)}>${code.toUpperCase()}</button>`)}
          </div>
        </div>
      </div>
      <nav class="tabs" aria-label=${t('tabs.label')}>
        ${TABS.map((name) => html`
          <a class="tab" href=${'#' + name} aria-current=${tab === name ? 'page' : undefined}>
            ${t('tabs.' + name)}
            ${name in counts && counts[name] !== null && html`<span class=${'count' + (name === 'learning' ? ' count-alert' : '')}>${counts[name]}</span>`}
          </a>`)}
      </nav>
    </header>`;
}

export function Banner({ onLoad }) {
  const { t } = useUi();
  return html`
    <div class="banner" role="status">
      <span>${t('header.newData')}</span>
      <button type="button" class="btn btn-sm" onMouseDown=${(e) => e.preventDefault()} onClick=${onLoad}>
        ${t('header.loadNow')}</button>
    </div>`;
}

/** A transient message with an optional undo action. */
export function Toast({ toast, onClose }) {
  const { t } = useUi();
  useEffect(() => {
    if (!toast) return undefined;
    const timer = setTimeout(onClose, toast.undo ? 7000 : 4000);
    return () => clearTimeout(timer);
  }, [toast]);
  if (!toast) return html`<div class="sr-only" role="status" aria-live="polite"></div>`;
  return html`
    <div class=${'toast' + (toast.error ? ' error' : '')} role="status" aria-live="polite">
      <span>${toast.message}</span>
      ${toast.undo && html`<button type="button" onClick=${async () => { onClose(); await toast.undo(); }}>
        ${t('action.undo')}</button>`}
    </div>`;
}

/** A button that opens a small popover; closes on Escape and outside click. */
export function Menu({ label, active = false, align = 'left', children, buttonClass = 'btn', menuLabel }) {
  const [open, setOpen] = useState(false);
  const wrap = useRef(null);
  const button = useRef(null);
  // Layout effect: focus moves into the menu and Escape works immediately after opening.
  useLayoutEffect(() => {
    if (!open) return undefined;
    const onDoc = (event) => { if (wrap.current && !wrap.current.contains(event.target)) setOpen(false); };
    const onKey = (event) => {
      if (event.key === 'Escape') { setOpen(false); button.current && button.current.focus(); }
    };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    const first = wrap.current && wrap.current.querySelector('.menu input, .menu button, .menu textarea');
    first && first.focus();
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);
  const close = () => { setOpen(false); button.current && button.current.focus(); };
  return html`
    <div class="menu-wrap" ref=${wrap}>
      <button type="button" ref=${button} class=${buttonClass + (active ? ' active' : '')}
        aria-expanded=${String(open)} aria-haspopup="true" onClick=${() => setOpen(!open)}
        aria-label=${menuLabel}>${label}</button>
      ${open && html`<div class=${'menu' + (align === 'right' ? ' right' : '')}>
        ${typeof children === 'function' ? children(close) : children}</div>`}
    </div>`;
}
