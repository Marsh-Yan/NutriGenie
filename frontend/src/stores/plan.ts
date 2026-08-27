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
  const resultLoading = ref(false)
  const draftInput = ref('')
  const draftDurationDays = ref(7)
  const draftTotalBudget = ref<number | null>(300)
  const draftExampleIndex = ref(-1)
  const editing = ref(false)
  const messages = ref<PlanMessage[]>([])
  const versions = ref<PlanVersionSummary[]>([])
  const lastRunError = ref<string | null>(null)
  let pollTimer: number | null = null
  let pollStartedAt = 0
  let resultFetchAttempts = 0
  const MAX_POLL_MS = 5 * 60 * 1000
  const MAX_RESULT_FETCH_ATTEMPTS = 10

  async function create(userInput: string, durationDays: number, totalBudget: number, profileId: number = 1) {
    stopPolling()
    const res = await planApi.createPlan({
      profile_id: profileId,
      user_input: userInput,
      duration_days: durationDays,
      total_budget: totalBudget,
    })
    planId.value = res.plan_id
    status.value = 'pending'
    result.value = null
    progress.value = null
    error.value = null
    lastRunError.value = null
    editing.value = false
    messages.value = []
    versions.value = []
    retryCount.value = 0
    resultLoading.value = false
    resultFetchAttempts = 0
    pollStartedAt = Date.now()
    startPolling()
    return res
  }

  function startPolling() {
    if (polling.value) return
    polling.value = true
    if (!pollStartedAt) pollStartedAt = Date.now()
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

  function schedulePoll(delay = 1000) {
    if (!polling.value) return
    if (pollTimer !== null) window.clearTimeout(pollTimer)
    pollTimer = window.setTimeout(() => {
      pollTimer = null
      poll()
    }, delay)
  }

  async function poll() {
    if (!planId.value || !polling.value) return
    const requestedPlanId = planId.value

    if (Date.now() - pollStartedAt > MAX_POLL_MS) {
      polling.value = false
      status.value = 'failed'
      error.value = '生成时间超过 5 分钟，请稍后继续获取或重新规划'
      return
    }

    try {
      const statusRes = await planApi.getPlanStatus(requestedPlanId)
      if (planId.value !== requestedPlanId) return
      status.value = statusRes.status
      progress.value = statusRes.progress
      error.value = statusRes.error || statusRes.last_error
      lastRunError.value = statusRes.last_error
      retryCount.value = 0

      if (status.value === 'completed') {
        editing.value = false
        resultLoading.value = true
        try {
          const resultRes = await planApi.getPlanResult(requestedPlanId)
          if (planId.value !== requestedPlanId) return
          if (resultRes.result) {
            result.value = resultRes.result
            error.value = null
            resultFetchAttempts = 0
            stopPolling()
            try {
              await loadConversation()
            } catch {
              // Conversation history is supplementary to the generated plan.
            }
            return
          }
          resultFetchAttempts += 1
          error.value = '方案已完成，结果正在同步，请稍候'
        } catch (e: any) {
          resultFetchAttempts += 1
          error.value = e.message || '结果加载失败，正在自动重试'
        } finally {
          resultLoading.value = false
        }
        if (resultFetchAttempts >= MAX_RESULT_FETCH_ATTEMPTS) {
          stopPolling()
          error.value = '方案已经生成，但结果加载失败，请点击“继续获取结果”'
        } else {
          schedulePoll(Math.min(600 * resultFetchAttempts, 3000))
        }
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
        schedulePoll(Math.min(1500 * retryCount.value, 6000))
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
    resultFetchAttempts = 0
    status.value = 'pending'
    error.value = null
    lastRunError.value = null
    pollStartedAt = Date.now()
    startPolling()
  }

  function refreshResult() {
    if (!planId.value) return
    retryCount.value = 0
    resultFetchAttempts = 0
    error.value = null
    pollStartedAt = Date.now()
    startPolling()
  }

  function load(id: number) {
    stopPolling()
    planId.value = id
    status.value = 'pending'
    progress.value = null
    result.value = null
    error.value = null
    lastRunError.value = null
    resultLoading.value = false
    messages.value = []
    versions.value = []
    resultFetchAttempts = 0
    editing.value = false
    retryCount.value = 0
    pollStartedAt = Date.now()
    startPolling()
  }

  function clearDraft() {
    draftInput.value = ''
    draftDurationDays.value = 7
    draftTotalBudget.value = 300
    draftExampleIndex.value = -1
  }

  async function sendMessage(message: string, action?: Record<string, any>) {
    if (!planId.value) throw new Error('方案不存在')
    await planApi.sendPlanMessage(planId.value, {
      message,
      action,
      client_request_id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    })
    editing.value = true
    status.value = 'pending'
    error.value = null
    lastRunError.value = null
    resultFetchAttempts = 0
    pollStartedAt = Date.now()
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
    resultLoading.value = false
    resultFetchAttempts = 0
    pollStartedAt = 0
  }

  return {
    planId, status, progress, result, error, polling, retryCount, resultLoading,
    draftInput, draftDurationDays, draftTotalBudget, draftExampleIndex,
    editing, messages, versions, lastRunError,
    create, load, startPolling, stopPolling, sendMessage, loadConversation,
    restoreVersion, retry, refreshResult, reset, clearDraft,
  }
})
