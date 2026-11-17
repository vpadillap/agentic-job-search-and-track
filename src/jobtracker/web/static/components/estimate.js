// Interview-chance estimates and the fit-to-you label, shown only when the server sends them
// (validated models at the predictive level or above).
import { html } from '../vendor/preact-htm.js';
import { useUi } from './shell.js';

const pct = (value) => `${Math.round(value * 100)}%`;

/** "dimension=value" → localized "Dimension: value". */
export function featureText(t, feature) {
  const [dimension, value] = feature.split('=');
  const name = t('dim.' + dimension);
  const shown = t('group.' + value);
  return `${name === 'dim.' + dimension ? dimension : name}: ${shown === 'group.' + value ? value : shown}`;
}

export function ChanceCell({ estimate, compact = false }) {
  const { t } = useUi();
  if (!estimate) return html`<span class="score none">–</span>`;
  const label = t('estimate.label.' + estimate.label);
  return html`<span class=${'confidence ' + estimate.label}
    title=${`${label} · ${t('estimate.range', { low: pct(estimate.low), high: pct(estimate.high) })}`}>
    ${compact ? pct(estimate.probability) : `${label} · ${pct(estimate.probability)}`}</span>`;
}

export function FitCell({ fit, compact = false }) {
  const { t } = useUi();
  if (!fit) return html`<span class="score none">–</span>`;
  if (compact) {
    return html`<span class=${'small fit-text fit-' + fit.label} title=${t('fit.meaning')}>
      ${t('fit.short', { label: t('estimate.label.' + fit.label).toLowerCase() })}</span>`;
  }
  return html`<span class=${'criteria fit-' + fit.label} title=${t('fit.meaning')}>
    ${t('estimate.label.' + fit.label)}</span>`;
}

/** Detail panel: the estimate with its range, the main factors, and what fit means. */
export function EstimatePanel({ estimate, fit }) {
  const { t } = useUi();
  if (!estimate && !fit) return null;
  return html`
    <div class="panel estimate-panel">
      ${estimate && html`
        <h2>${t('estimate.title')}</h2>
        <div style=${{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
          <span class="big-money">${pct(estimate.probability)}</span>
          <span class=${'confidence ' + estimate.label}>${t('estimate.label.' + estimate.label)}</span>
        </div>
        <span class="small">${t('estimate.range', { low: pct(estimate.low), high: pct(estimate.high) })}
          · ${t('estimate.base', { rate: pct(estimate.base_rate) })}</span>
        ${estimate.factors.length > 0 && html`<ul class="factors">${estimate.factors.map((f) => html`
          <li class=${'factor ' + f.effect}>${f.effect === 'up' ? '↑' : '↓'} ${featureText(t, f.feature)}</li>`)}</ul>`}
        <span class="note">${t('estimate.note')}</span>`}
      ${fit && html`
        <h2>${t('fit.title')}</h2>
        <span class=${'criteria fit-' + fit.label}>${t('estimate.label.' + fit.label)}</span>
        <span class="note">${t('fit.meaning')}</span>`}
    </div>`;
}
