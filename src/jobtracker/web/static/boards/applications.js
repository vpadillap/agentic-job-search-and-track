// Board 2: every tracked application, its status, documents, and what to do next.
import { html, useState, useEffect, useMemo, useRef } from '../vendor/preact-htm.js';
import { useUi, CommandChip, EmptyState, Menu } from '../components/shell.js';
import { DataTable } from '../components/data-table.js';
import * as Icon from '../components/icons.js';
import { api } from '../api.js';
import { WorkModeEditor, workModeText } from '../components/work-mode.js';
import { PostingDescription, PostingLink } from '../components/posting-description.js';
import { ChanceCell, EstimatePanel } from '../components/estimate.js';

const DOC_FILTERS = ['missingResume', 'proposedResume', 'sentResume', 'coverLetter', 'formUnanswered'];
const DATE_FILTERS = ['any', '7', '30', '90', 'none'];
const SORTS = ['next', 'applied', 'score', 'chance', 'status', 'company'];
const ATTENTION = ['missing_resume', 'unanswered_form', 'no_response', 'follow_up_due'];
const CHANNELS = ['Company site', 'Referral', 'Email', 'LinkedIn', 'Indeed', 'Bumeran', 'Computrabajo'];

const fold = (text) => (text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const tone = (score) => (score >= 80 ? 'high' : score >= 65 ? 'mid' : '');
const providerName = (id) => (id ? id.charAt(0).toUpperCase() + id.slice(1) : '');

function commandFor(commands, id) {
  const found = (commands || []).find((c) => c.id === id);
  return found ? found.example : `/${id}`;
}

/** Not applied yet (no applied date) and not ended: documents are still to prepare. */
const preparing = (app) => !app.applied_on && !app.ended;

function docState(app) {
  const docs = app.documents;
  return {
    missingResume: preparing(app) && !docs.resume_proposed && !docs.resume_sent,
    proposedResume: Boolean(docs.resume_proposed),
    sentResume: Boolean(docs.resume_sent),
    coverLetter: Boolean(docs.cover_letter),
    formUnanswered: app.form_question_count > app.form_answered_count,
  };
}

/** Lower sorts first: urgent things, then dated steps, then the rest. */
function nextKey(app) {
  const step = app.next_step;
  if (step.kind === 'ghost') return `0-${String(1000 - step.days).padStart(4, '0')}`;
  if (step.kind === 'follow_up' && step.due) return `1-${step.date}`;
  if (step.date) return `2-${step.date}`;
  if (step.kind === 'prepare_documents' || step.kind === 'apply') return '3';
  if (step.kind === 'set_date') return '4';
  return '9';
}

function sortValue(app, key, statusOrder) {
  switch (key) {
    case 'next': return nextKey(app);
    case 'applied': return app.applied_on || '';
    case 'score': return app.score ? app.score.total : -1;
    case 'chance': return app.estimate ? app.estimate.probability : -1;
    case 'status': return statusOrder.has(app.status.id) ? statusOrder.get(app.status.id) : statusOrder.size;
    case 'company': return fold(app.posting.company);
    default: return 0;
  }
}

// ── small pieces ──────────────────────────────────────────────────────────

function StatusTagMenu({ app, statuses, onStatus, onTags }) {
  const { t } = useUi();
  const [name, setName] = useState('');
  const [ends, setEnds] = useState(false);
  const [tag, setTag] = useState('');
  const status = app.status;
  const chipClass = 'status-chip' + (status.builtin ? '' : ' custom') + (status.ends ? ' ended' : '') + ' status-button';
  return html`
    <div class="tags">
      <${Menu} buttonClass=${chipClass} menuLabel=${t('row.changeStatus', { name: status.name })}
        label=${html`${status.name}<svg class="icon chevron" width="12" height="12" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"
          aria-hidden="true"><path d="M6 9l6 6 6-6"></path></svg>`}>
        ${(close) => html`
          <fieldset>
            <legend>${t('status.legend')}</legend>
            ${statuses.map((s) => html`
              <label>
                <input type="radio" name=${'status-' + app.job_id} checked=${s.id === status.id}
                  onChange=${() => { onStatus([app.job_id], s.id, null, s.name); close(); }} />
                ${s.name}
              </label>`)}
          </fieldset>
          <form class="menu-form" onSubmit=${(e) => {
            e.preventDefault();
            if (!name.trim()) return;
            onStatus([app.job_id], name.trim(), ends, name.trim(), true);
            setName('');
            setEnds(false);
            close();
          }}>
            <label class="sr-only" for=${'new-status-' + app.job_id}>${t('status.newLabel')}</label>
            <input id=${'new-status-' + app.job_id} type="text" maxlength="40" value=${name}
              placeholder=${t('status.newLabel') + ' · ' + t('status.newPlaceholder')}
              onInput=${(e) => setName(e.currentTarget.value)} />
            <label class="menu-check">
              <input type="checkbox" checked=${ends} onChange=${(e) => setEnds(e.currentTarget.checked)} />
              ${t('status.endsLabel')}</label>
            <button type="submit" class="btn btn-sm btn-dark" disabled=${!name.trim()}>${t('status.create')}</button>
          </form>`}
      </${Menu}>
      ${app.tags.map((item) => html`<span class="tag-chip">${item}
        ${onTags && html`<button type="button" class="tag-remove" aria-label=${t('tags.remove', { tag: item })}
          onClick=${() => onTags(app, [], [item])}>×</button>`}</span>`)}
      ${onTags && html`<${Menu} label=${html`<svg class="icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"></path></svg>`}
        buttonClass="add-chip" menuLabel=${t('row.addTag')}>
        ${() => html`
          <form class="menu-form" onSubmit=${(e) => {
            e.preventDefault();
            if (!tag.trim()) return;
            onTags(app, [tag.trim()], []);
            setTag('');
          }}>
            <label class="sr-only" for=${'new-tag-' + app.job_id}>${t('tags.add')}</label>
            <input id=${'new-tag-' + app.job_id} type="text" maxlength="40" value=${tag}
              placeholder=${t('tags.add') + ' · ' + t('tags.placeholder')}
              onInput=${(e) => setTag(e.currentTarget.value)} />
            <button type="submit" class="btn btn-sm" disabled=${!tag.trim()}>${t('tags.add')}</button>
          </form>`}
      </${Menu}>`}
    </div>`;
}

function DocLines({ app }) {
  const { t } = useUi();
  const docs = app.documents;
  const lines = [];
  if (docs.resume_sent) lines.push(['ok', t('doc.resumeSent')]);
  else if (docs.resume_proposed) lines.push(['ok', t('doc.resumeReady')]);
  else if (preparing(app)) lines.push(['missing', t('doc.resumeMissing')]);
  else lines.push(['na', t('doc.resumeBase')]);
  const letter = app.cover_letter || {};
  if (docs.cover_letter) lines.push(['ok', t('doc.letterReady')]);
  else if (letter.need === 'not_required') lines.push(['na', t('doc.letterNotRequired')]);
  else if (letter.need === 'required') lines.push(['missing', t('doc.letterMissing')]);
  else if (preparing(app)) lines.push(['queued', t('doc.letterUndecided')]);
  else lines.push(['na', t('doc.letterNone')]);
  if (app.form_question_count === 0) lines.push(['na', t('doc.noForm')]);
  else {
    const total = app.form_question_count;
    const done = app.form_answered_count >= total;
    const needsYou = (app.form_proposed_count || 0) - app.form_answered_count;
    lines.push([done ? 'ok' : needsYou > 0 && app.form_proposed_count >= total ? 'queued' : 'missing',
      needsYou > 0 ? t('doc.formNeedsYou', { answered: app.form_answered_count, total, count: needsYou })
        : t('doc.form', { answered: app.form_answered_count, total })]);
  }
  return html`<div class="doc-lines">${lines.map(([state, label]) => html`
    <span class=${'doc-line ' + state}><span class="doc-dot" aria-hidden="true"></span>${label}</span>`)}</div>`;
}

function AskedSuggested({ app }) {
  const { t, fmt } = useUi();
  const snap = app.at_application && app.at_application.suggested_salary;
  const offered = app.offered_salary;
  const current = app.salary && app.salary.status === 'suggested' ? app.salary : null;
  const suggested = snap || current;
  const asked = app.asked_salary;
  let diff = null;
  if (asked && suggested && asked.currency === suggested.currency && suggested.amount) {
    const pct = Math.round(((asked.amount - suggested.amount) / suggested.amount) * 100);
    diff = `${pct > 0 ? '+' : ''}${pct}%`;
  }
  return html`<div class="stack">
    <span class="mono" style=${{ fontWeight: 600 }}>${asked ? fmt.money(asked.amount, asked.currency) : t('row.notApplied')}</span>
    <span class="small mono">${suggested ? t('row.suggested', { amount: fmt.money(suggested.amount, suggested.currency) }) : t('row.suggestedNone')}</span>
    ${diff && html`<span class="small">${t('row.diff', { diff })}</span>`}
    ${offered && html`<span class="small mono offered">${t('row.offered', { amount: fmt.money(offered.amount, offered.currency) })}</span>`}
  </div>`;
}

function NextStep({ app, onStatus, thresholds }) {
  const { t, fmt } = useUi();
  const step = app.next_step;
  const tone = { ghost: 'warn', follow_up: step.due ? 'warn' : '', user: '' }[step.kind] || '';
  let main = t('next.' + step.kind);
  let sub = '';
  if (step.kind === 'prepare_documents') sub = t('next.prepare_documentsSub');
  if (step.kind === 'apply') sub = t('next.applySub');
  if (step.kind === 'follow_up') {
    main = step.due ? t('next.follow_upDue') : t('next.follow_up');
    sub = step.due ? t('next.follow_upDueSub', { date: fmt.dayMonth(step.date) })
      : t('next.follow_upSub', { date: fmt.dayMonth(step.date), days: thresholds.follow_up_after_days });
  }
  if (step.kind === 'ghost') main = t('next.ghost', { days: step.days });
  if (step.kind === 'set_date') sub = t('next.set_dateSub');
  if (step.kind === 'user') {
    main = step.note || t('next.userNoNote');
    sub = step.date ? fmt.dayMonth(step.date) : '';
  }
  return html`<div class="stack">
    <span class=${'next-main ' + tone}>${main}</span>
    ${sub && html`<span class="small">${sub}</span>`}
    ${step.kind === 'ghost' && html`<button type="button" class="link-btn small-btn"
      onClick=${() => onStatus([app.job_id], 'ghosted', null, t('next.ghostConfirm'))}>${t('next.ghostConfirm')}</button>`}
  </div>`;
}

// ── detail ────────────────────────────────────────────────────────────────

function CopyTextButton({ job, document }) {
  const { t } = useUi();
  const [done, setDone] = useState(false);
  const copy = async () => {
    const { text } = await api.documentText(job, document.id);
    await navigator.clipboard.writeText(text);
    setDone(true);
    setTimeout(() => setDone(false), 2000);
  };
  return html`<button type="button" class="link-btn" onClick=${copy}>${done ? t('detail.copiedText') : t('detail.copyText')}</button>
    <span class="sr-only" role="status">${done ? t('detail.copiedText') : ''}</span>`;
}

function DiffView({ job, document }) {
  const { t } = useUi();
  const [diff, setDiff] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    let live = true;
    api.documentDiff(job, document.id).then((r) => live && setDiff(r))
      .catch((e) => live && setError(e.message));
    return () => { live = false; };
  }, [job, document.id]);
  if (error) return html`<p class="note">${error}</p>`;
  if (!diff) return html`<p class="note">${t('diff.loading')}</p>`;
  return html`
    <div class="diff" role="region" aria-label=${t('diff.title')}>
      <p class="small">${t('diff.stats', { added: diff.stats.added, removed: diff.stats.removed })}</p>
      ${diff.hunks.length === 0 ? html`<p class="note">${t('diff.none')}</p>` : diff.hunks.map((hunk) => html`
        <div class="diff-hunk">
          ${hunk.base.map((line) => html`<p class="diff-line removed"><span class="sr-only">${t('diff.removed')}: </span>${line}</p>`)}
          ${hunk.proposed.map((line) => html`<p class="diff-line added"><span class="sr-only">${t('diff.added')}: </span>${line}</p>`)}
        </div>`)}
    </div>`;
}

