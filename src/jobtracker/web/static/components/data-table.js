// A reusable table: sortable columns, row selection, and expandable detail rows.
//
// columns: [{key, label, sortable, width, render(row), className}]
// sort: {key, dir: 'asc'|'desc'}; onSort(key)
// selected: Set of row keys; onSelect(key, checked); onSelectAll(checked)
// expanded: Set of row keys; onExpand(key)
// renderDetail(row): content of the expanded row
import { html } from '../vendor/preact-htm.js';
import { useUi } from './shell.js';
import * as Icon from './icons.js';

export function DataTable({
  columns, rows, rowKey, rowLabel, sort, onSort, selected, onSelect, onSelectAll,
  expanded, onExpand, renderDetail, rowClass, caption,
}) {
  const { t } = useUi();
  const selectable = Boolean(onSelect);
  const expandable = Boolean(renderDetail);
  const selectableRows = rows.filter((row) => !row.__noSelect);
  const allSelected = selectable && selectableRows.length > 0
    && selectableRows.every((row) => selected.has(rowKey(row)));
  const span = columns.length + (selectable ? 1 : 0) + (expandable ? 1 : 0);

  const header = (column) => {
    if (!column.sortable) return html`<th scope="col" style=${column.width ? { width: column.width } : null}>${column.label}</th>`;
    const active = sort && sort.key === column.key;
    const ariaSort = active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none';
    return html`
      <th scope="col" aria-sort=${ariaSort} style=${column.width ? { width: column.width } : null}>
        <button type="button" class="th-sort" onClick=${() => onSort(column.key)}>
          ${column.label}<span aria-hidden="true">${active ? (sort.dir === 'asc' ? '↑' : '↓') : ''}</span>
        </button>
      </th>`;
  };

  return html`
    <table class="table">
      ${caption && html`<caption class="sr-only">${caption}</caption>`}
      <thead>
        <tr>
          ${expandable && html`<th scope="col" style=${{ width: '44px' }}><span class="sr-only">${t('column.expand')}</span></th>`}
          ${selectable && html`
            <th scope="col" class="select-cell">
              <input type="checkbox" aria-label=${t('table.selectAll')} checked=${allSelected}
                disabled=${selectableRows.length === 0}
                onChange=${(e) => onSelectAll(e.currentTarget.checked)} />
            </th>`}
          ${columns.map(header)}
        </tr>
      </thead>
      <tbody>
        ${rows.map((row) => {
          const key = rowKey(row);
          const open = expandable && expanded.has(key);
          const label = rowLabel(row);
          const detailId = `detail-${key}`;
          return [html`
              <tr key=${key} class=${[open ? 'open' : '', rowClass ? rowClass(row) : ''].join(' ').trim()}>
                ${expandable && html`
                  <td>
                    <button type="button" class="expand-btn" aria-expanded=${String(open)}
                      aria-controls=${open ? detailId : undefined}
                      aria-label=${open ? t('table.collapse', { title: label }) : t('table.expand', { title: label })}
                      onClick=${() => onExpand(key)}>
                      ${open ? Icon.ChevronUp() : Icon.ChevronDown()}
                    </button>
                  </td>`}
                ${selectable && html`
                  <td class="select-cell">
                    ${!row.__noSelect && html`<input type="checkbox" checked=${selected.has(key)}
                      aria-label=${t('table.selectRow', { title: label })}
                      onChange=${(e) => onSelect(key, e.currentTarget.checked)} />`}
                  </td>`}
                ${columns.map((column) => html`<td class=${column.className || ''}>${column.render(row)}</td>`)}
              </tr>`,
            open && html`
                <tr key=${key + '-detail'} class="open"><td class="detail-cell" colspan=${span} id=${detailId}>${renderDetail(row)}</td></tr>`];
        })}
      </tbody>
    </table>`;
}
