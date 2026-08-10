<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { usePlanStore } from '@/stores/plan'
import RecipeCard from '@/components/recipe/RecipeCard.vue'
import WeeklyTimeline from '@/components/plan/WeeklyTimeline.vue'
import NutritionReport from '@/components/plan/NutritionReport.vue'
import ShoppingList from '@/components/plan/ShoppingList.vue'
import { Refresh } from '@element-plus/icons-vue'
import PremiumIcon from '@/components/common/PremiumIcon.vue'

const route = useRoute()
const store = usePlanStore()
const messageInput = ref('')
const ingredientInput = ref('')
const sendingMessage = ref(false)
const showVersions = ref(false)

const overview = computed(() => {
  const result = store.result
  if (!result) return null
  return {
    calories: result.nutrition_report.avg_daily_calories,
    cost: result.shopping_list.total_cost,
    recipes: result.recipes.length,
    warnings: result.validation?.warnings.length || 0,
  }
})

const currentError = computed(() => store.lastRunError || store.error)

onMounted(async () => {
  const planId = Number(route.params.id)
  if (planId) {
    store.planId = planId
    store.status = 'pending'
    store.startPolling()
    try {
      await store.loadConversation()
    } catch {
      // Conversation history is supplementary; the plan result remains usable.
    }
  }
})

onUnmounted(() => store.stopPolling())

watch(() => store.status, (status) => {
  if (status === 'completed' || status === 'failed') {
    store.stopPolling()
  }
})

async function submitMessage(action?: Record<string, any>) {
  const message = messageInput.value.trim()
  if (!message && !action) return
  sendingMessage.value = true
  try {
    await store.sendMessage(message, action)
    messageInput.value = ''
    await store.loadConversation()
  } catch (error: any) {
    store.error = error?.message || '修改方案失败'
  } finally {
    sendingMessage.value = false
  }
}

async function removeIngredient() {
  const ingredient = ingredientInput.value.trim()
  if (!ingredient) return
  await submitMessage({ type: 'remove_ingredient', ingredient })
  ingredientInput.value = ''
}

async function restoreVersion(versionId: number) {
  try {
    await store.restoreVersion(versionId)
    showVersions.value = false
  } catch (error: any) {
    store.error = error?.message || '恢复版本失败'
  }
}
</script>

