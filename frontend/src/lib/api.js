export const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

function isAbsoluteUrl(path) {
  return /^https?:\/\//i.test(path);
}

function normalizePath(path) {
  return path.startsWith('/') ? path : `/${path}`;
}

function isFormDataLike(body) {
  if (typeof FormData !== 'undefined' && body instanceof FormData) return true;
  return Boolean(body && typeof body === 'object' && typeof body.append === 'function');
}

function normalizeHeaders(headers = {}) {
  if (headers instanceof Headers) {
    return Object.fromEntries(headers.entries());
  }

  if (Array.isArray(headers)) {
    return Object.fromEntries(headers);
  }

  return { ...headers };
}

function hasContentType(headers) {
  return Object.keys(headers).some((key) => key.toLowerCase() === 'content-type');
}

function isJsonLikeBody(body) {
  return body !== null
    && typeof body === 'object'
    && !isFormDataLike(body)
    && !(body instanceof Blob)
    && !(body instanceof ArrayBuffer)
    && !(body instanceof URLSearchParams);
}

function appendQuery(url, query = {}) {
  const [base, existingQuery = ''] = url.split('?');
  const params = new URLSearchParams(existingQuery);
  for (const [key, value] of Object.entries(query || {})) {
    if (value === undefined || value === null || value === '') continue;
    params.set(key, String(value));
  }

  const queryString = params.toString();
  return queryString ? `${base}?${queryString}` : base;
}

export function buildApiUrl(path, query = null, base = API_BASE) {
  const url = isAbsoluteUrl(path)
    ? path
    : `${base ? base.replace(/\/$/, '') : ''}/${normalizePath(path).replace(/^\//, '')}`;

  return query ? appendQuery(url, query) : url;
}

function getResponseHeader(response, name) {
  return response?.headers?.get?.(name) || response?.headers?.[name.toLowerCase()] || '';
}

