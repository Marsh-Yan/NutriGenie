import type { PlanExecution } from '../types'
import type { MealExecutionStatus } from '../types/localState'

export function validLegacyExecution(raw: unknown): Record<string, MealExecutionStatus> {
  if (!raw || typeof raw !== 'object') return {}
  const allowed = new Set<MealExecutionStatus>(['completed', 'adjusted', 'skipped'])
  return Object.fromEntries(Object.entries(raw).filter((entry): entry is [string, MealExecutionStatus] => (
    /^day:[1-7]:slot:(breakfast|lunch|dinner)$/.test(entry[0]) && allowed.has(entry[1] as MealExecutionStatus)
  )))
}

export function reconcileExecution(local: Record<string, MealExecutionStatus>, remote: PlanExecution) {
  const statuses: Record<string, MealExecutionStatus> = {}
  for (const event of remote.events) {
    const key = `day:${event.day}:slot:${event.meal_slot}`
    statuses[key] = event.status === 'planned' ? 'pending' : event.status
  }
  return {
    statuses,
    pendingImport: Object.fromEntries(Object.entries(local).filter(([key]) => !(key in statuses))),
    conflictCount: Object.keys(local).filter(key => key in statuses && local[key] !== statuses[key]).length,
  }
}
