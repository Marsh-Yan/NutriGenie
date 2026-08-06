import api from './index'
import type { Profile, ProfileFormData } from '@/types'

export async function getProfile(id: number): Promise<Profile> {
  const { data } = await api.get(`/profiles/id/${id}`)
  return data
}

export async function getMyProfile(): Promise<Profile> {
  const { data } = await api.get('/profiles/me')
  return data
}

export async function createProfile(form: ProfileFormData): Promise<Profile> {
  const { data } = await api.post('/profiles', form)
  return data
}

export async function updateProfile(id: number, form: Partial<ProfileFormData>): Promise<Profile> {
  const { data } = await api.put(`/profiles/id/${id}`, form)
  return data
}