function ProposedResume({ app, doc }) {
  const { t, fmt } = useUi();
  const [compare, setCompare] = useState(false);
  return html`
    <span class="mono">${doc.file_name}</span>
    <span class="small">${t('detail.agentOn', { date: fmt.dayMonth(doc.created_at) })}
      ${doc.language ? ' · ' + t('detail.language', { language: doc.language.toUpperCase() }) : ''}</span>
    ${doc.base_resume && html`<span class="small">${doc.base_resume.language
      ? t('detail.fromBase', { language: doc.base_resume.language.toUpperCase(), version: doc.base_resume.version })
      : t('detail.fromBaseUnknown', { version: doc.base_resume.version })}</span>`}
    ${doc.summary && html`<p class="doc-summary">${doc.summary}</p>`}
    ${doc.level && doc.level !== 'light' && html`<span class="small">${t('detail.level.' + doc.level)}</span>`}
    ${doc.gaps && doc.gaps.length > 0 && html`
      <div class="doc-gaps"><span class="doc-kind">${t('detail.gaps')}</span>
        <ul>${doc.gaps.map((gap) => html`<li>${gap}</li>`)}</ul></div>`}
    ${doc.support && doc.support.length > 0 && html`
      <details class="doc-support"><summary>${t('detail.support', { count: doc.support.length })}</summary>
        <ul>${doc.support.map((s) => html`<li><strong>${s.term}</strong>: ${s.source}</li>`)}</ul></details>`}
    <div class="filter-group">
      <a href=${api.documentUrl(app.job_id, doc.id)} download>${t('detail.openDoc')}</a>
      <button type="button" class="link-btn" aria-expanded=${String(compare)}
        onClick=${() => setCompare(!compare)}>${compare ? t('diff.hide') : t('diff.show')}</button>
    </div>
    ${compare && html`<${DiffView} job=${app.job_id} document=${doc} />`}`;
}

