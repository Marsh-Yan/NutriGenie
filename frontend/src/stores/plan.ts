import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { PlanResult, PlanStatus, ProgressInfo } from '@/types'
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
  let pollTimer: number | null = null
  let pollStartedAt = 0
  const MAX_POLL_MS = 5 * 60 * 1000

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
    retryCount.value = 0
    resultLoading.value = false
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
      error.value = statusRes.error
      retryCount.value = 0

      if (status.value === 'completed') {
        polling.value = false
        resultLoading.value = true
        try {
          for (let attempt = 1; attempt <= 3; attempt++) {
            const resultRes = await planApi.getPlanResult(requestedPlanId)
            if (planId.value !== requestedPlanId) return
            if (resultRes.result) {
              result.value = resultRes.result
              error.value = null
              return
            }
            if (attempt < 3) await new Promise(resolve => window.setTimeout(resolve, 500 * attempt))
          }
          throw new Error('结果暂时未就绪，请继续获取')
        } finally {
          resultLoading.value = false
        }
        return
      }

      if (status.value === 'failed') {
        polling.value = false
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

  function retry() {
    retryCount.value = 0
    status.value = 'pending'
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
    resultLoading.value = false
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

  function reset() {
    planId.value = null
    status.value = 'pending'
    progress.value = null
    result.value = null
    error.value = null
    stopPolling()
    retryCount.value = 0
    resultLoading.value = false
    pollStartedAt = 0
  }

  return {
    planId, status, progress, result, error, polling, retryCount, resultLoading,
    draftInput, draftDurationDays, draftTotalBudget, draftExampleIndex,
    create, load, startPolling, stopPolling, retry, reset, clearDraft,
  }
})