function looksLikeJson(contentType, text) {
  return /json/i.test(contentType) || /^[\s\r\n]*[{\[]/.test(text);
}

function looksLikeHtml(contentType, text) {
  return /html/i.test(contentType)
    || /^[\s\r\n]*<!doctype html/i.test(text)
    || /^[\s\r\n]*<html[\s>]/i.test(text);
}

function extractDetail(payload) {
  if (payload && typeof payload === 'object') {
    if (typeof payload.detail === 'string') return payload.detail;
    if (typeof payload.message === 'string') return payload.message;
    if (typeof payload.error === 'string') return payload.error;
    if (payload.detail != null) return payload.detail;
  }

  if (typeof payload === 'string') return payload;
  return null;
}

function formatMessage(detail, fallback) {
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (detail && typeof detail === 'object') {
    try {
      return JSON.stringify(detail);
    } catch {
      return fallback;
    }
  }
  return fallback;
}

async function parseResponseBody(response) {
  const status = response.status;
  const contentType = getResponseHeader(response, 'content-type');
  if (status === 204) {
    return { body: null, text: '', contentType };
  }

  const text = await response.text();
  if (!text || !text.trim()) return { body: null, text, contentType };

  if (looksLikeJson(contentType, text)) {
    try {
      return { body: JSON.parse(text), text, contentType };
    } catch {
      return { body: text, text, contentType };
    }
  }

  return { body: text, text, contentType };
}

export class ApiError extends Error {
  constructor({ status, url, method, detail, message, responseBody }) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.url = url;
    this.method = method;
    this.detail = detail;
    this.responseBody = responseBody;
  }
}

export function buildWebSocketUrl(path) {
  const explicitBase = import.meta.env.VITE_WS_BASE_URL;
  if (explicitBase) return `${explicitBase}${path}`;

  if (API_BASE) {
    const url = new URL(API_BASE, window.location.origin);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${url.origin}${path}`;
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}${path}`;
}

export async function api(path, options = {}) {
  const url = buildApiUrl(path);
  const method = (options.method || 'GET').toUpperCase();
  const headers = normalizeHeaders(options.headers);
  let body = options.body;

  if (isFormDataLike(body)) {
    delete headers['Content-Type'];
    delete headers['content-type'];
  } else if (isJsonLikeBody(body)) {
    if (!hasContentType(headers)) {
      headers['Content-Type'] = 'application/json';
    }
    body = JSON.stringify(body);
  }

  const requestInit = {
    ...options,
    method,
    headers: Object.keys(headers).length ? headers : undefined,
    body,
  };

  try {
    const response = await fetch(url, requestInit);
    const parsedResponse = await parseResponseBody(response);
    const parsedBody = parsedResponse.body;

    if (!response.ok) {
      const detail = looksLikeHtml(parsedResponse.contentType, parsedResponse.text)
        ? null
        : extractDetail(parsedBody);
      const fallback = `Request failed with status ${response.status}`;
      const message = looksLikeHtml(parsedResponse.contentType, parsedResponse.text)
        ? fallback
        : formatMessage(detail, fallback);
      throw new ApiError({
        status: response.status,
        url,
        method,
        detail,
        message,
        responseBody: parsedBody,
      });
    }

    return parsedBody;
  } catch (error) {
    throw error;
  }
}

export async function apiPost(path, body, options = {}) {
  return api(path, {
    method: 'POST',
    body,
    ...options,
  });
}

export async function apiPut(path, body, options = {}) {
  return api(path, {
    method: 'PUT',
    body,
    ...options,
  });
}

export async function apiDelete(path, options = {}) {
  return api(path, {
    method: 'DELETE',
    ...options,
  });
}

export async function createFactoryRun(projectId, body = {}) {
  return apiPost(`/api/projects/${projectId}/factory-runs`, {
    template_id: body.template_id || 'default',
    autonomy_level: body.autonomy_level || 'autonomous_development',
    config: body.config || {},
    intent: body.intent || null,
  });
}

export async function listFactoryRuns(projectId) {
  return api(`/api/projects/${projectId}/factory-runs`);
}

export async function getFactoryRun(factoryRunId) {
  return api(`/api/factory-runs/${factoryRunId}`);
}

export async function createResearchArtifact(factoryRunId, body = {}) {
  return apiPost(`/api/factory-runs/${factoryRunId}/research-artifacts`, {
    title: body.title,
    source: body.source,
    raw_content: body.raw_content ?? null,
    raw_content_uri: body.raw_content_uri ?? null,
    raw_metadata: body.raw_metadata || {},
    normalized: body.normalized ?? null,
    force: body.force || false,
    correlation_id: body.correlation_id ?? null,
    actor: body.actor || 'system',
  });
}

export async function createResearchHandoff(factoryRunId) {
  return apiPost(`/api/factory-runs/${factoryRunId}/research-handoff`, {});
}

export async function getProjectTwin(ideaId) {
  return api(`/api/ideas/${ideaId}/project`);
}

export async function getBuildNextActions(ideaId) {
  return api(`/api/ideas/${ideaId}/build/next-actions`);
}

export async function getFactoryRunJobs(ideaId) {
  return api(`/api/ideas/${ideaId}/jobs`);
}

export async function createReviewPacket(factoryRunId) {
  return apiPost(`/api/factory-runs/${factoryRunId}/review-packet`);
}

export async function getReviewPacket(factoryRunId) {
  return api(`/api/factory-runs/${factoryRunId}/review-packet`);
}

export async function listReviewPackets(filter = null) {
  return api(buildApiUrl('/api/review-packets', filter ? { filter } : null));
}

export async function submitIntervention(factoryRunId, action, rationale = null) {
  return apiPost(`/api/factory-runs/${factoryRunId}/review-packet/intervene`, {
    action,
    rationale,
  });
}

export async function startWaitWindow(factoryRunId, expiresAt = null) {
  return apiPost(`/api/factory-runs/${factoryRunId}/review-packet/start-wait-window`, {
    expires_at: expiresAt,
  });
}

export async function recordExpiry(factoryRunId) {
  return apiPost(`/api/factory-runs/${factoryRunId}/review-packet/record-expiry`);
}
