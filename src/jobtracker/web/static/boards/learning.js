// Board 3 (design/panel-ux.html, "Learning"): what is working, the lessons the agent
// proposes, and the breakdowns. The learning level strip and, only at the levels that allow
// them, the prediction track record and suggestions are additions of the learning loop.
import { html, useState, useEffect } from '../vendor/preact-htm.js';
import { api } from '../api.js';
import { useUi, CommandChip, EmptyState } from '../components/shell.js';
import { ChanceCell, featureText } from '../components/estimate.js';

const PERIODS = ['30', '90', 'season', 'all'];
const LEVELS = ['collecting', 'descriptive', 'predictive', 'prescriptive'];
// The four breakdowns of the design first, then the ones the learning loop adds.
const ORDER = ['score_band', 'resume_kind', 'channel', 'salary_delta', 'language', 'work_mode'];
const SCORE_ORDER = ['85-100', '70-84', '55-69', '0-54', 'unscored'];
const pct = (value) => `${Math.round(value * 100)}%`;

function commandFor(commands, id) {
  const found = (commands || []).find((c) => c.id === id);
  return found ? (found.example || '/' + id) : '/' + id;
}

function translated(t, key, fallback) {
  const text = t(key);
  return text === key ? fallback : text;
}

function PageHead({ data, period, setPeriod, commands }) {
  const { t, fmt } = useUi();
  const review = data.level.last_analysis;
  return html`
    <div class="learn-head">
      <div class="learn-title">
        <h1>${t('learning.title')}</h1>
        <p class="muted">${t('learning.subtitle', { count: data.summary.applied, period: t('period.of.' + period) })}${' · '}${review ? t('learning.lastReview', { date: fmt.dayMonth(review.slice(0, 10)) }) : t('learning.noReview')}</p>
      </div>
      <div class="learn-tools">
        <div class="segmented" role="group" aria-label=${t('learning.period')}>
          ${PERIODS.map((p) => html`<button type="button" aria-pressed=${String(period === p)}
            onClick=${() => setPeriod(p)}>${t('period.' + p)}</button>`)}
        </div>
        <span class="learn-command">${t('learning.update')} <code>${commandFor(commands, 'analyze-results')}</code></span>
      </div>
    </div>`;
}

function LevelStrip({ level, fit, lastRefresh, commands }) {
  const { t, fmt } = useUi();
  const needs = level.needs || {};
  const needList = [
    needs.resolved ? t('level.needs.resolved', { count: needs.resolved }) : null,
    needs.interviews ? t('level.needs.interviews', { count: needs.interviews }) : null,
    needs.validated_analysis ? t('level.needs.analysis') : null,
    needs.validated_analyses ? t('level.needs.again', { count: needs.days_between }) : null,
  ].filter(Boolean);
  const decided = fit.decisions.tracked + fit.decisions.dismissed;
  const fitNeeds = Math.max(0, fit.needs - decided);
  return html`
    <section class="card level-strip" aria-labelledby="level-title">
      <div class="level-main">
        <h2 id="level-title">${t('level.title', { name: t('level.' + level.name) })}</h2>
        <ol class="level-steps" aria-label=${t('level.steps')}>
          ${LEVELS.map((name, index) => html`
            <li class=${index < level.level ? 'done' : index === level.level ? 'current' : ''}
              aria-current=${index === level.level ? 'step' : undefined}>${t('level.' + name)}</li>`)}
        </ol>
      </div>
      <p>${t('level.enables.' + level.name)}
        ${needList.length > 0 && html` <span class="muted">${t('level.next', { needs: fmt.list(needList) })}</span>`}</p>
      ${level.model_reason && html`<p class="note">${t('level.withdrawn', { reason: level.model_reason })}</p>`}
      <p class="small">${fit.available ? t('fit.available')
        : fitNeeds > 0 ? t('fit.needs', { count: fitNeeds, each: fit.each })
        : t('fit.needsEach', { each: fit.each })}${' · '}${lastRefresh ? t('level.refreshed', { time: fmt.shortDateTime(lastRefresh) }) : t('level.neverRefreshed')}</p>
      ${level.suggest_analysis && html`
        <div class="level-review">
          <p>${t('level.suggestReview', { count: level.resolved_since_analysis })}</p>
          <${CommandChip} command=${commandFor(commands, 'analyze-results')} note=${false} />
        </div>`}
    </section>`;
}

