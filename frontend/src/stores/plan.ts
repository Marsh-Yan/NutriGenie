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
      error.value = statusRes.error
      retryCount.value = 0

      if (status.value === 'completed') {
        polling.value = false
        const resultRes = await planApi.getPlanResult(planId.value)
        result.value = resultRes.result
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
    startPolling()
  }

  function reset() {
    planId.value = null
    status.value = 'pending'
    progress.value = null
    result.value = null
    error.value = null
    stopPolling()
    retryCount.value = 0
  }

  return { planId, status, progress, result, error, polling, retryCount, create, startPolling, stopPolling, retry, reset }
})
