// Panel strings from locales/<lang>.json. Plural entries are {one, other, ...} objects
// chosen with Intl.PluralRules. Text written by the agent or the user is never translated.

export const LANGUAGES = ['en', 'es'];
const catalogs = {};

export async function loadCatalogs() {
  await Promise.all(LANGUAGES.map(async (lang) => {
    const response = await fetch(`/static/locales/${lang}.json`);
    catalogs[lang] = await response.json();
  }));
}

/** The best Intl locale for a panel language: the browser's own variant when it matches. */
export function intlLocale(lang) {
  const preferred = (navigator.languages || [navigator.language || '']).find(
    (l) => l && l.toLowerCase().startsWith(lang));
  return preferred || lang;
}

export function makeTranslator(lang) {
  const catalog = catalogs[lang] || catalogs.en || {};
  const fallback = catalogs.en || {};
  const plurals = new Intl.PluralRules(intlLocale(lang));
  return function t(key, params = {}) {
    let entry = key in catalog ? catalog[key] : fallback[key];
    if (entry === undefined) return key;
    if (typeof entry === 'object') {
      entry = entry[plurals.select(Number(params.count ?? 0))] ?? entry.other;
    }
    return entry.replace(/\{(\w+)\}/g, (match, name) => (name in params ? String(params[name]) : match));
  };
}

export function initialLanguage(serverLanguage) {
  if (LANGUAGES.includes(serverLanguage)) return serverLanguage;
  try {
    const stored = localStorage.getItem('jt.lang');
    if (LANGUAGES.includes(stored)) return stored;
  } catch (error) { /* storage unavailable */ }
  return (navigator.language || 'en').toLowerCase().startsWith('es') ? 'es' : 'en';
}

export function rememberLanguage(lang) {
  try { localStorage.setItem('jt.lang', lang); } catch (error) { /* storage unavailable */ }
}
