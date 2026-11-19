// Dates, numbers, and money with the browser's Intl in the panel language.
import { intlLocale } from './i18n.js';

export function makeFormat(lang) {
  const locale = intlLocale(lang);
  const dayMs = 24 * 60 * 60 * 1000;

  const parseDay = (iso) => {
    const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
    return new Date(y, m - 1, d);
  };

  return {
    locale,
    /** "Sun, 15 Nov 2026 · 09:12" from an ISO timestamp (UTC in the database). */
    dateTime(iso) {
      if (!iso) return '';
      const date = new Date(iso);
      const day = new Intl.DateTimeFormat(locale, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }).format(date);
      const time = new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' }).format(date);
      return `${day} · ${time}`;
    },
    /** "15 Nov, 09:12" */
    shortDateTime(iso) {
      if (!iso) return '';
      return new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(iso));
    },
    /** "14 Nov" for the local day of a timestamp. */
    localDayMonth(iso) {
      if (!iso) return '';
      return new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short' }).format(new Date(iso));
    },
    /** "09:12" in local time. */
    time(iso) {
      if (!iso) return '';
      return new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' }).format(new Date(iso));
    },
    /** "14 Nov" from a calendar date. */
    dayMonth(isoDate) {
      if (!isoDate) return '';
      return new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short' }).format(parseDay(isoDate));
    },
    /** "1 Sep 2026" from a calendar date or timestamp. */
    longDate(iso) {
      if (!iso) return '';
      return new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short', year: 'numeric' }).format(parseDay(iso));
    },
    /** "Oct 2026" */
    monthYear(isoDate) {
      if (!isoDate) return '';
      return new Intl.DateTimeFormat(locale, { month: 'short', year: 'numeric' }).format(parseDay(isoDate));
    },
    /** "1 day ago" from a calendar date, relative to today. */
    ago(isoDate) {
      if (!isoDate) return '';
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const days = Math.round((parseDay(isoDate) - today) / dayMs);
      return new Intl.RelativeTimeFormat(locale, { numeric: 'auto', style: 'short' }).format(days, 'day');
    },
    money(amount, currency) {
      if (amount === null || amount === undefined) return '';
      try {
        return new Intl.NumberFormat(locale, { style: 'currency', currency, currencyDisplay: 'narrowSymbol', maximumFractionDigits: 0 }).format(amount);
      } catch (error) {
        return `${currency} ${this.number(amount)}`;
      }
    },
    number(value) {
      return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value);
    },
    country(code) {
      if (!code) return '';
      try { return new Intl.DisplayNames([locale], { type: 'region' }).of(code) || code; } catch (error) { return code; }
    },
    list(items) {
      try { return new Intl.ListFormat(locale, { style: 'short', type: 'conjunction' }).format(items); } catch (error) { return items.join(', '); }
    },
  };
}
