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

export const api = {
  state: () => request('GET', '/api/state'),
  changes: () => request('GET', '/api/changes'),
  search: (run) => request('GET', run ? `/api/search?run=${encodeURIComponent(run)}` : '/api/search'),
  providers: () => request('GET', '/api/providers'),
  setProvider: (id, enabled) => request('POST', `/api/providers/${encodeURIComponent(id)}`, { enabled }),
  setLanguage: (language) => request('POST', '/api/settings/language', { language }),
  track: (ids, applied = false) => request('POST', '/api/actions/track', { posting_ids: ids, applied }),
  untrack: (ids) => request('POST', '/api/actions/untrack', { posting_ids: ids }),
  dismiss: (ids, reason, note) => request('POST', '/api/actions/dismiss', { posting_ids: ids, reason, note }),
  undismiss: (ids) => request('POST', '/api/actions/undismiss', { posting_ids: ids }),
};