function DocumentsCard({ app, onUpload }) {
  const { t, fmt } = useUi();
  const input = useRef(null);
  const { resume_proposed: proposed, resume_sent: sent, cover_letter: letter } = app.documents;
  const open = (doc) => html`<a href=${api.documentUrl(app.job_id, doc.id)} download>${t('detail.openDoc')}</a>`;
  const need = app.cover_letter || {};
  return html`
    <div class="panel">
      <h2>${t('detail.documents')}</h2>
      <div class="doc-card">
        <span class="doc-kind">${t('detail.proposed')}</span>
        ${proposed ? html`<${ProposedResume} app=${app} doc=${proposed} />`
          : html`<span class="note">${t('detail.noProposed')}</span>`}
      </div>
      <div class=${'doc-card' + (sent ? ' sent' : '')}>
        <span class="doc-kind">${t('detail.sent')}</span>
        ${sent ? html`<span class="mono">${sent.file_name}</span>
          <span class="small">${t('detail.uploadedOn', { date: fmt.dayMonth(sent.created_at), name: sent.original_name })}</span>`
          : html`<span class="note">${t('detail.noSent')}</span>`}
        <div class="filter-group">
          ${sent && open(sent)}
          <input type="file" class="sr-only" ref=${input} id=${'upload-' + app.job_id}
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange=${(e) => { const file = e.currentTarget.files[0]; e.currentTarget.value = ''; if (file) onUpload(app, file); }} />
          <button type="button" class="btn btn-sm" onClick=${() => input.current.click()}>
            ${sent ? t('detail.replace') : t('detail.upload')}</button>
          <span class="small">${t('detail.uploadHint')}</span>
        </div>
      </div>
      <div class="doc-card">
        <span class="doc-kind">${t('detail.letter')}</span>
        ${letter ? html`<span class="mono">${letter.file_name}</span>
          <div class="filter-group">${open(letter)}<${CopyTextButton} job=${app.job_id} document=${letter} /></div>`
          : need.need === 'not_required'
            ? html`<span class="note">${t('detail.letterNotRequired')}${need.reason ? ' ' + need.reason : ''}</span>`
            : need.need === 'required'
              ? html`<span class="note">${t('detail.letterRequired')}</span>`
              : html`<span class="note">${t('detail.noLetter')}</span>`}
      </div>
    </div>`;
}