<template>
  <div class="plan-result-page page-container">

    <!-- 首次生成等待状态 -->
    <div v-if="(store.status === 'pending' || store.status === 'running') && !store.result" class="loading-section">
      <div class="loading-card card">
        <div class="loading-animation">
          <div class="loading-ring" />
          <PremiumIcon name="thinking" class="loading-icon" :size="34" :box-size="68" />
        </div>
        <h2 class="loading-title">AI 正在为你规划...</h2>
        <p class="loading-desc">
          {{ store.status === 'pending' ? '等待中，即将开始' : '正在生成并校验 AI 餐单...' }}
        </p>
      </div>
    </div>

    <!-- 编辑已有方案时保留旧版本 -->
    <div v-if="store.status === 'running' && store.result" class="generation-banner card">
      <PremiumIcon name="thinking" :size="18" :box-size="34" />
      <span>正在基于当前方案生成新版本，旧版本仍然可用。</span>
    </div>

    <!-- 无历史版本时的失败状态 -->
    <div v-if="store.status === 'failed' && !store.result" class="error-section">
      <div class="error-card card">
        <PremiumIcon name="alert" class="error-icon" :size="36" :box-size="72" />
        <h2 class="error-title">规划生成失败</h2>
        <p class="error-desc">{{ currentError || '请重试' }}</p>
        <el-button type="primary" round @click="$router.push('/plan/new')">
          <el-icon><Refresh /></el-icon>
          重新尝试
        </el-button>
        <el-button round @click="store.retry()">继续获取结果</el-button>
      </div>
    </div>

    <!-- 结果页面：成功、带警告或编辑失败时继续展示当前版本 -->
    <div v-if="store.result" class="result-section">
      <section v-if="overview" class="overview-card card" aria-labelledby="overview-title">
        <div class="overview-heading">
          <div><span class="eyebrow">你的专属方案</span><h1 id="overview-title">本周饮食概览</h1></div>
          <el-tag :type="overview.warnings ? 'warning' : 'success'" effect="light">
            {{ overview.warnings ? `${overview.warnings} 条提醒` : '整体匹配良好' }}
          </el-tag>
        </div>
        <div class="overview-grid">
          <div><strong>{{ overview.calories.toFixed(0) }}</strong><span>日均 kcal</span></div>
          <div><strong>{{ overview.cost == null ? '—' : `¥${overview.cost.toFixed(0)}` }}</strong><span>预计采购</span></div>
          <div><strong>{{ overview.recipes }}</strong><span>AI 生成菜谱</span></div>
        </div>
      </section>
      <section class="recommendation-status card">
        <details>
          <summary>查看 AI 生成依据</summary>
          <p>菜谱由大模型生成，程序对硬性限制、营养汇总和预算进行校验。</p>
          <el-tag :type="store.result.generation_meta.rag_used ? 'success' : 'info'" effect="light">
            {{ store.result.generation_meta.rag_used ? '已参考知识库' : '纯 AI 生成' }}
          </el-tag>
          <el-tag type="warning" effect="light">营养与预算为 AI 估算</el-tag>
        </details>
      </section>
      <!-- AI 生成菜谱 -->
      <section class="result-block">
        <h2 class="block-title">
          <PremiumIcon name="trophy" class="heading-icon" :size="18" :box-size="34" />
          AI 生成菜谱
          <span class="block-subtitle">根据你的约束即时生成</span>
        </h2>
        <div class="top5-list">
          <RecipeCard
            v-for="(recipe, i) in store.result.recipes"
            :key="recipe.recipe_key"
            :recipe="recipe"
            :rank="i + 1"
          />
        </div>
      </section>

      <!-- 周计划 -->
      <section v-if="store.result.weekly_plan.length > 0" class="result-block">
        <WeeklyTimeline :weekly-plan="store.result.weekly_plan" />
      </section>

      <section v-if="store.result.validation" class="result-block">
        <div class="validation-card card" :class="{ warning: store.result.validation.warnings.length }">
          <h3 class="validation-heading"><PremiumIcon name="check" :size="13" :box-size="26" />计划校验</h3>
          <p>日均 {{ (store.result.validation.derived.avg_daily_calories || store.result.nutrition_report.avg_daily_calories).toFixed(0) }} kcal</p>
          <p>预计采购 ¥{{ store.result.shopping_list.total_cost.toFixed(1) }}</p>
          <p v-for="warning in store.result.validation.warnings" :key="warning" class="validation-warning">
            <PremiumIcon name="alert" :size="12" :box-size="24" />{{ warning }}
          </p>
          <p v-if="!store.result.validation.warnings.length" class="validation-ok">计划完整，未发现需要提示的偏差。</p>
        </div>
      </section>

      <!-- 营养报告 -->
      <section class="result-block">
        <NutritionReport :report="store.result.nutrition_report" />
      </section>

      <!-- 采购清单 -->
      <section class="result-block">
        <ShoppingList :shopping-list="store.result.shopping_list" />
      </section>

      <!-- AI 总结 -->
      <section v-if="store.result.summary" class="result-block">
        <div class="summary-card card">
          <h3 class="summary-title">
            <PremiumIcon name="clipboard" class="heading-icon" :size="17" :box-size="32" />
            AI 总结
          </h3>
          <div class="summary-content">{{ store.result.summary }}</div>
        </div>
      </section>

      <section v-if="currentError && store.result" class="edit-error card">
        <PremiumIcon name="alert" :size="16" :box-size="30" />
        <span>本次修改没有生成新版本，当前仍显示上一个成功版本：{{ currentError }}</span>
      </section>

      <section class="conversation-card card">
        <div class="conversation-heading">
          <div>
            <span class="eyebrow">继续调整</span>
            <h2>和 AI 一起修改方案</h2>
          </div>
          <el-button link @click="showVersions = !showVersions">版本历史（{{ store.versions.length }}）</el-button>
        </div>
        <div class="quick-actions">
          <el-button size="small" round :disabled="store.editing" @click="submitMessage({ type: 'reduce_budget' })">降低预算</el-button>
          <el-button size="small" round :disabled="store.editing" @click="submitMessage({ type: 'increase_protein' })">增加蛋白质</el-button>
          <el-button size="small" round :disabled="store.editing" @click="submitMessage({ type: 'shorter_cooking' })">缩短烹饪时间</el-button>
          <el-button size="small" round :disabled="store.editing" @click="submitMessage({ type: 'replace_meal', day: 1, slot: 'lunch' })">重做第 1 天午餐</el-button>
          <el-button size="small" round :disabled="store.editing" @click="submitMessage({ type: 'replace_day', day: 1 })">重做第 1 天</el-button>
        </div>
        <div class="remove-ingredient-row">
          <el-input v-model="ingredientInput" size="small" placeholder="输入要去除的食材，例如：花生" :disabled="store.editing" @keydown.enter="removeIngredient" />
          <el-button size="small" round :disabled="!ingredientInput.trim() || store.editing" @click="removeIngredient">去除食材</el-button>
        </div>
        <div class="conversation-input">
          <el-input
            v-model="messageInput"
            type="textarea"
            :rows="3"
            maxlength="1000"
            show-word-limit
            :disabled="store.editing"
            placeholder="例如：把第三天晚餐换成不含海鲜、20 分钟内完成的菜"
            @keydown.ctrl.enter="submitMessage()"
          />
          <el-button type="primary" round :loading="sendingMessage || store.editing" :disabled="!messageInput.trim() || store.editing" @click="submitMessage()">生成新版本</el-button>
        </div>
        <div v-if="showVersions" class="version-list">
          <div v-for="version in store.versions" :key="version.version_id" class="version-row">
            <span>版本 {{ version.version_no }} · {{ new Date(version.created_at).toLocaleString() }}</span>
            <el-tag v-if="version.is_current" size="small" type="success">当前</el-tag>
            <el-button v-else size="small" link @click="restoreVersion(version.version_id)">恢复</el-button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped lang="scss">
