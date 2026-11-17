// Panel entry: hash routing, language, change polling, and the active board.
import { html, render, useState, useEffect, useRef, useMemo, useCallback } from './vendor/preact-htm.js';
import { api } from './api.js';
import { loadCatalogs, makeTranslator, initialLanguage, rememberLanguage } from './i18n.js';
import { makeFormat } from './format.js';
import { Ui, TABS, Header, Banner, Toast, EmptyState, Placeholder, SeasonBanner } from './components/shell.js';
import { SearchBoard } from './boards/search.js';
import { ApplicationsBoard } from './boards/applications.js';
import { LearningBoard } from './boards/learning.js';
import { ProfileBoard } from './boards/profile.js';

const POLL_MS = 3000;

function rememberTab(name) {
  try { localStorage.setItem('jt.tab', name); } catch (error) { /* storage unavailable */ }
}

function tabFromHash() {
  const name = location.hash.replace('#', '');
  if (TABS.includes(name)) { rememberTab(name); return name; }
  try {
    const stored = localStorage.getItem('jt.tab');
    if (TABS.includes(stored)) return stored;
  } catch (error) { /* storage unavailable */ }
  return 'search';
}

/** True while the user is typing somewhere: new data must not interrupt them. */
function isEditing() {
  const active = document.activeElement;
  if (!active) return false;
  if (active.tagName === 'TEXTAREA') return true;
  if (active.tagName === 'INPUT') return !['checkbox', 'radio', 'button', 'submit'].includes(active.type);
  return active.isContentEditable === true;
}

