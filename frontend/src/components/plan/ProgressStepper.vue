<script setup lang="ts">
import type { ProgressInfo, PlanStatus } from '@/types'
import { Check } from '@element-plus/icons-vue'

const props = defineProps<{
  status: PlanStatus
  progress: ProgressInfo | null
}>()

const stepLabels = ['意图分析', '约束分析', '混合推荐', '计划聚合', '结果校验', '生成总结']
</script>

<template>
  <div class="progress-stepper" aria-live="polite" aria-label="规划生成进度">
    <div class="status-header">
      <div v-if="status === 'pending'" class="status-badge pending">等待中</div>
      <div v-else-if="status === 'running'" class="status-badge running">
        <span class="running-dot" />
        规划中
      </div>
      <div v-else-if="status === 'completed'" class="status-badge completed">
        <el-icon><Check /></el-icon>
        已完成
      </div>
      <div v-else class="status-badge failed">失败</div>

      <span v-if="progress" class="step-hint">
        第 {{ progress.current_step }} / {{ progress.total_steps }} 步
      </span>
    </div>

    <div class="steps-bar">
      <div
        v-for="(label, i) in stepLabels"
        :key="i"
        class="step-dot-wrap"
        :class="{
          done: progress && progress.completed_steps > i,
          active: progress && progress.current_step === i + 1,
        }"
      >
        <div class="step-dot">
          <el-icon v-if="progress && progress.completed_steps > i"><Check /></el-icon>
          <span v-else-if="progress && progress.current_step === i + 1" class="dot-pulse" />
          <span v-else class="dot-empty" />
        </div>
        <span class="step-name">{{ label }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.progress-stepper {
  margin-bottom: 32px;
}

.status-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;

  &.pending {
    background: rgba($color-warning, 0.12);
    color: $color-warning;
  }

  &.running {
    background: rgba($color-info, 0.12);
    color: $color-info;
  }

  &.completed {
    background: rgba($color-success, 0.12);
    color: $color-success;
  }

  &.failed {
    background: rgba($color-danger, 0.12);
    color: $color-danger;
  }
}

.running-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: $color-info;
  animation: blink 1s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.step-hint {
  font-size: 13px;
  color: $color-text-secondary;
}

.steps-bar {
  display: flex;
  gap: 0;
  position: relative;

  @media (max-width: $breakpoint-sm) {
    overflow-x: auto;
    padding-bottom: 8px;
  }
}

.step-dot-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex: 1;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    top: 10px;
    left: -50%;
    right: 50%;
    height: 2px;
    background: $color-border;
    transition: background 0.3s;
  }

  &:first-child::before { display: none; }

  &.done::before {
    background: $color-sage-light;
  }

  &.active::before {
    background: $color-sage-light;
  }
}

.step-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  position: relative;
  z-index: 1;
  transition: all 0.3s;

  .done & {
    background: $color-sage;
    color: #fff;
  }

  .active & {
    background: $color-sage-light;
  }

  .done &, .active & {
    border: 2px solid $color-sage;
  }
}

.dot-empty {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: $color-border;
}

.dot-pulse {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: $color-sage;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.3); opacity: 0.6; }
}

.step-name {
  font-size: 11px;
  color: $color-text-placeholder;
  white-space: nowrap;

  .done & { color: $color-sage; }
  .active & { color: $color-text-primary; font-weight: 500; }
}
</style>
