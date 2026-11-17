// Inline SVG icons from the design. All are decorative (aria-hidden); the
// control around them carries the accessible name.
import { html } from '../vendor/preact-htm.js';

const svg = (size, children, extra = {}) => html`
  <svg class="icon" width=${size} height=${size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width=${extra.width || 2} stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${children}</svg>`;

export const Radar = () => html`
  <svg class="icon" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#8EA2FF"
    stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
    <circle cx="12" cy="12" r="9"></circle><circle cx="12" cy="12" r="4.5"></circle><path d="M12 12l6.2-6.2"></path>
  </svg>`;
export const Reload = () => svg(14, html`<path d="M20 11a8 8 0 1 0-2.3 5.7"></path><path d="M20 4v7h-7"></path>`);
export const Copy = () => svg(16, html`<rect x="9" y="9" width="11" height="11" rx="2"></rect><path d="M5 15V5a1 1 0 0 1 1-1h10"></path>`);
export const Check = (size = 14) => svg(size, html`<path d="M5 12l5 5 9-10"></path>`, { width: 2.4 });
export const Search = () => svg(16, html`<circle cx="11" cy="11" r="7"></circle><path d="M20 20l-3.5-3.5"></path>`);
export const ChevronDown = () => svg(18, html`<path d="M6 9l6 6 6-6"></path>`);
export const ChevronUp = () => svg(18, html`<path d="M6 15l6-6 6 6"></path>`);
export const External = () => svg(14, html`<path d="M14 4h6v6"></path><path d="M10 14L20 4"></path><path d="M19 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h6"></path>`);
export const Close = () => svg(16, html`<path d="M6 6l12 12M18 6L6 18"></path>`);
export const Alert = () => svg(14, html`<circle cx="12" cy="12" r="9"></circle><path d="M12 7v6M12 16.5h.01"></path>`);
export const Duplicate = () => svg(13, html`<rect x="8" y="8" width="12" height="12" rx="2"></rect><path d="M4 16V6a2 2 0 0 1 2-2h10"></path>`);
