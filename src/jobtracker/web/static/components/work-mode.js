// A posting's work mode with its detail ("Hybrid · 2 días presencial por semana").
// The chip opens an editor: the user sets or corrects both; the value is kept as theirs.
import { html, useState } from '../vendor/preact-htm.js';
import { useUi, Menu } from './shell.js';
import { api } from '../api.js';

const MODES = ['remote', 'hybrid', 'onsite'];
export const DETAIL_MAX = 200;

// The text shown for a posting's work mode, or null when nothing is known.
export function workModeText(t, posting) {
  const parts = [posting.work_mode && t('mode.' + posting.work_mode), posting.work_mode_detail];
  const text = parts.filter(Boolean).join(' · ');
  return text || null;
}

export function WorkModeEditor({ posting, onAction, extra = null }) {
  const { t } = useUi();
  const [mode, setMode] = useState(posting.work_mode || '');
  const [detail, setDetail] = useState(posting.work_mode_detail || '');
  const text = workModeText(t, posting);
  const edited = posting.work_mode_source === 'user';
  const shown = [text, extra].filter(Boolean).join(' · ');
  const reset = () => { setMode(posting.work_mode || ''); setDetail(posting.work_mode_detail || ''); };
  const label = html`
    <span class="wm-text" title=${shown || t('workMode.notStated')}>${shown || t('workMode.notStated')}</span>
    ${edited && html`<span class="wm-edited" title=${t('workMode.editedTitle')}>${t('workMode.edited')}</span>`}`;
  return html`
    <${Menu} label=${label} buttonClass=${'cond wm-chip' + (text ? '' : ' empty')}
      menuLabel=${t('workMode.edit', { value: text || t('workMode.notStated') })}>
      ${(close) => html`
        <form class="wm-form" onSubmit=${(e) => {
          e.preventDefault();
          const value = { work_mode: mode || null, detail: detail.trim() || null };
          close();
          onAction(async () => {
            await api.setWorkMode(posting.id, value.work_mode, value.detail);
            return { message: t('workMode.saved') };
          });
        }} onReset=${reset}>
          <fieldset>
            <legend>${t('workMode.legend')}</legend>
            ${[...MODES, ''].map((value) => html`
              <label key=${value || 'none'}>
                <input type="radio" name=${'wm-' + posting.id} value=${value} checked=${mode === value}
                  onChange=${() => setMode(value)} />
                ${value ? t('mode.' + value) : t('workMode.notStated')}
              </label>`)}
          </fieldset>
          <div class="menu-form">
            <label class="sr-only" for=${'wm-detail-' + posting.id}>${t('workMode.detail')}</label>
            <input id=${'wm-detail-' + posting.id} type="text" maxlength=${DETAIL_MAX} value=${detail}
              placeholder=${t('workMode.detailPlaceholder')} onInput=${(e) => setDetail(e.currentTarget.value)} />
            <button type="submit" class="btn btn-sm btn-dark">${t('workMode.save')}</button>
          </div>
        </form>`}
    </${Menu}>`;
}