.plan-result-page {
  padding: 32px 20px;
  max-width: 800px;
}

// ── 加载状态 ─────────────────────────────

.loading-section {
  padding-top: 40px;
}

.loading-card {
  text-align: center;
  padding: 60px 40px;
}

.loading-animation {
  position: relative;
  width: 80px;
  height: 80px;
  margin: 0 auto 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-ring {
  position: absolute;
  inset: 0;
  border: 3px solid $color-divider;
  border-top-color: $color-sage;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-icon {
  position: relative;
  z-index: 1;
}

.loading-title {
  font-size: 20px;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 8px;
}

.loading-desc {
  font-size: 14px;
  color: $color-text-secondary;
}

// ── 错误状态 ─────────────────────────────

.error-section {
  padding-top: 60px;
}

.error-card {
  text-align: center;
  padding: 60px 40px;
}

.error-icon {
  display: inline-grid;
  margin-bottom: 16px;
}

.error-title {
  font-size: 20px;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 8px;
}

.error-desc {
  font-size: 14px;
  color: $color-text-secondary;
  margin-bottom: 24px;
}

// ── 结果状态 ─────────────────────────────

.result-section {
  padding-top: 8px;
}

.overview-card { margin-bottom: 24px; padding: 28px; background: linear-gradient(135deg, rgba($color-sage,.14), rgba($color-rose,.09)); }
.overview-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.overview-heading h1 { margin-top: 4px; color: $color-text-primary; font-size: 26px; }
.eyebrow { color: $color-sage-dark; font-size: 13px; font-weight: 700; letter-spacing: .08em; }
.overview-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; margin-top: 22px; }
.overview-grid div { display: flex; flex-direction: column; padding: 14px; border-radius: $radius-md; background: rgba(255,255,255,.72); }
.overview-grid strong { color: $color-text-primary; font-size: 22px; }
.overview-grid span { color: $color-text-secondary; font-size: 12px; }

.result-block {
  margin-bottom: 40px;
}

.block-title {
  font-size: 20px;
  font-weight: 700;
  color: $color-text-primary;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.block-subtitle {
  font-size: 13px;
  font-weight: 400;
  color: $color-text-secondary;
}

.top5-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.recommendation-status { padding: 14px 18px; margin-bottom: 24px; }
.recommendation-status summary { color: $color-text-primary; cursor: pointer; font-weight: 600; }
.recommendation-status p { margin: 10px 0; color: $color-text-secondary; font-size: 13px; }
.validation-card { padding: 20px; }
.validation-heading { display: flex; align-items: center; gap: 8px; }
.validation-heading .premium-icon,
.validation-warning .premium-icon { border-radius: 8px; box-shadow: none; vertical-align: -7px; }
.validation-card h3 { margin-bottom: 8px; color: $color-text-primary; font-size: 17px; }
.validation-card p { margin-top: 6px; font-size: 14px; color: $color-text-secondary; line-height: 1.6; }
.validation-card.warning { border-color: $color-rose; }
.validation-ok { color: $color-sage-dark !important; }
.validation-warning { display: flex; align-items: center; gap: 8px; }

// ── 总结 ─────────────────────────────────

.summary-card {
  padding: 24px;
}

.summary-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 12px;
}

.summary-content {
  font-size: 14px;
  color: $color-text-primary;
  line-height: 1.8;
  white-space: pre-wrap;
}

.generation-banner,
.edit-error {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  margin-bottom: 20px;
  color: $color-text-secondary;
  font-size: 13px;
}

.edit-error {
  border-color: $color-rose;
}

.conversation-card {
  padding: 24px;
  margin-bottom: 36px;
}

.conversation-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.conversation-heading h2 {
  margin-top: 4px;
  font-size: 20px;
  color: $color-text-primary;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.remove-ingredient-row {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}

.remove-ingredient-row .el-input { flex: 1; }

.conversation-input {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}

.conversation-input .el-input { flex: 1; }

.version-list {
  margin-top: 18px;
  border-top: 1px solid $color-border;
  padding-top: 12px;
}

.version-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  color: $color-text-secondary;
  font-size: 13px;
}

@media (max-width: $breakpoint-sm) {
  .plan-result-page { padding-top: 24px; }
  .overview-card { padding: 20px; }
  .overview-heading { flex-direction: column; }
  .overview-grid { gap: 8px; }
  .overview-grid div { padding: 12px 8px; }
  .overview-grid strong { font-size: 18px; }
  .conversation-input { flex-direction: column; align-items: stretch; }
  .remove-ingredient-row { flex-direction: column; }
}
</style>
