// Global and local job sites: the coverage tag next to a site's name and the country
// filter above a job-site list. Filtering only hides rows; it never switches a site.
import { html } from '../vendor/preact-htm.js';
import { useUi } from './shell.js';

export const ALL = 'all';

export function CoverageTag({ provider }) {
  const { t } = useUi();
  if (!provider.coverage) return null;
  const text = provider.coverage === 'global'
    ? t('coverage.global')
    : t('coverage.local', { countries: provider.countries.join(', ') });
  return html`<span class="tag coverage" data-coverage=${provider.coverage}>${text}</span>`;
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