function CopyAnswer({ text }) {
  const { t } = useUi();
  const [done, setDone] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(text);
    setDone(true);
    setTimeout(() => setDone(false), 2000);
  };
  return html`<button type="button" class="icon-btn" onClick=${copy}
    aria-label=${done ? t('detail.copiedText') : t('answers.copy')} title=${t('answers.copy')}>
    ${done ? Icon.Check(14) : Icon.Copy(14)}</button>`;
}

function AnswerBlock({ job, question, onSaved }) {
  const { t } = useUi();
  const answer = question.answer;
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState('');
  const [state, setState] = useState(null);
  const startEdit = () => { setText(answer ? answer.text : ''); setEditing(true); };
  const save = async () => {
    setState({ kind: 'saving' });
    try {
      await api.editAnswer(job, question.position, text);
      setEditing(false);
      setState(null);
      onSaved();
    } catch (error) {
      setState({ kind: 'error', message: error.message });
    }
  };
  const pick = async (id) => {
    try { await api.pickAnswer(job, id); onSaved(); } catch (error) { setState({ kind: 'error', message: error.message }); }
  };
  const label = !answer ? null
    : answer.needs_user ? ['warn', t('answers.needsYou')]
    : answer.origin === 'user' ? ['user', t('answers.edited')] : ['agent', t('answers.agent')];
  return html`
    <div class="qa">
      <div class="qa-head">
        <span class="qa-q">${question.text}${question.required ? html` <span class="small">(${t('detail.required')})</span>` : ''}</span>
        ${answer && answer.text && !editing && html`<${CopyAnswer} text=${answer.text} />`}
      </div>
      ${editing ? html`
        <label class="sr-only" for=${'answer-' + job + '-' + question.position}>${t('answers.yourAnswer')}</label>
        <textarea id=${'answer-' + job + '-' + question.position} rows="3" value=${text}
          onInput=${(e) => setText(e.currentTarget.value)}></textarea>
        <div class="filter-group">
          <button type="button" class="btn btn-sm btn-dark" onClick=${save}>${t('answers.save')}</button>
          <button type="button" class="btn btn-sm" onClick=${() => setEditing(false)}>${t('answers.cancel')}</button>
        </div>`
      : answer ? html`
        ${answer.text && html`<p class="qa-a">${answer.text}</p>`}
        ${answer.needs_user && answer.note && html`<p class="note">${answer.note}</p>`}`
      : html`<span class="note">${t('detail.noAnswer')}</span>`}
      <div class="qa-meta">
        ${label && html`<span class=${'answer-tag ' + label[0]}>${label[1]}</span>`}
        ${answer && answer.basis && html`<span class="answer-tag basis">${answer.basis}</span>`}
        ${!editing && html`<button type="button" class="link-btn small-btn" onClick=${startEdit}>
          ${answer && answer.text ? t('answers.edit') : t('answers.write')}</button>`}
      </div>
      ${state && state.kind === 'error' && html`<span class="field-state error" role="status">${t('field.error', { message: state.message })}</span>`}
      ${question.alternatives.length > 0 && html`
        <details class="alternatives"><summary>${t('answers.alternatives', { count: question.alternatives.length })}</summary>
          ${question.alternatives.map((alt) => html`
            <div class="alternative">
              <p class="qa-a">${alt.text || alt.note}</p>
              <button type="button" class="btn btn-sm" onClick=${() => pick(alt.id)}>${t('answers.use')}</button>
            </div>`)}
        </details>`}
    </div>`;
}

function FormCard({ app, detail, onSaved }) {
  const { t } = useUi();
  const questions = detail ? detail.form_questions : [];
  if (detail && questions.length === 0) {
    return html`<div class="panel"><h2>${t('detail.form', { count: 0 })}</h2>
      <p class="note">${t('detail.noForm')}</p></div>`;
  }
  return html`
    <div class="panel">
      <h2>${t('detail.form', { count: questions.length })}</h2>
      ${questions.map((q) => html`<${AnswerBlock} key=${q.position} job=${app.job_id} question=${q} onSaved=${onSaved} />`)}
    </div>`;
}

function Field({ label, children, state }) {
  const { t } = useUi();
  return html`<label class="field">${label}${children}
    ${state && html`<span class=${'field-state ' + state.kind} role="status">
      ${state.kind === 'saving' ? t('field.saving') : state.kind === 'saved' ? t('field.saved')
        : t('field.error', { message: state.message })}</span>`}</label>`;
}

