// A reusable table: sortable columns, row selection, and expandable detail rows.
//
// columns: [{key, label, sortable, width, render(row), className, priority}]
//   priority: 1 (default) always shown; 2 hidden below 1,100 px wide, 3 below 900 px.
//     A hidden column is listed in the row's detail instead, so nothing is lost.
//   className: also sets the column's place when rows become cards on a phone:
//     'col-main' takes the rest of the first line, 'col-full' a line of its own,
//     'col-labelled' shows the column's label above the value.
// sort: {key, dir: 'asc'|'desc'}; onSort(key)
// selected: Set of row keys; onSelect(key, checked); onSelectAll(checked)
// expanded: Set of row keys; onExpand(key)
// renderDetail(row): content of the expanded row
import { html } from '../vendor/preact-htm.js';
import { useUi } from './shell.js';
import * as Icon from './icons.js';

const priorityClass = (column) => ((column.priority || 1) > 1 ? `col-p${column.priority}` : '');
const cellClass = (column) => [priorityClass(column), column.className || ''].join(' ').trim();

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
  const secondary = columns.filter((column) => (column.priority || 1) > 1);

  const header = (column) => {
    const style = column.width ? { width: column.width } : null;
    const cls = priorityClass(column) || undefined;
    if (!column.sortable) return html`<th scope="col" class=${cls} style=${style}>${column.label}</th>`;
    const active = sort && sort.key === column.key;
    const ariaSort = active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none';
    return html`
      <th scope="col" class=${cls} aria-sort=${ariaSort} style=${style}>
        <button type="button" class="th-sort" onClick=${() => onSort(column.key)}>
          ${column.label}<span aria-hidden="true">${active ? (sort.dir === 'asc' ? '↑' : '↓') : ''}</span>
        </button>
      </th>`;
  };

  // The columns a narrow screen hides, shown at the top of the row's detail.
  const hiddenColumns = (row) => secondary.length > 0 && html`
    <dl class="hidden-cols">
      ${secondary.map((column) => html`
        <div class=${'hidden-p' + column.priority}>
          <dt>${column.label}</dt><dd>${column.render(row)}</dd>
        </div>`)}
    </dl>`;

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
                  <td class="expand-cell">
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
                ${columns.map((column) => html`<td class=${cellClass(column)} data-label=${column.label}>${column.render(row)}</td>`)}
              </tr>`,
            open && html`
                <tr key=${key + '-detail'} class="open detail-row"><td class="detail-cell" colspan=${span} id=${detailId}>
                  ${hiddenColumns(row)}${renderDetail(row)}</td></tr>`];
        })}
      </tbody>
    </table>`;
}
