export const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

function buildUrl(path) {
  if (/^https?:\/\//.test(path)) return path;
  return `${API_BASE}${path}`;
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
    
    const data = await response.json();
    return data;
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
