import { ref } from 'vue'
import { defineStore } from 'pinia'
import { localStateRepository } from '@/repositories/localStateRepository'
import type { PantryState } from '@/types/localState'

export const usePantryStore = defineStore('pantry', () => {
  const userId = ref<number | null>(null)
  const items = ref<string[]>([])

  function persist() {
    if (!userId.value) return
    localStateRepository.writeUser<PantryState>(userId.value, 'pantry', { items: items.value })
  }

  function hydrate(nextUserId: number) {
    userId.value = nextUserId
    const state = localStateRepository.readUser<PantryState>(nextUserId, 'pantry', { items: [] })
    const storedItems = Array.isArray(state?.items) ? state.items.filter(item => typeof item === 'string') : []
    items.value = Array.from(new Set(storedItems.map(item => item.trim()).filter(Boolean))).slice(0, 30)
  }

  function add(rawItem: string) {
    const item = rawItem.trim()
    if (!item || items.value.includes(item) || items.value.length >= 30) return false
    items.value = [...items.value, item]
    persist()
    return true
  }

  function remove(item: string) {
    items.value = items.value.filter(candidate => candidate !== item)
    persist()
  }

  function clear() {
    items.value = []
    if (userId.value) localStateRepository.removeUser(userId.value, 'pantry')
  }

  function resetMemory() {
    userId.value = null
    items.value = []
  }

  return { userId, items, hydrate, add, remove, clear, resetMemory }
})
