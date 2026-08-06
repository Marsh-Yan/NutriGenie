import api from './index'
import type { AuthResponse, AuthUser } from '@/types'

export const register = (data: { email: string; nickname: string; password: string; verification_code: string }) => api.post<AuthResponse>('/auth/register', data).then(r => r.data)
export const login = (data: { email: string; password: string }) => api.post<AuthResponse>('/auth/login', data).then(r => r.data)
export const me = () => api.get<AuthUser>('/auth/me').then(r => r.data)
