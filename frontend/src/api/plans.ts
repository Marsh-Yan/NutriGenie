import api from './index'
import { normalizePlanResult } from './planResultAdapter'
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
  PlanPage,
  PlanSummary,
  PlanExecution,
  ServerExecutionStatus,
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
  return { ...data, result: normalizePlanResult(data.result) }
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

export async function getPlanPage(page = 1, archived = false, pageSize = 20): Promise<PlanPage> {
  const { data } = await api.get('/plans', { params: { page, page_size: pageSize, archived } })
  return data
}

export async function updatePlanMetadata(planId: number, patch: { title?: string; archived?: boolean }): Promise<PlanSummary> {
  const { data } = await api.patch(`/plans/${planId}`, patch)
  return data
}

export async function clonePlan(planId: number, title?: string): Promise<PlanCreateResponse> {
  const { data } = await api.post(`/plans/${planId}/clone`, title ? { title } : {})
  return data
}

export async function getPlanExecution(planId: number): Promise<PlanExecution> {
  const { data } = await api.get(`/plans/${planId}/execution`)
  return data
}

export async function putPlanExecution(
  planId: number,
  events: { day: number; meal_slot: 'breakfast' | 'lunch' | 'dinner'; status: ServerExecutionStatus; note: string | null }[],
): Promise<PlanExecution> {
  const { data } = await api.put(`/plans/${planId}/execution`, { events })
  return data
}

export async function importPlanExecution(
  planId: number,
  events: { day: number; meal_slot: 'breakfast' | 'lunch' | 'dinner'; status: ServerExecutionStatus; note: string | null }[],
): Promise<PlanExecution> {
  const { data } = await api.post(`/plans/${planId}/execution/import`, { events })
  return data
}