function Indicators({ summary, ghostDays }) {
  const { t } = useUi();
  const none = summary.resolved === 0;
  const cards = [
    { key: 'response', value: none ? '–' : `${summary.response.pct}%`,
      sub: t('kpi.responseSub', { count: summary.response.count, of: summary.response.of }) },
    { key: 'interview', value: none ? '–' : `${summary.interview.pct}%`,
      sub: t('kpi.of', { count: summary.interview.count, of: summary.interview.of }) },
    { key: 'offers', value: summary.offers, sub: t('kpi.offersSub', { count: summary.applied }),
      note: offeredVsAsked(t, summary.offered_salary) },
    { key: 'ghosting', value: none ? '–' : `${summary.ghosting.pct}%`,
      sub: t('kpi.ghostingSub', { count: summary.ghosting.count, days: ghostDays }) },
    { key: 'days', value: summary.median_days_to_response ?? '–', sub: t('kpi.median') },
  ];
  return html`
    <div class="kpis">${cards.map((card) => html`
      <div class="kpi" data-kpi=${card.key}>
        <span class="kpi-label">${t('kpi.' + card.key)}</span>
        <span class="kpi-value">${card.value}</span>
        <span class="small">${card.sub}</span>
        ${card.note && html`<span class="small kpi-note">${card.note}</span>`}
      </div>`)}</div>`;
}

/** The median difference between offered and asked salaries, when there are cases. */
function offeredVsAsked(t, offered) {
  const compared = offered && offered.vs_asked;
  if (!compared || !compared.cases) return null;
  const pct = compared.median_pct;
  return t('kpi.offeredVsAsked', { pct: `${pct > 0 ? '+' : ''}${pct}%`, count: compared.cases });
}

function Lessons({ lessons, onDecide }) {
  const { t, fmt } = useUi();
  const shown = [...lessons.filter((l) => l.status === 'proposed'), ...lessons.filter((l) => l.status === 'active')];
  return html`
    <section class="card lessons" aria-labelledby="lessons-title">
      <div class="lessons-head">
        <h2 id="lessons-title">${t('lesson.title')}</h2>
        <span class="small">${t('lesson.how')}</span>
      </div>
      ${shown.length === 0 ? html`<p class="note">${t('lesson.none')}</p>` : html`
        <ul>${shown.map((lesson) => html`
          <li class=${'lesson' + (lesson.status === 'proposed' ? ' proposed' : '')} data-rule=${lesson.id}>
            <div class="lesson-text">
              <strong>${lesson.text}</strong>
              <span class="small">${t('lesson.affects', { area: translated(t, 'area.' + lesson.area, lesson.area) })}</span>
            </div>
            <p class="lesson-evidence">${lesson.evidence}</p>
            <div class="lesson-actions">
              ${lesson.status === 'proposed' ? html`
                <button type="button" class="btn btn-primary" onClick=${() => onDecide(lesson, 'apply')}>
                  ${t('lesson.apply')}</button>
                <button type="button" class="btn" onClick=${() => onDecide(lesson, 'ignore')}>
                  ${t('lesson.ignore')}</button>` : html`
                <span class="applied-chip">${t('lesson.appliedOn', {
                  date: fmt.dayMonth((lesson.applied_at || lesson.updated_at).slice(0, 10)) })}</span>
                <button type="button" class="link-btn" onClick=${() => onDecide(lesson, 'revert')}>
                  ${t('lesson.revert')}</button>`}
            </div>
          </li>`)}</ul>`}
    </section>`;
}

