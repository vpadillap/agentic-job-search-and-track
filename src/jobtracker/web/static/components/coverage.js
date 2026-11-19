// Global and local job sites: the coverage tag next to a site's name and the country
// filter above a job-site list. Filtering only hides rows; it never switches a site.
import { html } from '../vendor/preact-htm.js';
import { useUi } from './shell.js';

export const ALL = 'all';

export function CoverageTag({ provider }) {
  const { t } = useUi();
  const privateTag = provider.origin === 'private'
    && html`<span class="tag coverage private" title=${t('coverage.privateHint')}>${t('coverage.private')}</span>`;
  if (!provider.coverage) return privateTag || null;
  const text = provider.coverage === 'global'
    ? t('coverage.global')
    : t('coverage.local', { countries: provider.countries.join(', ') });
  return html`<span class="tag coverage" data-coverage=${provider.coverage}>${text}</span>${privateTag}`;
}

// Every country named by a local site, sorted.
export function siteCountries(providers) {
  const found = new Set();
  (providers || []).forEach((p) => (p.countries || []).forEach((c) => found.add(c)));
  return [...found].sort();
}

export const defaultCountry = (profileCountry) => profileCountry || ALL;

// Global sites plus the local sites of `country`; everything for ALL. A site whose
// file is invalid (no coverage) is always shown, so its problem stays visible.
export function filterByCountry(providers, country) {
  if (country === ALL) return providers;
  return providers.filter((p) => !p.coverage || p.coverage === 'global'
    || (p.countries || []).includes(country));
}

// Job sites have a switch; salary sources never do (they are always used), so the
// switch lists show job sites and one line names the salary sources.
export const jobSites = (providers) => (providers || []).filter((p) => p.kind !== 'salary');

export function SalarySourcesNote({ providers, country }) {
  const { t } = useUi();
  const names = filterByCountry((providers || []).filter((p) => p.kind === 'salary' || p.kind === 'both'),
    country).map((p) => p.name);
  if (!names.length) return null;
  return html`<p class="small salary-sources">${t('providers.salarySources', { names: names.join(', ') })}</p>`;
}

export function CountryFilter({ providers, profileCountry, value, onChange, id }) {
  const { t } = useUi();
  const countries = siteCountries(providers);
  if (profileCountry && !countries.includes(profileCountry)) countries.unshift(profileCountry);
  if (!countries.length) return null;
  return html`
    <label class="run-select coverage-filter" for=${id}>
      ${t('coverage.filter')}
      <select id=${id} value=${value} onChange=${(e) => onChange(e.currentTarget.value)}>
        <option value=${ALL}>${t('coverage.all')}</option>
        ${countries.map((c) => html`
          <option value=${c}>${t(c === profileCountry ? 'coverage.yours' : 'coverage.country',
            { country: c })}</option>`)}
      </select>
    </label>`;
}
