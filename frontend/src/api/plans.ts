import api from './index'
import type {
  PlanCreateRequest,
  PlanCreateResponse,
  PlanListItem,
  PlanStatusResponse,
  PlanResultResponse,
  PlanMessage,
  PlanMessageRequest,
  PlanRun,
  PlanVersionSummary,
} from '@/types'

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

export async function sendPlanMessage(planId: number, input: PlanMessageRequest): Promise<PlanRun> {
  const { data } = await api.post(`/plans/${planId}/messages`, input)
  return data
}

export async function retryPlan(planId: number): Promise<PlanRun> {
  const { data } = await api.post(`/plans/${planId}/retry`)
  return data
}

export async function getPlanMessages(planId: number): Promise<PlanMessage[]> {
  const { data } = await api.get(`/plans/${planId}/messages`)
  return data
}

export async function getPlanVersions(planId: number): Promise<{ current_version_id: number | null; items: PlanVersionSummary[] }> {
  const { data } = await api.get(`/plans/${planId}/versions`)
  return data
}

export async function restorePlanVersion(planId: number, versionId: number): Promise<void> {
  await api.post(`/plans/${planId}/versions/${versionId}/restore`)
}

export async function getPlans(): Promise<PlanListItem[]> {
  const { data } = await api.get('/plans')
  return data
}
