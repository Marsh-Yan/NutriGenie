<script setup lang="ts">
import { computed } from 'vue'
import type { ProgressInfo, PlanStatus } from '@/types'
import { Check } from '@element-plus/icons-vue'

const props = defineProps<{
  status: PlanStatus
  progress: ProgressInfo | null
}>()

const fallbackLabels = ['意图分析', '约束构建', '食材知识', 'AI 创作候选', '食材标准化', '硬约束校验', '整周优化', '结果校验与汇总', '保存方案版本']
const descriptionByLabel: Record<string, string> = {
  意图分析: '理解目标',
  约束构建: '计算边界',
  食材知识: '准备事实',
  'AI 创作候选': '创作菜品',
  食材标准化: '重新核算',
  硬约束校验: '检查安全',
  整周优化: '控制重复',
  结果校验与汇总: '汇总结果',
  保存方案版本: '整理结果',
}
const stepLabels = computed(() => props.progress?.steps?.length
  ? props.progress.steps.map(step => step.name)
  : fallbackLabels)

const activeStep = computed(() => {
  if (props.status === 'completed') return stepLabels.value.length
  return props.progress?.current_step || (props.status === 'pending' ? 0 : 1)
})

const progressPercent = computed(() => {
  if (props.status === 'completed') return 100
  if (props.status === 'pending') return 4
  const completed = props.progress?.completed_steps ?? Math.max(activeStep.value - 1, 0)
  return Math.min(96, Math.max(8, Math.round(((completed + 0.42) / stepLabels.value.length) * 100)))
})
</script>

<template>
  <div class="progress-stepper" aria-live="polite" aria-label="规划生成进度">
    <div class="status-header">
      <div class="status-copy">
        <div v-if="status === 'pending'" class="status-badge pending">正在准备</div>
        <div v-else-if="status === 'running'" class="status-badge running">
          <span class="running-dot" />
          AI 工作流运行中
        </div>
        <div v-else-if="status === 'completed'" class="status-badge completed">
          <el-icon><Check /></el-icon>
          方案已完成
        </div>
        <div v-else class="status-badge failed">生成中断</div>

        <span class="step-hint">
          {{ activeStep ? `第 ${activeStep} / ${stepLabels.length} 步` : '即将开始' }}
        </span>
      </div>
      <strong class="progress-value">{{ progressPercent }}%</strong>
    </div>

    <div
      class="progress-track"
      role="progressbar"
      :aria-valuenow="progressPercent"
      :aria-valuetext="`${progressPercent}%`"
      aria-valuemin="0"
      aria-valuemax="100"
    >
      <div class="progress-fill" :style="{ width: `${progressPercent}%` }">
        <span aria-hidden="true" />
      </div>
    </div>

    <div class="steps-grid" role="list">
      <div
        v-for="(label, i) in stepLabels"
        :key="label"
        class="step-item"
        role="listitem"
        :aria-current="activeStep === i + 1 && progressPercent < 100 ? 'step' : undefined"
        :class="{
          done: progressPercent === 100 || activeStep > i + 1,
          active: activeStep === i + 1 && progressPercent < 100,
        }"
      >
        <div class="step-index">
          <el-icon v-if="progressPercent === 100 || activeStep > i + 1"><Check /></el-icon>
          <span v-else>{{ String(i + 1).padStart(2, '0') }}</span>
        </div>
        <div class="step-text">
          <strong>{{ label }}</strong>
          <span>{{ descriptionByLabel[label] || '处理中' }}</span>
        </div>
        <span v-if="activeStep === i + 1 && progressPercent < 100" class="active-wave" aria-hidden="true" />
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.progress-stepper {
  width: 100%;
  padding: clamp(18px, 3vw, 26px);
  border: 1px solid rgba($color-sage-dark, .11);
  border-radius: $radius-lg;
  background:
    radial-gradient(circle at 100% 0, rgba($color-lime, .18), transparent 15rem),
    rgba($color-card, .9);
  box-shadow: $shadow-sm;
}

