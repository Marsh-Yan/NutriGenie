<script setup lang="ts">
import { computed } from 'vue'
import type { GenerationMeta, PlanValidation } from '@/types'
import PremiumIcon from '@/components/common/PremiumIcon.vue'

const props = defineProps<{
  meta: GenerationMeta
  validation: PlanValidation
}>()

const ragSources = computed(() => props.meta.rag_sources || [])
const unresolvedIngredients = computed(() => props.meta.unresolved_ingredients || [])
const validationWarnings = computed(() => props.validation.warnings || [])
const sourceLabels: Record<string, string> = {
  ingredient_catalog_v1: '标准食材目录核算',
  legacy_estimate: '历史方案估算',
}
const estimateLabel = computed(() => {
  const nutrition = props.meta.nutrition_source || props.meta.estimate_source
  const cost = props.meta.cost_source || props.meta.estimate_source
  const label = (source: string) => sourceLabels[source] || '来源未记录'
  return nutrition === cost ? label(nutrition) : `营养：${label(nutrition)}；成本：${label(cost)}`
})

const strategyLabel = computed(() => {
  const labels: Record<string, string> = {
    hybrid_rag_v1: '结构化筛选 + 语义重排',
    legacy_database_recommendation: '数据库确定性推荐',
    ai_native_v2: 'AI 创作 + 程序校验',
  }
  return labels[props.meta.strategy] || props.meta.strategy || '未记录'
})

const ragState = computed(() => {
  if (!props.meta.rag_enabled) return { label: '未启用知识库检索', tone: 'neutral' }
  if (props.meta.rag_used) return { label: '已参考知识库', tone: 'success' }
  if (props.meta.fallback_used || props.meta.rag_error) return { label: '知识库不可用，已安全降级', tone: 'warning' }
  return { label: '本次未使用知识库', tone: 'neutral' }
})

const validationLabel = computed(() => {
  if (props.validation.status === 'failed') return '存在未通过的硬约束'
  if (validationWarnings.value.length) return `${validationWarnings.value.length} 条可执行提醒`
  return '计划校验已通过'
})
</script>

<template>
  <section class="evidence-card card" aria-labelledby="evidence-title">
    <header class="evidence-heading">
      <div>
        <span class="eyebrow">推荐依据</span>
        <h2 id="evidence-title"><PremiumIcon name="clipboard" :size="17" :box-size="32" />这份计划如何得出</h2>
      </div>
      <span class="rag-state" :class="ragState.tone">{{ ragState.label }}</span>
    </header>

    <div class="evidence-grid">
      <div><span>生成策略</span><strong>{{ strategyLabel }}</strong></div>
      <div><span>候选菜谱</span><strong>{{ meta.candidate_count || '未记录' }}</strong></div>
      <div><span>营养与成本依据</span><strong>{{ estimateLabel }}</strong></div>
      <div><span>确定性校验</span><strong>{{ validationLabel }}</strong></div>
    </div>

    <details v-if="ragSources.length || unresolvedIngredients.length || meta.rag_error" class="evidence-details">
      <summary>查看技术记录</summary>
      <div v-if="ragSources.length" class="source-list">
        <p v-for="source in ragSources.slice(0, 5)" :key="source.chunk_id">
          <strong>{{ source.section_title || source.source_file || '知识库片段' }}</strong>
          <span>匹配度 {{ Math.round(source.score * 100) }}%</span>
        </p>
      </div>
      <p v-if="unresolvedIngredients.length" class="technical-note">
        尚未匹配到标准目录的食材：{{ unresolvedIngredients.join('、') }}
      </p>
      <p v-if="meta.rag_error" class="technical-note">知识库降级原因：{{ meta.rag_error }}</p>
    </details>

    <p class="evidence-disclaimer">推荐依据用于解释方案生成过程，不代表模型已“学习”你的本地偏好；过敏原、营养和预算校验仍优先执行。</p>
  </section>
</template>

<style scoped lang="scss">
.evidence-card { margin-bottom: 20px; padding: clamp(20px, 3vw, 28px); box-shadow: none; }
.evidence-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; }
.evidence-heading h2 { display: flex; align-items: center; gap: 9px; margin-top: 7px; font-size: 21px; letter-spacing: -.025em; }
.evidence-heading :deep(.premium-icon) { border-radius: 9px; box-shadow: none; }
.rag-state { flex: 0 0 auto; padding: 7px 11px; border: 1px solid $color-border; border-radius: $radius-round; background: $color-surface-soft; color: $color-text-secondary; font-size: 13px; font-weight: 750; }
.rag-state.success { border-color: rgba($color-success, .22); background: rgba($color-success, .09); color: $color-success; }
.rag-state.warning { border-color: rgba($color-warning, .25); background: rgba($color-warning, .1); color: $color-warning; }
.evidence-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 9px; margin-top: 20px; }
.evidence-grid > div { display: grid; align-content: start; gap: 5px; min-height: 84px; padding: 14px; border-radius: $radius-sm; background: $color-surface-soft; }
.evidence-grid span { color: $color-text-secondary; font-size: 12px; font-weight: 680; }
.evidence-grid strong { color: $color-text-primary; font-size: 14px; line-height: 1.45; overflow-wrap: anywhere; }
.evidence-details { margin-top: 16px; padding-top: 14px; border-top: 1px solid $color-divider; }
.evidence-details summary { min-height: 44px; color: $color-sage-dark; cursor: pointer; font-size: 14px; font-weight: 750; }
.source-list { display: grid; gap: 7px; }
.source-list p { display: flex; justify-content: space-between; gap: 16px; padding: 10px 12px; border-radius: $radius-xs; background: $color-surface-soft; font-size: 13px; }
.source-list span { flex: 0 0 auto; color: $color-text-secondary; }
.technical-note { margin-top: 9px; color: $color-text-secondary; font-size: 13px; line-height: 1.65; }
.evidence-disclaimer { margin-top: 16px; color: $color-text-secondary; font-size: 13px; line-height: 1.65; }

@media (max-width: $breakpoint-md) {
  .evidence-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: $breakpoint-sm) {
  .evidence-heading { align-items: flex-start; flex-direction: column; }
  .evidence-grid { grid-template-columns: 1fr; }
  .evidence-grid > div { min-height: auto; }
  .source-list p { align-items: flex-start; flex-direction: column; gap: 3px; }
}
</style>