function BreakdownCard({ dimension, data }) {
  const { t } = useUi();
  let groups = data.groups;
  if (dimension === 'score_band') {
    groups = [...groups].sort((a, b) => SCORE_ORDER.indexOf(a.group) - SCORE_ORDER.indexOf(b.group));
  }
  const few = groups.some((g) => g.insufficient);
  return html`
    <section class="card breakdown" data-dimension=${dimension} aria-labelledby=${'bd-' + dimension}>
      <h2 id=${'bd-' + dimension}>${t('bd.title.' + dimension)}</h2>
      <p class="small">${t('bd.sub.' + dimension)}</p>
      ${groups.length === 0 ? html`<p class="note">${t('breakdown.none')}</p>` : html`
        <table class="bd-table">
          <thead><tr><th scope="col">${t('bd.col.' + dimension)}</th><th scope="col">${t('breakdown.rate')}</th>
            <th scope="col"><span class="sr-only">%</span></th><th scope="col" class="num">${t('breakdown.cases')}</th></tr></thead>
          <tbody>${groups.map((g) => html`
            <tr class=${g.insufficient ? 'insufficient' : ''}
              title=${g.insufficient ? t('breakdown.few') : t('estimate.range', { low: pct(g.low), high: pct(g.high) })}>
              <th scope="row">${translated(t, 'group.' + g.group, g.group)}</th>
              <td class="bd-bar"><div class="bar"><div style=${{ width: pct(g.raw) }}></div></div></td>
              <td class="mono num">${pct(g.raw)}${g.insufficient ? '*' : ''}</td>
              <td class="mono num">${g.cases}</td>
            </tr>`)}</tbody>
        </table>`}
      ${few && html`<p class="bd-foot">${t('breakdown.fewNote')}</p>`}
    </section>`;
}

function TrackRecord({ record }) {
  const { t } = useUi();
  return html`
    <section class="card breakdown track-record" aria-labelledby="track-title">
      <h2 id="track-title">${t('track.title')}</h2>
      <p class="small">${t('track.summary', { tested: record.tested,
        model: record.model_brier.toFixed(3), base: record.base_brier.toFixed(3) })}</p>
      <table class="bd-table">
        <thead><tr><th scope="col">${t('track.range')}</th><th scope="col" class="num">${t('track.predicted')}</th>
          <th scope="col" class="num">${t('track.actual')}</th><th scope="col" class="num">${t('breakdown.cases')}</th></tr></thead>
        <tbody>${record.calibration.map((row) => html`
          <tr><th scope="row">${pct(row.range[0])} – ${pct(row.range[1])}</th>
            <td class="mono num">${pct(row.predicted)}</td><td class="mono num">${pct(row.actual)}</td>
            <td class="mono num">${row.cases}</td></tr>`)}</tbody>
      </table>
      <p class="bd-foot">${t('track.note')}</p>
    </section>`;
}

