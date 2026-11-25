// Fetch wrappers for the panel API. Every response is {ok: true, ...} or {ok: false, error}.

export class ApiError extends Error {
  constructor(code, message, status) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request(method, path, body) {
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    throw new ApiError('offline', String(error), 0);
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    const error = data.error || {};
    const detail = Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join('; ') : null;
    throw new ApiError(error.code || 'http_' + response.status,
      error.message || detail || response.statusText, response.status);
  }
  return data;
}

/** '?a=1&b=2' from the values that are set, or ''. */
function query(params) {
  const parts = Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== '')
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`);
  return parts.length ? '?' + parts.join('&') : '';
}

export const api = {
  state: () => request('GET', '/api/state'),
  changes: () => request('GET', '/api/changes'),
  search: (group, season) => request('GET', '/api/search' + query({ group, season })),
  providers: () => request('GET', '/api/providers'),
  setWorkMode: (postingId, workMode, detail) => request('POST', `/api/postings/${encodeURIComponent(postingId)}/work-mode`,
    { work_mode: workMode, detail }),
  setProvider: (id, enabled) => request('POST', `/api/providers/${encodeURIComponent(id)}`, { enabled }),
  setLanguage: (language) => request('POST', '/api/settings/language', { language }),
  track: (ids, applied = false) => request('POST', '/api/actions/track', { posting_ids: ids, applied }),
  untrack: (ids) => request('POST', '/api/actions/untrack', { posting_ids: ids }),
  dismiss: (ids, reason, note) => request('POST', '/api/actions/dismiss', { posting_ids: ids, reason, note }),
  undismiss: (ids) => request('POST', '/api/actions/undismiss', { posting_ids: ids }),
  restoreFiltered: (ids) => request('POST', '/api/actions/restore-filtered', { posting_ids: ids }),
  applications: (season) => request('GET', '/api/applications' + query({ season })),
  profileBoard: () => request('GET', '/api/profile-board'),
  decideSuggestedTitle: (title, state) => request('POST', '/api/profile/suggested-title', { title, state }),
  resumeUrl: (id) => `/api/resumes/${encodeURIComponent(id)}`,
  application: (job) => request('GET', `/api/applications/${encodeURIComponent(job)}`),
  setStatus: (jobIds, status, ends = null) => request('POST', '/api/applications/status',
    { job_ids: jobIds, status, ends }),
  setDetails: (job, fields) => request('POST', `/api/applications/${encodeURIComponent(job)}/details`, fields),
  removeApplications: (jobs) => request('POST', '/api/applications/remove', { job_ids: jobs }),
  setTags: (job, add = [], remove = []) => request('POST', `/api/applications/${encodeURIComponent(job)}/tags`, { add, remove }),
  documentText: (job, id) => request('GET', `/api/applications/${encodeURIComponent(job)}/documents/${id}/text`),
  documentUrl: (job, id) => `/api/applications/${encodeURIComponent(job)}/documents/${id}`,
  documentDiff: (job, id) => request('GET', `/api/applications/${encodeURIComponent(job)}/documents/${id}/diff`),
  editAnswer: (job, position, text) => request('POST', `/api/applications/${encodeURIComponent(job)}/answers/${position}`, { text }),
  pickAnswer: (job, answerId) => request('POST', `/api/applications/${encodeURIComponent(job)}/answers-pick`, { answer_id: answerId }),
  pending: () => request('GET', '/api/pending'),
  learning: (period) => request('GET', `/api/learning?period=${encodeURIComponent(period)}`),
  decideRule: (id, action) => request('POST', `/api/rules/${encodeURIComponent(id)}/${action}`),
  decideExperiment: (id, action) => request('POST', `/api/experiments/${encodeURIComponent(id)}/${action}`),
  async uploadSentResume(job, file) {
    const form = new FormData();
    form.append('file', file);
    let response;
    try {
      response = await fetch(`/api/applications/${encodeURIComponent(job)}/resume-sent`, { method: 'POST', body: form });
    } catch (error) {
      throw new ApiError('offline', String(error), 0);
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) {
      const error = data.error || {};
      throw new ApiError(error.code || 'http_' + response.status, error.message || response.statusText, response.status);
    }
    return data;
  },
};
