import { writable, get } from 'svelte/store'

export const workerStatus = writable('idle')
export const currentJob = writable(null)
export const jobHistory = writable([])
export const logs = writable([])
export const workerConfig = writable({})
export const connectionHealth = writable({ connected: false, lastHeartbeat: null, uptime: 0 })
export const pairingStatus = writable(null)

// --- Health store ---
export const health = writable({
  apiConnected: false,
  sqsMessages: 0,
  sessionCount: 0,
  lastJobTime: null,
  errorCount: 0,
})

export function updateHealth(data) {
  health.update(h => ({ ...h, ...data }))
}

// --- Log entries store (structured, max 1000) ---
let _nextLogId = 0
export const logEntries = writable([])

export function addLog(level, message) {
  const entry = {
    id: ++_nextLogId,
    level,
    message,
    timestamp: Date.now(),
  }
  logEntries.update(entries => {
    const next = [entry, ...entries]
    if (next.length > 1000) next.length = 1000
    return next
  })
}

// --- Clear errors (zero errorCount in health) ---
export function clearErrors() {
  health.update(h => ({ ...h, errorCount: 0 }))
}

// --- Revoked store ---
export const revoked = writable({
  isRevoked: false,
  reason: '',
  countdown: 0,
})
