interface StoredEnvelope<T> {
  version: 1
  updatedAt: string
  data: T
}

type StorageScope =
  | 'dashboard'
  | 'plan-index'
  | 'execution'
  | 'shopping'
  | 'pantry'
  | 'preferences'

const STORAGE_PREFIX = 'nutrigenie:v1'

function getStorage() {
  if (typeof window === 'undefined') return null
  try {
    return window.localStorage
  } catch {
    return null
  }
}

function copyFallback<T>(fallback: T): T {
  return JSON.parse(JSON.stringify(fallback)) as T
}

function safeSegment(value: string | number) {
  return encodeURIComponent(String(value))
}

export function userStorageKey(userId: number, scope: StorageScope) {
  return `${STORAGE_PREFIX}:user:${safeSegment(userId)}:${scope}`
}

export function planStorageKey(userId: number, planId: number, scope: StorageScope) {
  return `${STORAGE_PREFIX}:user:${safeSegment(userId)}:plan:${safeSegment(planId)}:${scope}`
}

function readValue<T>(key: string, fallback: T): T {
  const storage = getStorage()
  if (!storage) return copyFallback(fallback)

  try {
    const raw = storage.getItem(key)
    if (!raw) return copyFallback(fallback)
    const envelope = JSON.parse(raw) as StoredEnvelope<T>
    if (envelope?.version !== 1 || envelope.data === undefined) {
      storage.removeItem(key)
      return copyFallback(fallback)
    }
    return envelope.data
  } catch {
    try { storage.removeItem(key) } catch { /* Storage may be unavailable in private or restricted contexts. */ }
    return copyFallback(fallback)
  }
}

function writeValue<T>(key: string, data: T) {
  const storage = getStorage()
  if (!storage) return
  const envelope: StoredEnvelope<T> = {
    version: 1,
    updatedAt: new Date().toISOString(),
    data,
  }
  try {
    storage.setItem(key, JSON.stringify(envelope))
  } catch {
    // Local progress is an enhancement; quota or privacy restrictions must not break the core flow.
  }
}

export const localStateRepository = {
  readUser<T>(userId: number, scope: StorageScope, fallback: T) {
    return readValue(userStorageKey(userId, scope), fallback)
  },

  writeUser<T>(userId: number, scope: StorageScope, data: T) {
    writeValue(userStorageKey(userId, scope), data)
  },

  removeUser(userId: number, scope: StorageScope) {
    try { getStorage()?.removeItem(userStorageKey(userId, scope)) } catch { /* no-op */ }
  },

  readPlan<T>(userId: number, planId: number, scope: StorageScope, fallback: T) {
    return readValue(planStorageKey(userId, planId, scope), fallback)
  },

  writePlan<T>(userId: number, planId: number, scope: StorageScope, data: T) {
    writeValue(planStorageKey(userId, planId, scope), data)
  },

  removePlan(userId: number, planId: number, scope: StorageScope) {
    try { getStorage()?.removeItem(planStorageKey(userId, planId, scope)) } catch { /* no-op */ }
  },
}
