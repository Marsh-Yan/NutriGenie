import { ref } from 'vue'
import { defineStore } from 'pinia'
import { localStateRepository } from '@/repositories/localStateRepository'
import type { DashboardState } from '@/types/localState'

export const useDashboardStore = defineStore('dashboard', () => {
  const userId = ref<number | null>(null)
  const currentPlanId = ref<number | null>(null)

  function hydrate(nextUserId: number) {
    userId.value = nextUserId
    const state = localStateRepository.readUser<DashboardState>(nextUserId, 'dashboard', {
      currentPlanId: null,
    })
    currentPlanId.value = state && Number.isInteger(state.currentPlanId) ? state.currentPlanId : null
  }

  function selectPlan(planId: number | null) {
    currentPlanId.value = planId
    if (!userId.value) return
    localStateRepository.writeUser<DashboardState>(userId.value, 'dashboard', {
      currentPlanId: planId,
    })
  }

  function resetMemory() {
    userId.value = null
    currentPlanId.value = null
  }

  return { userId, currentPlanId, hydrate, selectPlan, resetMemory }
})