function App({ initialState }) {
  const [state, setState] = useState(initialState);
  const [lang, setLang] = useState(() => initialLanguage(initialState && initialState.language));
  const [tab, setTab] = useState(tabFromHash);
  const [board, setBoard] = useState(null);
  const [apps, setApps] = useState(null);
  const [runId, setRunId] = useState(null);
  const [viewSeason, setViewSeason] = useState(null);   // an earlier season, or null
  const [stale, setStale] = useState(false);
  const [toast, setToast] = useState(null);
  const counter = useRef(initialState && initialState.changes ? initialState.changes.counter : null);

  const ui = useMemo(() => ({ t: makeTranslator(lang), fmt: makeFormat(lang), lang }), [lang]);
  useEffect(() => { document.documentElement.lang = lang; document.title = ui.t('brand'); }, [lang]);

  // Routing: the hash is the source of truth; the last tab is remembered.
  useEffect(() => {
    const onHash = () => setTab(tabFromHash());
    window.addEventListener('hashchange', onHash);
    if (!location.hash) history.replaceState(null, '', '#' + tab);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const showError = (error) => setToast({
    error: true,
    message: error.code === 'offline' ? ui.t('error.offline') : ui.t('error.generic', { message: error.message }),
  });

  const reload = useCallback(async (wantedRun = runId) => {
    try {
      const next = await api.state();
      setState(next);
      if (next.changes) counter.current = next.changes.counter;
      if (!next.initialized) setBoard(null);
      else if (tab === 'applications') setApps(await api.applications(viewSeason));
      else if (tab === 'search') setBoard(await api.search(wantedRun, viewSeason));
      setStale(false);
    } catch (error) {
      if (error.status === 404 && wantedRun) { setRunId(null); return reload(null); }
      showError(error);
    }
    return undefined;
  }, [runId, ui, tab, viewSeason]);

  useEffect(() => { reload(runId); }, [runId, tab, viewSeason]);

  const openSeason = (number) => {
    setRunId(null);
    setApps(null);
    setBoard(null);
    setViewSeason(number);
    location.hash = '#applications';
  };
  // An earlier season is a view of Search and Applications; other tabs return to the current one.
  useEffect(() => { if (!['search', 'applications'].includes(tab)) setViewSeason(null); }, [tab]);
  const backToActive = () => { setRunId(null); setApps(null); setBoard(null); setViewSeason(null); };

  // Freshness: poll the change counter while the page is visible.
  useEffect(() => {
    const tick = async () => {
      if (document.visibilityState !== 'visible') return;
      try {
        const health = state && state.initialized ? await api.changes() : await api.state();
        const value = health.counter ?? (health.changes && health.changes.counter) ?? null;
        const initializedNow = health.initialized !== undefined ? health.initialized : true;
        if (value !== counter.current || (state && !state.initialized && initializedNow)) {
          if (isEditing()) setStale(true);
          else reload();
        } else if (stale && !isEditing()) {
          reload();
        }
      } catch (error) { /* the next tick retries */ }
    };
    const timer = setInterval(tick, POLL_MS);
    return () => clearInterval(timer);
  }, [state, stale, reload]);

  const changeLanguage = async (next) => {
    setLang(next);
    rememberLanguage(next);
    if (state && state.initialized) {
      try {
        const result = await api.setLanguage(next);
        setState((s) => ({ ...s, language: result.language, commands: result.commands }));
        await reload();                     // server-localized names (statuses) follow the switch
      } catch (error) { showError(error); }
    }
  };

  // Every write: run it, reload, and offer undo in a toast.
  const onAction = async (action) => {
    try {
      const outcome = await action();
      await reload();
      if (outcome) {
        setToast({
          message: outcome.message,
          undo: outcome.undo && (async () => {
            try {
              const message = await outcome.undo();
              await reload();
              setToast({ message });
            } catch (error) { showError(error); }
          }),
        });
      }
    } catch (error) {
      showError(error);
      await reload();
    }
  };

  const counts = state && state.header ? state.header.counts : {};
  let content;
  if (state && !state.initialized) {
    content = html`<${EmptyState} title=${ui.t('setup.title')} body=${ui.t('setup.body')}
      command=${(state.commands.find((c) => c.id === 'setup') || {}).example || '/setup'} />`;
  } else if (tab === 'search') {
    content = html`<${SearchBoard} data=${board} runId=${runId} onRunChange=${setRunId}
      commands=${state && state.commands} setupRequired=${state && state.setup_required} onAction=${onAction} />`;
  } else if (tab === 'applications') {
    content = html`<${ApplicationsBoard} data=${apps} version=${state && state.changes ? state.changes.counter : 0}
      commands=${state && state.commands} onAction=${onAction} onReload=${() => reload()} />`;
  } else if (tab === 'profile') {
    content = html`<${ProfileBoard} version=${state && state.changes ? state.changes.counter : 0}
      onAction=${onAction} onViewSeason=${openSeason} />`;
  } else if (tab === 'learning') {
    content = html`<${LearningBoard} version=${state && state.changes ? state.changes.counter : 0}
      commands=${state && state.commands} onAction=${onAction} />`;
  } else {
    content = html`<${Placeholder} tab=${tab} />`;
  }
  const seasonBanner = viewSeason && ['search', 'applications'].includes(tab)
    && html`<${SeasonBanner} season=${viewSeason} onBack=${backToActive} />`;

  return html`
    <${Ui.Provider} value=${ui}>
      <${Header} state=${state} lang=${lang} onLanguage=${changeLanguage} onReload=${() => reload()}
        tab=${tab} viewSeason=${viewSeason} counts=${{ search: counts.search ?? null, applications: counts.applications ?? null,
          learning: counts.learning ? counts.learning : null }} />
      ${stale && html`<${Banner} onLoad=${() => reload()} />`}
      <main class="main" id="main">${seasonBanner}${content}</main>
      <${Toast} toast=${toast} onClose=${() => setToast(null)} />
    </${Ui.Provider}>`;
}

async function start() {
  await loadCatalogs();
  let state = null;
  try { state = await api.state(); } catch (error) { state = null; }
  render(html`<${App} initialState=${state} />`, document.getElementById('app'));
}

start();
