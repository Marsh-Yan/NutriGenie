import { ref } from 'vue'
import { defineStore } from 'pinia'
import { localStateRepository } from '@/repositories/localStateRepository'
import type { PreferenceState } from '@/types/localState'

export const usePreferenceStore = defineStore('preference', () => {
  const userId = ref<number | null>(null)
  const note = ref('')

  function hydrate(nextUserId: number) {
    userId.value = nextUserId
    const state = localStateRepository.readUser<PreferenceState>(nextUserId, 'preferences', { note: '' })
    note.value = typeof state?.note === 'string' ? state.note.slice(0, 300) : ''
  }

  function setNote(nextNote: string) {
    note.value = nextNote.slice(0, 300)
    if (!userId.value) return
    localStateRepository.writeUser<PreferenceState>(userId.value, 'preferences', { note: note.value })
  }

  function clear() {
    note.value = ''
    if (userId.value) localStateRepository.removeUser(userId.value, 'preferences')
  }

  function resetMemory() {
    userId.value = null
    note.value = ''
  }

  return { userId, note, hydrate, setNote, clear, resetMemory }
})