function historyText(item, t, fmt, statusName) {
  const d = item.data || {};
  switch (item.kind) {
    case 'found': return t('history.found', { provider: providerName(d.provider) });
    case 'tracked': return t('history.tracked', { job: d.job_id });
    case 'created': return t('history.created');
    case 'scored': return t('history.scored', { total: d.total });
    case 'salary': return t('history.salary', { value: d.status === 'suggested' ? fmt.number(d.amount) : t('history.salaryNone') });
    case 'status_changed': return t('history.status_changed', { to: d.to_name || statusName(d.to) });
    case 'field_changed': return t('history.field_changed', { field: t('field.' + ({ asked_salary: 'asked', offered_salary: 'offered' }[d.field] || d.field)) });
    case 'applied': return t('history.applied', { date: d.on ? fmt.dayMonth(d.on) : '' });
    case 'tag_added': return t('history.tag_added', { tag: d.tag });
    case 'tag_removed': return t('history.tag_removed', { tag: d.tag });
    case 'document_registered': return t('history.document_registered', { kind: t('kind.' + d.kind), version: d.version, origin: t('origin.' + d.origin) });
    case 'reposted': return t('history.reposted', { provider: providerName(d.provider) });
    case 'answers_proposed': return t('history.answers_proposed', { count: (d.current || []).length + (d.alternatives || []).length });
    case 'answer_edited': return t('history.answer_edited', { position: d.position });
    case 'answer_picked': return t('history.answer_picked', { position: d.position });
    case 'cover_letter_need': return t('history.cover_letter_need.' + d.need);
    case 'work_mode': return t('history.work_mode', {
      value: workModeText(t, { work_mode: d.to.mode, work_mode_detail: d.to.detail }) || t('workMode.notStated') });
    default: return item.kind;
  }
}

function YourApplication({ app, detail, onSaved, statusName }) {
  const locked = app.earlier_season;   // an earlier season: only the offered salary changes
  const { t, fmt } = useUi();
  const initial = () => ({
    applied_on: app.applied_on || '', asked: app.asked_salary ? String(app.asked_salary.amount) : '',
    currency: (app.asked_salary && app.asked_salary.currency) || (app.salary && app.salary.currency) || 'PEN',
    offered: app.offered_salary ? String(app.offered_salary.amount) : '',
    offeredCurrency: (app.offered_salary && app.offered_salary.currency)
      || (app.asked_salary && app.asked_salary.currency) || (app.salary && app.salary.currency) || 'PEN',
    channel: app.channel || '', contact: app.contact || '', notes: app.notes || '',
    next_step_on: app.next_step_on || '', next_step_note: app.next_step_note || '',
  });
  const [values, setValues] = useState(initial);
  const [states, setStates] = useState({});
  useEffect(() => { if (!document.activeElement || !document.activeElement.closest('.app-form')) setValues(initial()); }, [app]);

  const save = async (field, payload) => {
    setStates((s) => ({ ...s, [field]: { kind: 'saving' } }));
    try {
      await api.setDetails(app.job_id, payload);
      setStates((s) => ({ ...s, [field]: { kind: 'saved' } }));
      setTimeout(() => setStates((s) => ({ ...s, [field]: null })), 2000);
      onSaved();
    } catch (error) {
      setStates((s) => ({ ...s, [field]: { kind: 'error', message: error.message } }));
    }
  };
  const bind = (field, transform) => ({
    value: values[field],
    disabled: locked,
    onInput: (e) => setValues({ ...values, [field]: e.currentTarget.value }),
    onChange: () => save(field, { [field]: transform ? transform(values[field]) : (values[field] || null) }),
  });
  const saveSalary = (field, detail, currencyField) => {
    const amount = parseInt(values[field].replace(/[^\d]/g, ''), 10);
    save(field, { [detail]: Number.isFinite(amount) && amount > 0
      ? { amount, currency: values[currencyField].toUpperCase(), basis: 'gross' } : null });
  };
  const saveAsked = () => saveSalary('asked', 'asked_salary', 'currency');
  const saveOffered = () => saveSalary('offered', 'offered_salary', 'offeredCurrency');
  return html`
    <div class="panel app-form">
      <h2>${t('detail.yours')}</h2>
      <div class="form-grid">
        <${Field} label=${t('field.applied_on')} state=${states.applied_on}>
          <input type="date" ...${bind('applied_on')} /></${Field}>
        <${Field} label=${t('field.asked')} state=${states.asked}>
          <span class="money-input">
            <input type="text" inputmode="numeric" class="mono" value=${values.asked} disabled=${locked}
              onInput=${(e) => setValues({ ...values, asked: e.currentTarget.value })} onChange=${saveAsked} />
            <input type="text" maxlength="3" class="mono currency" aria-label=${t('field.currency')} value=${values.currency}
              disabled=${locked}
              onInput=${(e) => setValues({ ...values, currency: e.currentTarget.value.toUpperCase() })} onChange=${saveAsked} />
          </span></${Field}>
        <${Field} label=${t('field.offered')} state=${states.offered}>
          <span class="money-input">
            <input type="text" inputmode="numeric" class="mono" value=${values.offered}
              onInput=${(e) => setValues({ ...values, offered: e.currentTarget.value })} onChange=${saveOffered} />
            <input type="text" maxlength="3" class="mono currency" aria-label=${t('field.offeredCurrency')} value=${values.offeredCurrency}
              onInput=${(e) => setValues({ ...values, offeredCurrency: e.currentTarget.value.toUpperCase() })} onChange=${saveOffered} />
          </span></${Field}>
        <${Field} label=${t('field.channel')} state=${states.channel}>
          <input type="text" list="channels" ...${bind('channel')} /></${Field}>
        <${Field} label=${t('field.contact')} state=${states.contact}>
          <input type="text" placeholder=${t('field.contactPlaceholder')} ...${bind('contact')} /></${Field}>
        <${Field} label=${t('field.next_step_on')} state=${states.next_step_on}>
          <input type="date" ...${bind('next_step_on')} /></${Field}>
        <${Field} label=${t('field.next_step_note')} state=${states.next_step_note}>
          <input type="text" ...${bind('next_step_note')} /></${Field}>
      </div>
      <${Field} label=${t('field.notes')} state=${states.notes}>
        <textarea rows="3" ...${bind('notes')}></textarea></${Field}>
      <datalist id="channels">${CHANNELS.map((c) => html`<option value=${c}></option>`)}</datalist>
      <div class="history">
        <span class="doc-kind">${t('detail.history')}</span>
        ${detail ? detail.history.map((item) => html`
          <div class="history-row"><span class="mono muted">${fmt.dayMonth(item.at)}</span>
            <span>${historyText(item, t, fmt, statusName)}</span></div>`) : ''}
      </div>
    </div>`;
}

