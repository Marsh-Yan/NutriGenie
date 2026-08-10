import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { PlanMessage, PlanResult, PlanStatus, ProgressInfo, PlanVersionSummary } from '@/types'
import * as planApi from '@/api/plans'

export const usePlanStore = defineStore('plan', () => {
  const planId = ref<number | null>(null)
  const status = ref<PlanStatus>('pending')
  const progress = ref<ProgressInfo | null>(null)
  const result = ref<PlanResult | null>(null)
  const error = ref<string | null>(null)
  const polling = ref(false)
  const retryCount = ref(0)
  const editing = ref(false)
  const messages = ref<PlanMessage[]>([])
  const versions = ref<PlanVersionSummary[]>([])
  const lastRunError = ref<string | null>(null)
  let pollTimer: number | null = null

  async function create(userInput: string, durationDays: number, totalBudget: number, profileId: number = 1) {
    const res = await planApi.createPlan({
      profile_id: profileId,
      user_input: userInput,
      duration_days: durationDays,
      total_budget: totalBudget,
    })
    planId.value = res.plan_id
    status.value = 'pending'
    result.value = null
    error.value = null
    lastRunError.value = null
    editing.value = false
    retryCount.value = 0
    startPolling()
    return res
  }

  function startPolling() {
    if (polling.value) return
    polling.value = true
    error.value = null
    poll()
  }

  function stopPolling() {
    polling.value = false
    if (pollTimer !== null) {
      window.clearTimeout(pollTimer)
      pollTimer = null
    }
  }

  function schedulePoll(delay = 2000) {
    if (!polling.value) return
    if (pollTimer !== null) window.clearTimeout(pollTimer)
    pollTimer = window.setTimeout(() => {
      pollTimer = null
      poll()
    }, delay)
  }

  async function poll() {
    if (!planId.value || !polling.value) return

    try {
      const statusRes = await planApi.getPlanStatus(planId.value)
      status.value = statusRes.status
      progress.value = statusRes.progress
      error.value = statusRes.error || statusRes.last_error
      lastRunError.value = statusRes.last_error
      retryCount.value = 0

      if (status.value === 'completed') {
        polling.value = false
        editing.value = false
        const resultRes = await planApi.getPlanResult(planId.value)
        result.value = resultRes.result
        await loadConversation()
        return
      }

      if (status.value === 'failed') {
        polling.value = false
        editing.value = false
        error.value = statusRes.error || '规划生成失败'
        return
      }

      // 继续轮询
      schedulePoll()
    } catch (e: any) {
      retryCount.value += 1
      error.value = e.message || '暂时无法获取生成进度'
      if (retryCount.value <= 3 && polling.value) {
        schedulePoll(Math.min(2000 * retryCount.value, 6000))
      } else {
        polling.value = false
        status.value = 'failed'
      }
    }
  }

  async function retry() {
    if (!planId.value) return
    await planApi.retryPlan(planId.value)
    retryCount.value = 0
    status.value = 'pending'
    error.value = null
    lastRunError.value = null
    startPolling()
  }

  async function sendMessage(message: string, action?: Record<string, any>) {
    if (!planId.value) throw new Error('方案不存在')
    await planApi.sendPlanMessage(planId.value, {
      message,
      action,
      client_request_id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    })
    editing.value = true
    error.value = null
    startPolling()
  }

  async function loadConversation() {
    if (!planId.value) return
    const [messageItems, versionResponse] = await Promise.all([
      planApi.getPlanMessages(planId.value),
      planApi.getPlanVersions(planId.value),
    ])
    messages.value = messageItems
    versions.value = versionResponse.items
  }

  async function restoreVersion(versionId: number) {
    if (!planId.value) return
    await planApi.restorePlanVersion(planId.value, versionId)
    const resultRes = await planApi.getPlanResult(planId.value)
    result.value = resultRes.result
    await loadConversation()
  }

  function reset() {
    planId.value = null
    status.value = 'pending'
    progress.value = null
    result.value = null
    error.value = null
    editing.value = false
    messages.value = []
    versions.value = []
    lastRunError.value = null
    stopPolling()
    retryCount.value = 0
  }

  return {
    planId, status, progress, result, error, polling, retryCount, editing,
    messages, versions, lastRunError, create, startPolling, stopPolling,
    sendMessage, loadConversation, restoreVersion, retry, reset,
  }
})
