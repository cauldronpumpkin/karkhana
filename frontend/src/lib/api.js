export const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

function buildUrl(path) {
  if (/^https?:\/\//.test(path)) return path;
  if (!API_BASE) return path;
  return `${API_BASE.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
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
  const url = buildUrl(path);
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  };

  try {
    const response = await fetch(url, defaultOptions);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    if (response.status === 204) return null;

    const text = await response.text();
    return text ? JSON.parse(text) : null;
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

export async function apiPost(path, body, options = {}) {
  return api(path, {
    method: 'POST',
    body: JSON.stringify(body),
    ...options,
  });
}

export async function apiPut(path, body, options = {}) {
  return api(path, {
    method: 'PUT',
    body: JSON.stringify(body),
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
  const params = filter ? `?filter=${filter}` : '';
  return api(`/api/review-packets${params}`);
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