function ApplicationDetail({ app, version, onUpload, onSaved, statusName }) {
  const { t } = useUi();
  const [detail, setDetail] = useState(null);
  useEffect(() => {
    let live = true;
    api.application(app.job_id).then((r) => { if (live) setDetail(r.application); }).catch(() => {});
    return () => { live = false; };
  }, [app.job_id, version]);
  return html`
    <div class="detail app-detail">
      <${PostingDescription} text=${detail ? detail.description : null} url=${app.posting.url}
        site=${providerName(app.posting.provider)} capturedAt=${app.posting.captured_at} />
      ${app.earlier_season && html`<p class="note season-readonly">${t('season.readOnly', { number: app.season })}</p>`}
      <div class="detail-grid apps">
        <fieldset class="season-lock" disabled=${app.earlier_season}>
          <${DocumentsCard} app=${app} onUpload=${onUpload} /></fieldset>
        <fieldset class="season-lock" disabled=${app.earlier_season}>
          <${FormCard} app=${app} detail=${detail} onSaved=${onSaved} /></fieldset>
        <${YourApplication} app=${app} detail=${detail} onSaved=${onSaved} statusName=${statusName} />
      </div>
      <${EstimatePanel} estimate=${app.estimate} />
    </div>`;
}

// ── board ─────────────────────────────────────────────────────────────────

