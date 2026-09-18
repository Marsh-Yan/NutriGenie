import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { localStateRepository } from '@/repositories/localStateRepository'
import type { ShoppingCheckState } from '@/types/localState'

export const useShoppingStateStore = defineStore('shopping-state', () => {
  const userId = ref<number | null>(null)
  const planId = ref<number | null>(null)
  const checkedKeys = ref<string[]>([])
  const checkedSet = computed(() => new Set(checkedKeys.value))

  function persist() {
    if (!userId.value || !planId.value) return
    localStateRepository.writePlan<ShoppingCheckState>(userId.value, planId.value, 'shopping', {
      checkedKeys: checkedKeys.value,
    })
  }

  function hydrate(nextUserId: number, nextPlanId: number) {
    userId.value = nextUserId
    planId.value = nextPlanId
    const state = localStateRepository.readPlan<ShoppingCheckState>(
      nextUserId,
      nextPlanId,
      'shopping',
      { checkedKeys: [] },
    )
    checkedKeys.value = Array.from(new Set(Array.isArray(state?.checkedKeys) ? state.checkedKeys.filter(key => typeof key === 'string') : []))
  }

  function toggle(key: string) {
    checkedKeys.value = checkedSet.value.has(key)
      ? checkedKeys.value.filter(item => item !== key)
      : [...checkedKeys.value, key]
    persist()
  }

  function reset() {
    checkedKeys.value = []
    if (userId.value && planId.value) {
      localStateRepository.removePlan(userId.value, planId.value, 'shopping')
    }
  }

  function resetMemory() {
    userId.value = null
    planId.value = null
    checkedKeys.value = []
  }

  return { userId, planId, checkedKeys, checkedSet, hydrate, toggle, reset, resetMemory }
})