.status-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 14px;
}

.status-copy {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 7px 12px;
  border: 1px solid transparent;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 750;

  &.pending {
    background: rgba($color-warning, 0.12);
    border-color: rgba($color-warning, .16);
    color: $color-warning;
  }

  &.running {
    background: rgba($color-sage, .1);
    border-color: rgba($color-sage, .18);
    color: $color-sage-dark;
  }

  &.completed {
    background: rgba($color-success, 0.12);
    border-color: rgba($color-success, .16);
    color: $color-success;
  }

  &.failed {
    background: rgba($color-danger, 0.12);
    border-color: rgba($color-danger, .16);
    color: $color-danger;
  }
}

.running-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: $color-sage;
  box-shadow: 0 0 0 4px rgba($color-sage, .12);
  animation: blink 1s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.step-hint {
  font-size: 13px;
  font-weight: 600;
  color: $color-text-secondary;
}

.progress-value {
  color: $color-sage-dark;
  font-size: 24px;
  font-variant-numeric: tabular-nums;
  letter-spacing: -.04em;
}

.progress-track {
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  border: 1px solid rgba($color-sage-dark, .06);
  background: rgba($color-sage, .1);
  box-shadow: inset 0 1px 2px rgba(63, 98, 80, .08);
}

.progress-fill {
  position: relative;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, $color-sage-dark, $color-sage 70%, $color-lime);
  box-shadow: 0 0 16px rgba($color-sage, .32);
  transition: width .6s cubic-bezier(.2, .8, .2, 1);

  span {
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,.48), transparent);
    transform: translateX(-100%);
    animation: sweep 2.2s ease-in-out infinite;
  }
}

@keyframes sweep {
  70%, 100% { transform: translateX(100%); }
}

.steps-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 20px;

  @media (max-width: $breakpoint-sm) {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.step-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 74px;
  padding: 13px;
  overflow: hidden;
  border: 1px solid rgba($color-border, .82);
  border-radius: $radius-sm;
  background: rgba($color-card, .74);
  transition: border-color .3s, background .3s, transform .3s;

  &.done { border-color: rgba($color-sage, .2); background: rgba($color-sage, .06); }
  &.active { border-color: rgba($color-sage, .46); background: linear-gradient(145deg, rgba($color-sage-light, .6), rgba($color-lime-soft, .46)); transform: translateY(-2px); box-shadow: 0 10px 22px rgba($color-sage-dark,.09); }
}

.step-index {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  border-radius: 10px;
  background: $color-divider;
  color: $color-text-placeholder;
  font-size: 12px;
  font-weight: 800;

  .done & { background: $color-sage-dark; color: #fff; }
  .active & { background: $color-sage; color: #fff; }
}

.step-text {
  display: grid;
  gap: 3px;
  min-width: 0;

  strong { color: $color-text-primary; font-size: 13px; font-weight: 720; line-height: 1.4; }
  span { color: $color-text-secondary; font-size: 12px; font-weight: 550; line-height: 1.45; }
  .done & strong, .active & strong { color: $color-text-primary; }
}

.active-wave {
  position: absolute;
  right: -12px;
  bottom: -14px;
  width: 34px;
  height: 34px;
  border: 1px solid rgba($color-sage, .22);
  border-radius: 50%;
  animation: wave 1.8s ease-out infinite;
}

@keyframes wave {
  from { transform: scale(.5); opacity: .8; }
  to { transform: scale(1.35); opacity: 0; }
}

@media (max-width: $breakpoint-sm) {
  .status-header { align-items: flex-start; }
  .status-copy { align-items: flex-start; flex-direction: column; gap: 6px; }
  .progress-value { font-size: 20px; }
  .step-item { min-height: 70px; padding: 12px; }
  .step-text strong { font-size: 13px; }
  .step-text span { font-size: 12px; }
}

@media (max-width: 420px) {
  .progress-stepper { padding: 16px; }
  .steps-grid { grid-template-columns: 1fr; }
  .step-item { min-height: 66px; }
}
</style>
