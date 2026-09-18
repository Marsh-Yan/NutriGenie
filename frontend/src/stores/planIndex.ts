import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { localStateRepository } from '@/repositories/localStateRepository'
import type { LocalPlanIndexItem } from '@/types/localState'

export const usePlanIndexStore = defineStore('plan-index', () => {
  const userId = ref<number | null>(null)
  const items = ref<LocalPlanIndexItem[]>([])

  const sortedItems = computed(() =>
    [...items.value].sort((a, b) => b.lastOpenedAt.localeCompare(a.lastOpenedAt)),
  )

  function persist() {
    if (!userId.value) return
    localStateRepository.writeUser(userId.value, 'plan-index', items.value)
  }

  function hydrate(nextUserId: number) {
    userId.value = nextUserId
    const stored = localStateRepository.readUser<unknown>(nextUserId, 'plan-index', [])
    const statuses = new Set(['pending', 'running', 'completed', 'failed'])
    items.value = Array.isArray(stored)
      ? stored.flatMap(rawItem => {
          if (!rawItem || typeof rawItem !== 'object') return []
          const item = rawItem as Partial<LocalPlanIndexItem>
          if (!Number.isInteger(item.planId) || Number(item.planId) <= 0) return []
          const createdAt = typeof item.createdAt === 'string' ? item.createdAt : new Date().toISOString()
          return [{
            planId: Number(item.planId),
            title: typeof item.title === 'string' && item.title ? item.title : `计划 #${item.planId}`,
            userInput: typeof item.userInput === 'string' ? item.userInput : '',
            durationDays: Number.isFinite(item.durationDays) ? Number(item.durationDays) : 7,
            totalBudget: Number.isFinite(item.totalBudget) ? Number(item.totalBudget) : 0,
            status: statuses.has(String(item.status)) ? item.status! : 'pending',
            createdAt,
            completedAt: typeof item.completedAt === 'string' ? item.completedAt : null,
            lastOpenedAt: typeof item.lastOpenedAt === 'string' ? item.lastOpenedAt : createdAt,
            sourcePlanId: Number.isInteger(item.sourcePlanId) ? Number(item.sourcePlanId) : undefined,
          }]
        })
      : []
  }

  function upsert(item: LocalPlanIndexItem) {
    const index = items.value.findIndex(candidate => candidate.planId === item.planId)
    if (index >= 0) items.value[index] = { ...items.value[index], ...item }
    else items.value.push(item)
    persist()
  }

  function update(planId: number, patch: Partial<LocalPlanIndexItem>) {
    const item = items.value.find(candidate => candidate.planId === planId)
    if (!item) return
    Object.assign(item, patch)
    persist()
  }

  function touch(planId: number) {
    update(planId, { lastOpenedAt: new Date().toISOString() })
  }

  function remove(planId: number) {
    items.value = items.value.filter(item => item.planId !== planId)
    persist()
  }

  function clear() {
    if (userId.value) localStateRepository.removeUser(userId.value, 'plan-index')
    items.value = []
  }

  function resetMemory() {
    userId.value = null
    items.value = []
  }

  return { userId, items, sortedItems, hydrate, upsert, update, touch, remove, clear, resetMemory }
})
