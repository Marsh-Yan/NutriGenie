import api from './index'
import type { PlanCreateRequest, PlanCreateResponse, PlanStatusResponse, PlanResultResponse } from '@/types'

export async function createPlan(data: PlanCreateRequest): Promise<PlanCreateResponse> {
  const { data: res } = await api.post('/plans', data)
  return res
}

export async function getPlanStatus(planId: number): Promise<PlanStatusResponse> {
  const { data } = await api.get(`/plans/${planId}/status`)
  return data
}

export async function getPlanResult(planId: number): Promise<PlanResultResponse> {
  const { data } = await api.get(`/plans/${planId}`)
  return data
}
