import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { AuthUser } from '@/types'
import * as authApi from '@/api/auth'

const TOKEN_KEY = 'nutrigenie_access_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY))
  const user = ref<AuthUser | null>(null)
  const restored = ref(false)
  const isLoggedIn = computed(() => Boolean(token.value && user.value))
  const isAdmin = computed(() => user.value?.role === 'admin')

  function applySession(accessToken: string, currentUser: AuthUser) {
    token.value = accessToken; user.value = currentUser; localStorage.setItem(TOKEN_KEY, accessToken)
  }
  async function login(email: string, password: string) { const data = await authApi.login({ email, password }); applySession(data.access_token, data.user) }
  async function register(email: string, nickname: string, password: string, verificationCode: string) { const data = await authApi.register({ email, nickname, password, verification_code: verificationCode }); applySession(data.access_token, data.user) }
  async function restore() { if (restored.value) return; try { if (token.value) user.value = await authApi.me() } catch { logout() } finally { restored.value = true } }
  function logout() { token.value = null; user.value = null; localStorage.removeItem(TOKEN_KEY) }
  return { token, user, restored, isLoggedIn, isAdmin, login, register, restore, logout }
})