export function ApplicationsBoard({ data, version, commands, onAction, onReload }) {
  const { t, fmt } = useUi();
  const [query, setQuery] = useState('');
  const [cardFilter, setCardFilter] = useState(null);
  const [statusFilter, setStatusFilter] = useState([]);
  const [docFilter, setDocFilter] = useState([]);
  const [tagFilter, setTagFilter] = useState([]);
  const [dateFilter, setDateFilter] = useState('any');
  const [attention, setAttention] = useState(null);
  const [showEnded, setShowEnded] = useState(false);
  const [sort, setSort] = useState({ key: 'next', dir: 'asc' });
  const [expanded, setExpanded] = useState(new Set());

  const items = data ? data.applications : [];
  const statuses = data ? data.statuses : [];
  const allTags = useMemo(() => [...new Set(items.flatMap((a) => a.tags))].sort(), [items]);

  const view = useMemo(() => {
    const ended = items.filter((a) => a.ended);
    // An ending status picked on its card or in the status filter lists its applications.
    const endsOf = new Map([...statuses.map((s) => [s.id, s.ends]), ...items.map((a) => [a.status.id, a.status.ends])]);
    const endedPicked = [cardFilter, ...statusFilter].some((id) => id !== null && endsOf.get(id));
    const base = showEnded || endedPicked ? items : items.filter((a) => !a.ended);
    const statusOrder = new Map(statuses.map((s, index) => [s.id, index]));
    const needle = fold(query.trim());
    const today = new Date();
    const since = (days) => { const d = new Date(today); d.setDate(d.getDate() - Number(days)); return d.toISOString().slice(0, 10); };
    const ids = attention && data ? new Set(data.attention[attention]) : null;
    const shown = base.filter((a) => {
      if (needle && !fold([a.posting.title, a.posting.company, a.notes, ...a.tags].join(' ')).includes(needle)) return false;
      if (cardFilter !== null && a.status.id !== cardFilter) return false;
      if (statusFilter.length && !statusFilter.includes(a.status.id)) return false;
      if (docFilter.length) { const state = docState(a); if (!docFilter.every((f) => state[f])) return false; }
      if (tagFilter.length && !tagFilter.every((tag) => a.tags.includes(tag))) return false;
      if (dateFilter === 'none' && a.applied_on) return false;
      if (!['any', 'none'].includes(dateFilter) && (!a.applied_on || a.applied_on < since(dateFilter))) return false;
      if (ids && !ids.has(a.job_id)) return false;
      return true;
    });
    const dir = sort.dir === 'asc' ? 1 : -1;
    shown.sort((a, b) => {
      const x = sortValue(a, sort.key, statusOrder);
      const y = sortValue(b, sort.key, statusOrder);
      return (x < y ? -1 : x > y ? 1 : 0) * dir || a.job_id.localeCompare(b.job_id);
    });
    const hiddenEnded = showEnded || endedPicked ? 0 : ended.length;
    return { shown, total: base.length, hiddenEnded, ended };
  }, [items, statuses, query, cardFilter, statusFilter, docFilter, tagFilter, dateFilter, attention, showEnded, sort, data]);

  if (!data) return html`<section class="card empty" aria-busy="true"></section>`;
  if (items.length === 0) {
    return html`<${EmptyState} title=${t('apps.empty')} body=${t('apps.emptyBody')} />`;
  }

  const statusName = (ref) => (statuses.find((s) => s.id === ref || s.key === ref) || {}).name || ref;
  const changeStatus = (jobIds, status, ends, label, created) => onAction(async () => {
    await api.setStatus(jobIds, status, ends);
    const name = created ? label : statusName(status);
    return { message: created ? t('toast.statusCreated', { name })
      : t('toast.statusChanged', { count: jobIds.length, job: jobIds[0], status: name }) };
  });
  const changeTags = (app, add, remove) => onAction(async () => { await api.setTags(app.job_id, add, remove); return null; });
  const upload = (app, file) => onAction(async () => {
    await api.uploadSentResume(app.job_id, file);
    return { message: t('toast.uploaded') };
  });

  const limits = data.thresholds;
  const endedNames = [...new Set(view.ended.map((a) => a.status.name))].join(', ');

  const columns = [
    { key: 'score', label: t('col.scoreApps'), sortable: true, width: '92px', render: (a) => {
      const chance = a.estimate && html`<${ChanceCell} estimate=${a.estimate} compact />`;
      if (!a.score) return html`<div class="stack"><span class="score none">–</span>${chance}</div>`;
      const prev = a.score.previous_total;
      const delta = prev !== null && prev !== undefined && prev !== a.score.total ? a.score.total - prev : null;
      const text = delta === null ? null : `${delta > 0 ? '+' : ''}${delta}`;
      return html`<div class="stack">
        <span class=${'score ' + tone(a.score.total)}>${a.score.total}</span>
        ${text && html`<span class=${'delta' + (delta < 0 ? ' down' : '')}>
          ${a.score.resume_kind === 'sent' ? t('row.delta', { delta: text }) : t('row.deltaOther', { delta: text })}</span>`}
        ${chance}
      </div>`;
    } },
    { key: 'company', label: t('col.job'), sortable: true, render: (a) => html`
      <div class="job">
        <span class="job-title">${a.posting.title}</span>
        <span class="job-company">${[a.posting.company,
          a.posting.contract_type && t('contract.' + a.posting.contract_type)].filter(Boolean).join(' · ')}</span>
        <${WorkModeEditor} posting=${a.posting} onAction=${onAction} />
        <${PostingLink} url=${a.posting.url} site=${providerName(a.posting.provider)} className="source small-link" />
        <span class="small mono">${a.job_id}</span>
      </div>` },
    { key: 'status', label: t('col.statusTags'), sortable: true, render: (a) => html`
      <${StatusTagMenu} app=${a} statuses=${statuses} onStatus=${changeStatus}
        onTags=${a.earlier_season ? null : changeTags} />` },
    { key: 'documents', label: t('col.documents'), width: '190px', render: (a) => html`<${DocLines} app=${a} />` },
    { key: 'applied', label: t('col.applied'), sortable: true, width: '110px', render: (a) => html`<div class="stack">
      <span>${a.applied_on ? fmt.dayMonth(a.applied_on) : t('row.notApplied')}</span>
      <span class="small">${a.channel || providerName(a.posting.provider)}</span></div>` },
    { key: 'asked', label: t('col.askedSuggested'), width: '160px', render: (a) => html`<${AskedSuggested} app=${a} />` },
    { key: 'next', label: t('col.next'), sortable: true, render: (a) => html`
      <${NextStep} app=${a} onStatus=${changeStatus} thresholds=${limits} />` },
  ];

  const attentionCount = (key) => data.attention[key].length;
  return html`
    <section class="funnel" aria-label=${t('funnel.label')}>
      ${data.funnel.map((card) => {
        const pressed = cardFilter === card.status_id;
        const label = card.ends && !showEnded && !pressed ? t('funnel.endedHidden', { name: card.name }) : card.name;
        return html`<button type="button" class=${'funnel-card' + (pressed ? ' on' : '') + (card.ends ? ' ended' : '')}
          aria-pressed=${String(pressed)}
          onClick=${() => { setAttention(null); setCardFilter(pressed ? null : card.status_id); }}>
          <span class="funnel-label">${label}</span>
          <span class="funnel-count">${card.count}</span>
        </button>`;
      })}
    </section>
    <section class="card attention" aria-label=${t('attention.title')}>
      <div class="attention-items">
        <strong>${t('attention.title')}</strong>
        ${ATTENTION.every((key) => attentionCount(key) === 0) ? html`<span class="muted">${t('attention.none')}</span>`
          : ATTENTION.filter((key) => attentionCount(key) > 0).map((key) => html`
            <button type="button" class=${'link-btn' + (attention === key ? ' active-link' : '')} aria-pressed=${String(attention === key)}
              onClick=${() => { setCardFilter(null); setAttention(attention === key ? null : key); }}>
              ${t('attention.' + key, { count: attentionCount(key), days: limits.ghost_after_days })}</button>`)}
        ${attention && html`<button type="button" class="btn btn-sm" onClick=${() => setAttention(null)}>${t('attention.clear')}</button>`}
        ${attention === 'no_response' && attentionCount('no_response') > 0 && html`
          <button type="button" class="btn btn-sm btn-dark"
            onClick=${() => changeStatus(data.attention.no_response, 'ghosted')}>
            ${t('attention.ghostAll', { count: attentionCount('no_response') })}</button>`}
      </div>
      <div class="attention-command">
        <span class="small">${t('attention.note')}</span>
        <${CommandChip} command=${commandFor(commands, 'prepare-documents')} note=${false} />
      </div>
    </section>
    <section class="filters" aria-label=${t('filters.label')}>
      <div class="filter-group">
        <label class="search-box">
          ${Icon.Search()}
          <span class="sr-only">${t('apps.searchLabel')}</span>
          <input type="search" value=${query} placeholder=${t('apps.searchPlaceholder')}
            onInput=${(e) => setQuery(e.currentTarget.value)} />
        </label>
        <${Menu} label=${t('apps.statusFilter', { value: statusFilter.length ? statusFilter.map(statusName).join(', ') : t('apps.statusAll') })}
          active=${statusFilter.length > 0}>
          <fieldset><legend>${t('status.legend')}</legend>
            ${statuses.map((s) => html`<label>
              <input type="checkbox" checked=${statusFilter.includes(s.id)}
                onChange=${(e) => setStatusFilter(e.currentTarget.checked ? [...statusFilter, s.id] : statusFilter.filter((x) => x !== s.id))} />
              ${s.name}</label>`)}
          </fieldset>
        </${Menu}>
        <${Menu} label=${t('apps.docsFilter')} active=${docFilter.length > 0}>
          <fieldset><legend>${t('apps.docsFilter')}</legend>
            ${DOC_FILTERS.map((f) => html`<label>
              <input type="checkbox" checked=${docFilter.includes(f)}
                onChange=${(e) => setDocFilter(e.currentTarget.checked ? [...docFilter, f] : docFilter.filter((x) => x !== f))} />
              ${t('docs.' + f)}</label>`)}
          </fieldset>
        </${Menu}>
        <${Menu} label=${t('apps.tagsFilter')} active=${tagFilter.length > 0}>
          <fieldset><legend>${t('apps.tagsFilter')}</legend>
            ${allTags.length === 0 ? html`<span class="small" style=${{ padding: '4px 8px' }}>${t('apps.noTags')}</span>`
              : allTags.map((tag) => html`<label>
                <input type="checkbox" checked=${tagFilter.includes(tag)}
                  onChange=${(e) => setTagFilter(e.currentTarget.checked ? [...tagFilter, tag] : tagFilter.filter((x) => x !== tag))} />
                ${tag}</label>`)}
          </fieldset>
        </${Menu}>
        <${Menu} label=${t('apps.dateFilter', { value: t(dateFilter === 'any' ? 'apps.dateAny' : dateFilter === 'none' ? 'apps.dateNone' : 'apps.date' + dateFilter) })}
          active=${dateFilter !== 'any'}>
          <fieldset><legend>${t('col.applied')}</legend>
            ${DATE_FILTERS.map((f) => html`<label>
              <input type="radio" name="applied-date" checked=${dateFilter === f} onChange=${() => setDateFilter(f)} />
              ${t(f === 'any' ? 'apps.dateAny' : f === 'none' ? 'apps.dateNone' : 'apps.date' + f)}</label>`)}
          </fieldset>
        </${Menu}>
        <${Menu} label=${t('apps.sort', { value: t(sort.dir === 'asc' ? 'sort.ascending' : 'sort.descending', { column: t('sort.' + (sort.key === 'company' ? 'company' : sort.key)) }) })}
          buttonClass="btn btn-ghost">
          <fieldset><legend>${t('apps.sort', { value: '' })}</legend>
            ${SORTS.filter((key) => key !== 'chance' || items.some((a) => a.estimate)).flatMap((key) => ['asc', 'desc'].map((dir) => html`<label>
              <input type="radio" name="apps-sort" checked=${sort.key === key && sort.dir === dir} onChange=${() => setSort({ key, dir })} />
              ${t(dir === 'asc' ? 'sort.ascending' : 'sort.descending', { column: t('sort.' + key) })}</label>`))}
          </fieldset>
        </${Menu}>
      </div>
      <label class="check-label">
        <input type="checkbox" checked=${showEnded} onChange=${(e) => setShowEnded(e.currentTarget.checked)} />
        ${t('apps.showEnded', { count: view.ended.length, statuses: endedNames || '—' })}
      </label>
    </section>
    <section class="card results" aria-label=${t('tabs.applications')}>
      ${view.shown.length === 0 ? html`<div class="empty"><p>${t('apps.noRows')}</p></div>` : html`
        <${DataTable} columns=${columns} rows=${view.shown} rowKey=${(a) => a.job_id}
          rowLabel=${(a) => `${a.posting.title} · ${a.posting.company}`} caption=${t('tabs.applications')}
          sort=${sort} onSort=${(key) => setSort(sort.key === key ? { key, dir: sort.dir === 'asc' ? 'desc' : 'asc' }
            : { key, dir: key === 'score' || key === 'applied' ? 'desc' : 'asc' })}
          expanded=${expanded}
          onExpand=${(id) => { const next = new Set(expanded); next.has(id) ? next.delete(id) : next.add(id); setExpanded(next); }}
          renderDetail=${(a) => html`<${ApplicationDetail} app=${a} version=${version} onUpload=${upload} onSaved=${onReload} statusName=${statusName} />`} />`}
    </section>
    <p class="footer" role="status">
      <span>${query.trim() ? t('apps.footerQuery', { shown: view.shown.length, total: view.total, query: query.trim() })
        : t('apps.footerAll', { shown: view.shown.length, total: view.total })}</span>
      ${view.hiddenEnded > 0 && html`<span>· ${t('apps.endedHidden', { count: view.hiddenEnded })}</span>`}
    </p>`;
}
