import { writable } from 'svelte/store'

export const workerStatus = writable('idle')
export const currentJob = writable(null)
export const jobHistory = writable([])
export const logs = writable([])
export const workerConfig = writable({})
export const connectionHealth = writable({ connected: false, lastHeartbeat: null, uptime: 0 })
export const pairingStatus = writable(null)
