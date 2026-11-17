// A posting's description, verbatim, readable in full in the page (no inner scroll bar):
// its beginning is shown, and "Read the full description" reveals the rest in place.
import { html, useState, useRef, useLayoutEffect } from '../vendor/preact-htm.js';
import { useUi } from './shell.js';
import * as Icon from './icons.js';

export const safeHref = (url) => (/^https?:\/\//i.test(url || '') ? url : undefined);

export function PostingLink({ url, site, className = 'source' }) {
  const { t } = useUi();
  const href = safeHref(url);
  if (!href) return null;
  return html`<a class=${className} href=${href} target="_blank" rel="noopener noreferrer">
    ${t('detail.openOn', { site })} ${Icon.External()}</a>`;
}

export function PostingDescription({ text, url, site, capturedAt, children = null }) {
  const { t, fmt } = useUi();
  const [open, setOpen] = useState(false);
  const [overflows, setOverflows] = useState(false);
  const body = useRef(null);
  const toggle = useRef(null);

  useLayoutEffect(() => {
    const element = body.current;
    if (!element) return undefined;
    const measure = () => {
      if (!element.classList.contains('clamped')) return;
      setOverflows(element.scrollHeight > element.clientHeight + 1);
    };
    measure();
    const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(measure) : null;
    if (observer) observer.observe(element);
    return () => observer && observer.disconnect();
  }, [text]);

  const close = () => {
    setOpen(false);
    if (toggle.current) {
      toggle.current.focus();
      toggle.current.scrollIntoView({ block: 'nearest' });
    }
  };
  return html`
    <div class="panel posting-description">
      <div class="panel-head">
        <h2>${t('detail.description')}</h2>
        ${capturedAt && html`<span class="small">${t('detail.captured', { date: fmt.shortDateTime(capturedAt) })}</span>`}
      </div>
      ${text ? html`
        <div ref=${body} class=${'description' + (open ? '' : ' clamped') + (overflows && !open ? ' faded' : '')}>${text}</div>
        ${(overflows || open) && html`
          <button type="button" ref=${toggle} class="link-btn read-more" aria-expanded=${String(open)}
            onClick=${() => (open ? close() : setOpen(true))}>
            ${open ? t('detail.readLess') : t('detail.readMore')}</button>`}`
        : html`<p class="muted">${t('detail.noDescription')}</p>`}
      <div class="panel-foot">
        <${PostingLink} url=${url} site=${site} className="" />
        ${children}
      </div>
    </div>`;
}