function Suggestions({ recs, experiments, onExperiment }) {
  const { t } = useUi();
  const proposed = experiments.filter((e) => e.status === 'proposed');
  const running = experiments.filter((e) => e.status === 'active' || e.status === 'concluded');
  const emphasis = recs.resume_emphasis || { emphasis: [], gaps: [] };
  return html`
    <section class="card breakdown recommendations" aria-labelledby="recs-title">
      <h2 id="recs-title">${t('recs.title')}</h2>
      <p class="small">${t('recs.note')}</p>
      <h3>${t('recs.applyNext')}</h3>
      ${recs.apply_next.length === 0 ? html`<p class="note">${t('recs.nothingToApply')}</p>` : html`
        <ol class="apply-next">${recs.apply_next.map((item) => html`
          <li><div class="lesson-text"><strong>${item.job_id} · ${item.title}</strong>
              <span class="small">${item.company}${item.estimate && item.estimate.factors.length > 0
                ? ' · ' + item.estimate.factors.map((f) => featureText(t, f.feature)).join(' · ') : ''}</span></div>
            <${ChanceCell} estimate=${item.estimate} /></li>`)}</ol>`}
      <h3>${t('recs.timing')}</h3>
      ${recs.timing ? html`<p>${t('recs.followUp', { count: recs.timing.follow_up_after_days })}
          ${' '}${t('recs.ghost', { count: recs.timing.ghost_after_days })}</p>
        <p class="small">${t('recs.timingBasis', { count: recs.timing.responses, days: recs.timing.median_days })}</p>`
        : html`<p class="note">${t('recs.noTiming')}</p>`}
      <h3>${t('recs.resume')}</h3>
      ${emphasis.emphasis.length > 0 && html`<p class="small">${t('recs.emphasis')}</p>
        <div class="tags">${emphasis.emphasis.map((e) => html`<span class="tag info">${e.term}</span>`)}</div>`}
      ${emphasis.gaps.length > 0 && html`<p class="small">${t('recs.gaps')}</p>
        <div class="tags">${emphasis.gaps.map((g) => html`<span class="tag">${g.term}</span>`)}</div>
        <p class="note">${t('recs.gapsNote')}</p>`}
      ${emphasis.emphasis.length === 0 && emphasis.gaps.length === 0 && html`<p class="note">${t('recs.noResume')}</p>`}
      <h3>${t('exp.title')}</h3>
      ${proposed.length === 0 && running.length === 0 && html`<p class="note">${
        recs.experiments.length > 0 ? t('exp.ideas', { count: recs.experiments.length }) : t('exp.none')}</p>`}
      <ul class="experiments">
        ${proposed.map((e) => html`
          <li class="lesson proposed" data-experiment=${e.id}>
            <div class="lesson-text"><strong>${e.question}</strong>
              <span class="small">${t('exp.plan', { a: e.option_a, b: e.option_b, count: e.planned })}</span></div>
            <div class="lesson-actions">
              <button type="button" class="btn btn-primary" onClick=${() => onExperiment(e, 'accept')}>${t('exp.accept')}</button>
              <button type="button" class="btn" onClick=${() => onExperiment(e, 'decline')}>${t('exp.decline')}</button>
            </div>
          </li>`)}
        ${running.map((e) => html`
          <li class="lesson" data-experiment=${e.id}>
            <div class="lesson-text"><strong>${e.question}</strong>
              <span class="small">${t('exp.status.' + e.status)}</span></div>
          </li>`)}
      </ul>
    </section>`;
}

export function LearningBoard({ version, commands, onAction }) {
  const { t } = useUi();
  const [period, setPeriod] = useState('season');
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(null);

  useEffect(() => {
    let live = true;
    api.learning(period).then((body) => { if (live) { setData(body); setFailed(null); } })
      .catch((error) => live && setFailed(error));
    return () => { live = false; };
  }, [period, version]);

  if (failed && !data) return html`<${EmptyState} title=${t('error.generic', { message: failed.message })} />`;
  if (!data) return html`<section class="card empty"><p>${t('learning.loading')}</p></section>`;

  const decide = (lesson, action) => onAction(async () => {
    await api.decideRule(lesson.id, action);
    setData(await api.learning(period));
    return { message: t('lesson.done.' + action) };
  });
  const experiment = (item, action) => onAction(async () => {
    await api.decideExperiment(item.id, action);
    setData(await api.learning(period));
    return { message: t('exp.done.' + action) };
  });

  const level = data.level;
  const noApplications = data.summary.applied === 0 && level.resolved === 0;
  const dimensions = ORDER.filter((d) => data.breakdowns[d]);
  return html`
    <${PageHead} data=${data} period=${period} setPeriod=${setPeriod} commands=${commands} />
    <${LevelStrip} level=${level} fit=${data.fit} lastRefresh=${data.last_refresh} commands=${commands} />
    ${noApplications ? html`<${EmptyState} heading="h2" title=${t('learning.emptyTitle')}
      body=${t('learning.emptyBody')} />` : html`<${Indicators} summary=${data.summary} ghostDays=${data.ghost_after_days} />`}
    <${Lessons} lessons=${data.lessons} onDecide=${decide} />
    ${!noApplications && level.level < 1 && html`<p class="note learn-note">${t('learning.collectingNote')}</p>`}
    ${(dimensions.length > 0 || data.track_record || data.recommendations) && html`
      <div class="breakdowns">
        ${dimensions.map((d) => html`<${BreakdownCard} dimension=${d} data=${data.breakdowns[d]} />`)}
        ${data.track_record && html`<${TrackRecord} record=${data.track_record} />`}
        ${data.recommendations && html`<${Suggestions} recs=${data.recommendations}
          experiments=${data.experiments || []} onExperiment=${experiment} />`}
      </div>`}`;
}
