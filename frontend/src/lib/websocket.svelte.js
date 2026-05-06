/**
 * WebSocket store for real-time bidirectional communication with the Karkhana backend.
 *
 * Uses Svelte 5 runes ($state, $effect) for reactive connection state.
 * Pattern: ConnectionManager → auto-reconnect with exponential backoff + jitter.
 *
 * Based on Gemini Deep Research (May 2026): SvelteKit + FastAPI WebSocket patterns.
 *
 * Usage:
 *   import { wsStore } from '$lib/websocket.svelte.js';
 *   // Access reactive state:
 *   wsStore.connected   // $state boolean
 *   wsStore.lastMessage  // $state parsed JSON message
 *   // Send messages:
 *   wsStore.send({ type: 'subscribe', topic: 'factory-run:123' });
 */

const WS_URL = 'wss://api.karkhana.one/ws';

const MAX_RECONNECT_DELAY = 30_000; // 30 seconds
const INITIAL_RECONNECT_DELAY = 1_000; // 1 second
const JITTER_FACTOR = 0.3; // ±30% jitter

/**
 * @param {number} delay - base delay in ms
 * @returns {number} delay with ±jitter applied
 */
function jitter(delay) {
  const range = delay * JITTER_FACTOR;
  return delay + (Math.random() * 2 - 1) * range;
}

/**
 * @param {string} [jwt] - JWT token for authentication
 * @returns {string[]} WebSocket sub-protocols
 */
function buildProtocols(jwt) {
  if (jwt) {
    return [`jwt.${jwt}`];
  }
  return [];
}

/**
 * Create a WebSocket store.
 *
 * @param {object} [opts]
 * @param {string} [opts.url] - WebSocket URL (default: wss://api.karkhana.one/ws)
 * @param {() => string | null} [opts.getJwt] - function returning current JWT, or null for anonymous
 * @returns {object} reactive store with connected, lastMessage, send(), connect(), disconnect()
 */
export function createWebSocketStore(opts = {}) {
  const { url = WS_URL, getJwt = () => null } = opts;

  /** @type {WebSocket | null} */
  let ws = null;
  let reconnectAttempts = 0;
  let reconnectTimer = null;
  let intentionalClose = false;
  /** @type {Array<object>} */
  let sendQueue = [];

  // ── Svelte 5 reactive state ─────────────────────────────────────────

  let connected = $state(false);
  let lastMessage = $state(/** @type {object | null} */ (null));
  let error = $state(/** @type {string | null} */ (null));

  // ── Connection logic ────────────────────────────────────────────────

  function connect() {
    if (ws?.readyState === WebSocket.OPEN || ws?.readyState === WebSocket.CONNECTING) {
      return;
    }

    intentionalClose = false;
    const jwt = getJwt?.() ?? null;

    try {
      ws = new WebSocket(url, buildProtocols(jwt));
    } catch (err) {
      error = `WebSocket constructor failed: ${err.message}`;
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      connected = true;
      error = null;
      reconnectAttempts = 0;

      // Flush queued messages
      const queue = sendQueue;
      sendQueue = [];
      for (const msg of queue) {
        _sendRaw(msg);
      }
    };

    ws.onmessage = (event) => {
      try {
        lastMessage = JSON.parse(event.data);
      } catch {
        lastMessage = { type: 'raw', data: event.data };
      }
    };

    ws.onclose = (event) => {
      connected = false;
      ws = null;

      if (!intentionalClose) {
        scheduleReconnect();
      }
    };

    ws.onerror = () => {
      error = 'WebSocket connection error';
    };
  }

  function disconnect() {
    intentionalClose = true;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (ws) {
      ws.close(1000, 'Client disconnect');
      ws = null;
    }
    connected = false;
  }

  function scheduleReconnect() {
    if (intentionalClose) return;

    const delay = Math.min(
      INITIAL_RECONNECT_DELAY * Math.pow(2, reconnectAttempts),
      MAX_RECONNECT_DELAY
    );
    reconnectAttempts++;

    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, jitter(delay));
  }

  // ── Send ────────────────────────────────────────────────────────────

  function _sendRaw(msg) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  }

  /**
   * Send a JSON message. Queues if not connected, sends immediately if connected.
   * @param {object} msg
   * @param {string} msg.type
   */
  function send(msg) {
    if (ws?.readyState === WebSocket.OPEN) {
      _sendRaw(msg);
    } else {
      sendQueue.push(msg);
      // Auto-connect if not already connecting
      if (!ws || ws.readyState === WebSocket.CLOSED) {
        connect();
      }
    }
  }

  // ── Auto-connect on creation (if client-side) ──────────────────────

  if (typeof window !== 'undefined') {
    connect();
  }

  // ── Return reactive API ─────────────────────────────────────────────

  return {
    get connected() {
      return connected;
    },
    get lastMessage() {
      return lastMessage;
    },
    get error() {
      return error;
    },
    send,
    connect,
    disconnect,
  };
}

/**
 * Singleton WebSocket store for the Karkhana app.
 * Provide getJwt to enable authenticated connections.
 */
export const wsStore = createWebSocketStore();
