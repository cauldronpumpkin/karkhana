import { vi } from 'vitest';
import '@testing-library/jest-dom/vitest';

// Mock scrollIntoView for jsdom
Element.prototype.scrollIntoView = vi.fn();
Element.prototype.scrollTo = vi.fn();

// Mock WebSocket - must be a constructor function
class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.onopen = null;
    this.onmessage = null;
    this.onclose = null;
    this.onerror = null;
    this.readyState = 1; // OPEN
  }
  send = vi.fn();
  close = vi.fn();
}
global.WebSocket = MockWebSocket;

// Mock FormData
global.FormData = vi.fn().mockImplementation(() => ({
  append: vi.fn(),
}));

// Mock navigator.clipboard
Object.defineProperty(global.navigator, 'clipboard', {
  value: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
  writable: true,
});

// Mock fetch
global.fetch = vi.fn();
