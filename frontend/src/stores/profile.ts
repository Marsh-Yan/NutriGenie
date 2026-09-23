import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Profile, ProfileFormData } from '@/types'
import * as profileApi from '@/api/profiles'

export const useProfileStore = defineStore('profile', () => {
  const profile = ref<Profile | null>(null)
  const loading = ref(false)

  const hasProfile = computed(() => profile.value !== null)

  const defaultForm: ProfileFormData = {
    age: null,
    gender: null,
    height: null,
    weight: null,
    activity_level: 'moderate',
    diet_type: 'balanced',
    health_goal: 'healthy',
    allergies: [],
  }

  async function fetchProfile(id: number) {
    loading.value = true
    try {
      profile.value = await profileApi.getProfile(id)
    } finally {
      loading.value = false
    }
  }

  async function fetchMyProfile() {
    loading.value = true
    try {
      profile.value = await profileApi.getMyProfile()
      return profile.value
    } catch (error: unknown) {
      if ((error as { status?: number })?.status === 404) {
        profile.value = null
        return null
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  async function saveProfile(form: ProfileFormData): Promise<Profile> {
    loading.value = true
    try {
      const p = await profileApi.createProfile(form)
      profile.value = p
      return p
    } finally {
      loading.value = false
    }
  }

  async function updateProfile(id: number, form: Partial<ProfileFormData>) {
    loading.value = true
    try {
      profile.value = await profileApi.updateProfile(id, form)
    } finally {
      loading.value = false
    }
  }

  function reset() {
    profile.value = null
    loading.value = false
  }

  return { profile, loading, hasProfile, defaultForm, fetchProfile, fetchMyProfile, saveProfile, updateProfile, reset }
})
