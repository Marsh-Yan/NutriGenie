import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { localStateRepository } from '@/repositories/localStateRepository'
import { getPlanExecution, importPlanExecution, putPlanExecution } from '@/api/plans'
import type { PlanExecution, ServerExecutionStatus } from '@/types'
import type { MealExecutionState, MealExecutionStatus } from '@/types/localState'
import { reconcileExecution, validLegacyExecution } from '@/utils/executionMigration'

export function mealExecutionKey(day: number, slot: string) {
  return `day:${day}:slot:${slot}`
}

export const useExecutionStore = defineStore('execution', () => {
  const userId = ref<number | null>(null)
  const planId = ref<number | null>(null)
  const statuses = ref<Record<string, MealExecutionStatus>>({})
  const localLegacy = ref<Record<string, MealExecutionStatus>>({})
  const pendingImport = ref<Record<string, MealExecutionStatus>>({})
  const conflictCount = ref(0)
  const loading = ref(false)
  const ready = ref(false)
  const saving = ref(false)
  const error = ref('')
  let scopeVersion = 0

  const handledCount = computed(() =>
    Object.values(statuses.value).filter(status => status !== 'pending').length,
  )

  function applyRemote(remote: PlanExecution) {
    const reconciled = reconcileExecution(localLegacy.value, remote)
    statuses.value = reconciled.statuses
    pendingImport.value = reconciled.pendingImport
    conflictCount.value = reconciled.conflictCount
  }

  function hydrate(nextUserId: number, nextPlanId: number) {
    scopeVersion += 1
    userId.value = nextUserId
    planId.value = nextPlanId
    const state = localStateRepository.readPlan<MealExecutionState>(
      nextUserId,
      nextPlanId,
      'execution',
      { statuses: {} },
    )
    localLegacy.value = validLegacyExecution(state?.statuses)
    statuses.value = { ...localLegacy.value }
    pendingImport.value = {}
    conflictCount.value = 0
    loading.value = false
    ready.value = false
    saving.value = false
    error.value = ''
  }

  async function loadServer() {
    const requestedUser = userId.value
    const requestedPlan = planId.value
    const requestedScope = scopeVersion
    if (!requestedUser || !requestedPlan) return
    loading.value = true
    ready.value = false
    error.value = ''
    try {
      const remote = await getPlanExecution(requestedPlan)
      if (requestedScope !== scopeVersion || requestedUser !== userId.value || requestedPlan !== planId.value) return
      applyRemote(remote)
      ready.value = true
    } catch (cause) {
      if (requestedScope === scopeVersion && requestedUser === userId.value && requestedPlan === planId.value) {
        error.value = cause instanceof Error ? cause.message : '执行状态加载失败'
        statuses.value = {}
      }
    } finally {
      if (requestedScope === scopeVersion && requestedUser === userId.value && requestedPlan === planId.value) loading.value = false
    }
  }

  function statusFor(day: number, slot: string): MealExecutionStatus {
    return statuses.value[mealExecutionKey(day, slot)] || 'pending'
  }

  async function setStatus(day: number, slot: string, status: MealExecutionStatus) {
    if (!ready.value || saving.value || !planId.value) return
    if (!Number.isInteger(day) || day < 1 || day > 7 || !['breakfast', 'lunch', 'dinner'].includes(slot)) return
    const requestedScope = scopeVersion
    const requestedPlan = planId.value
    saving.value = true
    error.value = ''
    try {
      const remote = await putPlanExecution(requestedPlan, [{
        day,
        meal_slot: slot as 'breakfast' | 'lunch' | 'dinner',
        status: (status === 'pending' ? 'planned' : status) as ServerExecutionStatus,
        note: null,
      }])
      if (requestedScope === scopeVersion) applyRemote(remote)
    } catch (cause) {
      if (requestedScope === scopeVersion) error.value = cause instanceof Error ? cause.message : '保存失败，请重试'
    } finally {
      if (requestedScope === scopeVersion) saving.value = false
    }
  }

  async function importLocal() {
    if (!ready.value || saving.value || !planId.value) return
    const requestedScope = scopeVersion
    const requestedPlan = planId.value
    const requestedUser = userId.value
    if (!requestedUser) return
    saving.value = true
    error.value = ''
    try {
      // Re-read immediately before importing: a newer server event always wins.
      const latest = await getPlanExecution(requestedPlan)
      if (requestedScope !== scopeVersion) return
      const occupied = new Set(latest.events.map(event => mealExecutionKey(event.day, event.meal_slot)))
      const events = Object.entries(localLegacy.value).filter(([key]) => !occupied.has(key)).map(([key, status]) => {
        const match = /^day:([1-7]):slot:(breakfast|lunch|dinner)$/.exec(key)!
        return { day: Number(match[1]), meal_slot: match[2] as 'breakfast' | 'lunch' | 'dinner', status: status as ServerExecutionStatus, note: null }
      })
      const remote = events.length ? await importPlanExecution(requestedPlan, events) : latest
      if (requestedScope !== scopeVersion) return
      localStateRepository.removePlan(requestedUser, requestedPlan, 'execution')
      localLegacy.value = {}
      applyRemote(remote)
    } catch (cause) {
      if (requestedScope === scopeVersion) {
        await loadServer()
        error.value = cause instanceof Error ? cause.message : '导入失败，本地记录仍保留'
      }
    } finally {
      if (requestedScope === scopeVersion) saving.value = false
    }
  }

  function dismissLocal() {
    if (userId.value && planId.value) localStateRepository.removePlan(userId.value, planId.value, 'execution')
    localLegacy.value = {}
    pendingImport.value = {}
    conflictCount.value = 0
  }

  function reset() {
    statuses.value = {}
    dismissLocal()
  }

  function resetMemory() {
    scopeVersion += 1
    userId.value = null
    planId.value = null
    statuses.value = {}
    localLegacy.value = {}
    pendingImport.value = {}
    conflictCount.value = 0
    ready.value = false
    loading.value = false
    saving.value = false
    error.value = ''
  }

  return { userId, planId, statuses, handledCount, pendingImport, conflictCount, loading, ready, saving, error, hydrate, loadServer, statusFor, setStatus, importLocal, dismissLocal, reset, resetMemory }
})
