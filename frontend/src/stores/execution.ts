import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { localStateRepository } from '@/repositories/localStateRepository'
import type { MealExecutionState, MealExecutionStatus } from '@/types/localState'

export function mealExecutionKey(day: number, slot: string) {
  return `day:${day}:slot:${slot}`
}

export const useExecutionStore = defineStore('execution', () => {
  const userId = ref<number | null>(null)
  const planId = ref<number | null>(null)
  const statuses = ref<Record<string, MealExecutionStatus>>({})

  const handledCount = computed(() =>
    Object.values(statuses.value).filter(status => status !== 'pending').length,
  )

  function persist() {
    if (!userId.value || !planId.value) return
    localStateRepository.writePlan<MealExecutionState>(userId.value, planId.value, 'execution', {
      statuses: statuses.value,
    })
  }

  function hydrate(nextUserId: number, nextPlanId: number) {
    userId.value = nextUserId
    planId.value = nextPlanId
    const state = localStateRepository.readPlan<MealExecutionState>(
      nextUserId,
      nextPlanId,
      'execution',
      { statuses: {} },
    )
    const allowed = new Set<MealExecutionStatus>(['pending', 'completed', 'adjusted', 'skipped'])
    statuses.value = state && typeof state.statuses === 'object' && state.statuses
      ? Object.fromEntries(Object.entries(state.statuses).filter((entry): entry is [string, MealExecutionStatus] => allowed.has(entry[1])))
      : {}
  }

  function statusFor(day: number, slot: string): MealExecutionStatus {
    return statuses.value[mealExecutionKey(day, slot)] || 'pending'
  }

  function setStatus(day: number, slot: string, status: MealExecutionStatus) {
    statuses.value = { ...statuses.value, [mealExecutionKey(day, slot)]: status }
    persist()
  }

  function reset() {
    statuses.value = {}
    if (userId.value && planId.value) {
      localStateRepository.removePlan(userId.value, planId.value, 'execution')
    }
  }

  function resetMemory() {
    userId.value = null
    planId.value = null
    statuses.value = {}
  }

  return { userId, planId, statuses, handledCount, hydrate, statusFor, setStatus, reset, resetMemory }
})
