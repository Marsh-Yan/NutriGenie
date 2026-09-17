<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePlanStore } from '@/stores/plan'
import RecipeCard from '@/components/recipe/RecipeCard.vue'
import WeeklyTimeline from '@/components/plan/WeeklyTimeline.vue'
import NutritionReport from '@/components/plan/NutritionReport.vue'
import ShoppingList from '@/components/plan/ShoppingList.vue'
import { Refresh } from '@element-plus/icons-vue'
import PremiumIcon from '@/components/common/PremiumIcon.vue'
import ProgressStepper from '@/components/plan/ProgressStepper.vue'

const route = useRoute()
const router = useRouter()
const store = usePlanStore()
const messageInput = ref('')
const ingredientInput = ref('')
const sendingMessage = ref(false)
const showVersions = ref(false)
const showAllValidationWarnings = ref(false)

const loadingCopy = computed(() => {
  if (store.resultLoading) {
    return { eyebrow: 'FINALIZING', title: '方案已经就绪', desc: '正在整理营养数据与采购清单，马上为你呈现。' }
  }
  if (store.status === 'pending') {
    return { eyebrow: 'GETTING READY', title: '正在准备规划引擎', desc: '我们正在读取你的健康画像与本次饮食需求。' }
  }
  const step = store.progress?.step_name
  const copies: Record<string, { title: string; desc: string }> = {
    意图分析: { title: '正在理解你的需求', desc: '识别目标、预算、忌口与每日餐数。' },
    约束构建: { title: '正在计算合理边界', desc: '结合身体数据、活动水平与营养目标。' },
    食材知识: { title: '正在准备食材事实', desc: '读取标准食材、营养、价格与单位信息。' },
    'AI 创作候选': { title: '正在创作候选菜品', desc: 'AI 根据你的约束即时设计多样化菜品。' },
    食材标准化: { title: '正在重新核算菜品', desc: '解析食材与单位，并重新计算营养和成本。' },
    硬约束校验: { title: '正在检查硬性约束', desc: '核对忌口、过敏原、食材覆盖与饮食类型。' },
    整周优化: { title: '正在编排整周餐单', desc: '控制重复，平衡热量、预算与菜品多样性。' },
    结果校验与汇总: { title: '正在进行最终校验', desc: '汇总营养、采购清单与方案质量指标。' },
    保存方案版本: { title: '正在保存专属方案', desc: '整理结果与生成记录，马上为你呈现。' },
  }
  return { eyebrow: 'AI PLANNING', ...(copies[step || ''] || { title: '正在生成专属方案', desc: 'AI 正在分析需求并匹配适合你的菜谱。' }) }
})

const overview = computed(() => {
  const result = store.result
  if (!result) return null
  return {
    calories: result.nutrition_report.avg_daily_calories,
    cost: result.shopping_list.total_cost,
    recipes: result.generation_meta?.unique_recipe_count || result.recipes.length,
    maxRepeat: result.generation_meta?.max_recipe_repeat || 0,
    warnings: result.validation?.warnings.length || 0,
  }
})

const currentError = computed(() => store.lastRunError || store.error)
const isV2Result = computed(() => store.result?.schema_version === 'ai_native_v2')
const validationWarningGroups = computed(() => {
  const groups = new Map<string, number>()
  for (const warning of store.result?.validation?.warnings || []) {
    const message = warning.trim()
    if (message) groups.set(message, (groups.get(message) || 0) + 1)
  }
  return Array.from(groups, ([message, count]) => ({ message, count }))
})
const visibleValidationWarningGroups = computed(() => (
  showAllValidationWarnings.value
    ? validationWarningGroups.value
    : validationWarningGroups.value.slice(0, 4)
))
const hiddenValidationGroupCount = computed(() => Math.max(0, validationWarningGroups.value.length - 4))

watch(() => route.params.id, (value) => {
  showAllValidationWarnings.value = false
  const planId = Number(value)
  if (Number.isInteger(planId) && planId > 0) {
    store.load(planId)
  }
  else {
    store.reset()
    store.status = 'failed'
    store.error = '方案编号无效，请从“我的方案”重新进入'
  }
}, { immediate: true })

onUnmounted(() => store.stopPolling())

function printPlan() {
  window.print()
}

async function submitMessage(action?: Record<string, any>) {
  const message = messageInput.value.trim()
  if ((!message && !action) || sendingMessage.value || store.editing) return
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
    <div v-if="!store.result && store.status !== 'failed'" class="loading-section">
      <div class="loading-card card">
        <div class="loading-glow glow-one" />
        <div class="loading-glow glow-two" />
        <div class="loading-hero">
          <div class="loading-animation" aria-hidden="true">
            <div class="orbit orbit-one"><span /></div>
            <div class="orbit orbit-two"><span /></div>
            <PremiumIcon name="thinking" class="loading-icon" :size="38" :box-size="74" />
          </div>
          <div class="loading-copy">
            <span class="loading-eyebrow"><i />{{ loadingCopy.eyebrow }}</span>
            <h1 class="loading-title">{{ loadingCopy.title }}</h1>
            <p class="loading-desc">{{ loadingCopy.desc }}</p>
            <div class="loading-tags" aria-label="规划特点">
              <span>AI 原生生成</span><span>营养约束</span><span>预算校验</span>
            </div>
          </div>
        </div>
        <div class="progress-panel">
          <ProgressStepper :status="store.status" :progress="store.progress" />
        </div>
        <div class="loading-footer">
          <span><i />{{ store.error || '无需刷新，完成后将自动展示' }}</span>
          <el-button
            v-if="store.status === 'completed' && !store.polling && !store.resultLoading"
            size="small"
            round
            @click="store.refreshResult()"
          >
            继续获取结果
          </el-button>
          <span v-else>通常需要 30–90 秒</span>
        </div>
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
          <div><strong>{{ overview.recipes }}</strong><span>本周不同菜品</span></div>
          <div><strong>{{ overview.maxRepeat || '—' }}</strong><span>单菜最多重复</span></div>
        </div>
        <div class="result-actions">
          <el-button round @click="printPlan">打印方案</el-button>
          <el-button type="primary" round @click="router.push('/plan/new')">重新规划</el-button>
        </div>
      </section>
      <section class="recommendation-status card">
        <details>
          <summary>查看 AI 生成依据</summary>
          <p>菜谱由大模型生成，程序对硬性限制、营养汇总和预算进行校验。</p>
          <el-tag :type="store.result.generation_meta.rag_used ? 'success' : 'info'" effect="light">
            {{ store.result.generation_meta.rag_used ? '已参考知识库' : '纯 AI 生成' }}
          </el-tag>
          <el-tag :type="isV2Result ? 'success' : 'warning'" effect="light">
            {{ isV2Result ? '营养与预算由食材目录核算' : '历史版本使用 AI 估算数据' }}
          </el-tag>
        </details>
      </section>
      <div class="plan-dashboard">
        <!-- 周计划：桌面端主视图 -->
        <section v-if="store.result.weekly_plan.length > 0" class="dashboard-panel schedule-panel card">
          <WeeklyTimeline :weekly-plan="store.result.weekly_plan" />
        </section>

        <aside class="insights-column" aria-label="营养与计划校验">
          <section class="dashboard-panel nutrition-panel card">
            <NutritionReport
              :report="store.result.nutrition_report"
              :target-range="store.result.validation?.derived?.target_calorie_range"
            />
          </section>

          <section v-if="store.result.validation" class="validation-card card" :class="{ warning: store.result.validation.warnings.length }">
            <div class="validation-title-row">
              <h2 class="validation-heading"><PremiumIcon name="check" :size="14" :box-size="28" />计划校验</h2>
              <span>{{ store.result.validation.warnings.length ? `${validationWarningGroups.length} 类提醒` : '状态良好' }}</span>
            </div>
            <div class="validation-metrics">
              <p><strong>{{ (store.result.validation.derived.avg_daily_calories || store.result.nutrition_report.avg_daily_calories).toFixed(0) }}</strong><span>日均 kcal</span></p>
              <p><strong>¥{{ store.result.shopping_list.total_cost.toFixed(1) }}</strong><span>预计采购</span></p>
            </div>
            <div
              v-if="visibleValidationWarningGroups.length"
              class="validation-warnings-list"
              :class="{ expanded: showAllValidationWarnings }"
            >
              <p v-for="warning in visibleValidationWarningGroups" :key="warning.message" class="validation-warning">
                <PremiumIcon name="alert" :size="12" :box-size="24" />
                <span>{{ warning.message }}</span>
                <small v-if="warning.count > 1">重复 {{ warning.count }} 次</small>
              </p>
            </div>
            <button
              v-if="validationWarningGroups.length > 4"
              type="button"
              class="validation-toggle"
              :aria-expanded="showAllValidationWarnings"
              @click="showAllValidationWarnings = !showAllValidationWarnings"
            >
              {{ showAllValidationWarnings ? '收起提醒' : `查看其余 ${hiddenValidationGroupCount} 类提醒` }}
            </button>
            <p v-if="!store.result.validation.warnings.length" class="validation-ok">计划完整，未发现需要提示的偏差。</p>
          </section>
        </aside>
      </div>

      <!-- AI 生成菜谱 -->
      <section class="result-block recipe-section">
        <div class="block-heading">
          <div><span class="eyebrow">AI 精选</span><h2 class="block-title"><PremiumIcon name="trophy" class="heading-icon" :size="18" :box-size="34" />生成菜谱</h2></div>
          <p class="block-subtitle">根据你的画像、预算与忌口即时生成，点击菜谱查看依据与做法。</p>
        </div>
        <div class="top5-list">
          <RecipeCard
            v-for="(recipe, i) in store.result.recipes"
            :key="'recipe_key' in recipe ? recipe.recipe_key : `legacy-${recipe.recipe_id}`"
            :recipe="recipe"
            :rank="i + 1"
          />
        </div>
      </section>

      <div class="result-lower-grid" :class="{ single: !store.result.summary }">
        <section class="dashboard-panel shopping-panel card">
          <ShoppingList :shopping-list="store.result.shopping_list" />
        </section>

        <section v-if="store.result.summary" class="summary-card card">
          <div class="summary-kicker">NUTRIGENIE NOTE</div>
          <h2 class="summary-title">
            <PremiumIcon name="clipboard" class="heading-icon" :size="17" :box-size="32" />
            AI 总结
          </h2>
          <div class="summary-content">{{ store.result.summary }}</div>
        </section>
      </div>

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
          <el-button link :aria-expanded="showVersions" :disabled="store.editing" @click="showVersions = !showVersions">版本历史（{{ store.versions.length }}）</el-button>
        </div>
        <div class="quick-actions">
          <el-button size="small" round :disabled="store.editing || sendingMessage" @click="submitMessage({ type: 'reduce_budget' })">降低预算</el-button>
          <el-button size="small" round :disabled="store.editing || sendingMessage" @click="submitMessage({ type: 'increase_protein' })">增加蛋白质</el-button>
          <el-button size="small" round :disabled="store.editing || sendingMessage" @click="submitMessage({ type: 'shorter_cooking' })">缩短烹饪时间</el-button>
          <el-button size="small" round :disabled="store.editing || sendingMessage" @click="submitMessage({ type: 'replace_meal', day: 1, slot: 'lunch' })">重做第 1 天午餐</el-button>
          <el-button size="small" round :disabled="store.editing || sendingMessage" @click="submitMessage({ type: 'replace_day', day: 1 })">重做第 1 天</el-button>
        </div>
        <div class="remove-ingredient-row">
          <el-input v-model="ingredientInput" size="small" placeholder="输入要去除的食材，例如：花生" :disabled="store.editing || sendingMessage" @keydown.enter="removeIngredient" />
          <el-button size="small" round :disabled="!ingredientInput.trim() || store.editing || sendingMessage" @click="removeIngredient">去除食材</el-button>
        </div>
        <div class="conversation-input">
          <el-input
            v-model="messageInput"
            type="textarea"
            :rows="3"
            maxlength="1000"
            show-word-limit
            :disabled="store.editing || sendingMessage"
            placeholder="例如：把第三天晚餐换成不含海鲜、20 分钟内完成的菜"
            @keydown.ctrl.enter="submitMessage()"
          />
          <el-button type="primary" round :loading="sendingMessage || store.editing" :disabled="!messageInput.trim() || store.editing" @click="submitMessage()">生成新版本</el-button>
        </div>
        <div v-if="showVersions" class="version-list">
          <div v-for="version in store.versions" :key="version.version_id" class="version-row">
            <span>版本 {{ version.version_no }} · {{ new Date(version.created_at).toLocaleString() }}</span>
            <el-tag v-if="version.is_current" size="small" type="success">当前</el-tag>
            <el-button v-else size="small" link :disabled="store.editing || sendingMessage" @click="restoreVersion(version.version_id)">恢复</el-button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped lang="scss">
.plan-result-page {
  max-width: 1320px;
  padding-top: clamp(28px, 4vw, 52px);
  padding-bottom: 96px;
}

// ── 加载状态 ─────────────────────────────

.loading-section {
  max-width: 860px;
  margin-inline: auto;
  padding-top: 22px;
}

.loading-card {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  padding: 34px;
  border-color: rgba($color-sage, .18);
  background: linear-gradient(145deg, rgba($color-card,.96), rgba($color-background,.92));
  box-shadow: 0 20px 54px rgba($color-brand, .09);
}

.loading-glow {
  position: absolute;
  z-index: -1;
  border-radius: 50%;
  filter: blur(2px);
  pointer-events: none;
}

.glow-one { top: -110px; right: -70px; width: 300px; height: 300px; background: radial-gradient(circle, rgba($color-sage-light,.34), transparent 68%); }
.glow-two { bottom: -130px; left: -80px; width: 260px; height: 260px; background: radial-gradient(circle, rgba($color-rose-light,.22), transparent 68%); }

.loading-hero {
  display: grid;
  grid-template-columns: 124px minmax(0, 1fr);
  align-items: center;
  gap: 28px;
  max-width: 660px;
  margin: 0 auto 30px;
}

.loading-animation {
  position: relative;
  width: 118px;
  height: 118px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.orbit {
  position: absolute;
  border: 1px solid rgba($color-sage, .2);
  border-radius: 50%;

  span {
    position: absolute;
    top: 50%;
    left: -3px;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: $color-sage;
    box-shadow: 0 0 0 5px rgba($color-sage,.1), 0 0 14px rgba($color-sage,.35);
  }
}

.orbit-one { inset: 2px; animation: spin 5.5s linear infinite; }
.orbit-two { inset: 14px; border-style: dashed; animation: spin-reverse 8s linear infinite; }

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes spin-reverse { to { transform: rotate(-360deg); } }

.loading-icon {
  position: relative;
  z-index: 1;
  border-radius: 24px;
  box-shadow: inset 0 1px 0 rgba($color-card,.8), 0 14px 32px rgba($color-brand,.14);
  animation: breathe 2.8s ease-in-out infinite;
}

.loading-icon:hover { transform: none; }
@keyframes breathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.04); } }

.loading-copy { text-align: left; }
.loading-eyebrow { display: inline-flex; align-items: center; gap: 8px; color: $color-sage-dark; font-size: 12px; font-weight: 820; letter-spacing: .12em; }
.loading-eyebrow i { width: 7px; height: 7px; border-radius: 50%; background: $color-sage; box-shadow: 0 0 0 5px rgba($color-sage,.1); animation: blink 1.5s ease-in-out infinite; }

.loading-title {
  margin: 8px 0 6px;
  font-size: 28px;
  font-weight: 750;
  color: $color-text-primary;
  letter-spacing: -.035em;
}

.loading-desc {
  font-size: 14px;
  color: $color-text-secondary;
  line-height: 1.7;
}

.loading-tags { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 14px; }
.loading-tags span { padding: 6px 10px; border: 1px solid rgba($color-sage,.2); border-radius: 999px; background: rgba(255,255,255,.68); color: $color-text-secondary; font-size: 12px; font-weight: 600; }

.progress-panel { padding: 22px; border: 1px solid rgba($color-sage,.13); border-radius: 18px; background: rgba(255,255,255,.64); backdrop-filter: blur(8px); }

.loading-footer { display: flex; justify-content: space-between; gap: 12px; margin-top: 18px; color: $color-text-secondary; font-size: 12px; font-weight: 550; }
.loading-footer span:first-child { display: inline-flex; align-items: center; gap: 7px; }
.loading-footer i { width: 6px; height: 6px; border-radius: 50%; background: $color-success; }

// ── 错误状态 ─────────────────────────────

.error-section {
  max-width: 760px;
  margin-inline: auto;
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

.overview-card {
  position: relative;
  margin-bottom: 16px;
  padding: clamp(26px, 4vw, 44px);
  overflow: hidden;
  border-color: rgba($color-sage,.18);
  background:
    radial-gradient(circle at 88% -30%, rgba($color-blue-soft,.9), transparent 20rem),
    radial-gradient(circle at 0 120%, rgba($color-rose-light,.65), transparent 18rem),
    linear-gradient(135deg, $color-surface-muted, $color-surface-warm);
  box-shadow: 0 24px 64px rgba($color-brand,.13);
}
.overview-card::after { position: absolute; right: -84px; bottom: -120px; width: 300px; height: 300px; border: 1px solid rgba($color-sage,.14); border-radius: 50%; content: ''; pointer-events: none; }
.overview-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.overview-heading h1 { margin-top: 7px; color: $color-text-primary; font-size: clamp(30px, 3vw, 42px); letter-spacing: -.045em; }
.overview-heading .eyebrow { color: $color-sage-dark; }
.overview-heading .eyebrow::before { background: $color-sage; box-shadow: 0 0 0 5px rgba($color-sage,.11); }
.overview-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-top: 22px; }
.overview-grid div { display: flex; flex-direction: column; padding: 16px 18px; border: 1px solid rgba($color-sage,.13); border-radius: $radius-md; background: rgba($color-card,.55); backdrop-filter: blur(10px); }
.overview-grid strong { color: $color-text-primary; font-size: clamp(21px,2.2vw,28px); letter-spacing: -.03em; }
.overview-grid span { color: $color-text-secondary; font-size: 12px; font-weight: 600; }
.result-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 18px; }
.result-actions :deep(.el-button:not(.el-button--primary)) { border-color: rgba($color-sage,.24); background: rgba($color-card,.5); color: $color-sage-dark; }
.result-actions :deep(.el-button--primary) { border-color: $color-sage-dark; background: $color-sage-dark; color: $color-text-inverse; }

.result-block {
  margin-bottom: 40px;
}

.block-title {
  margin: 6px 0 0;
  font-size: 28px;
  font-weight: 800;
  color: $color-text-primary;
  display: flex;
  align-items: center;
  gap: 8px;
}

.block-subtitle {
  max-width: 480px;
  font-size: 13px;
  font-weight: 400;
  color: $color-text-secondary;
}

.top5-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.recommendation-status { padding: 14px 18px; margin-bottom: 20px; border-radius: $radius-md; box-shadow: none; }
.recommendation-status summary { color: $color-text-primary; cursor: pointer; font-weight: 600; }
.recommendation-status p { margin: 10px 0; color: $color-text-secondary; font-size: 13px; }
.plan-dashboard { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(330px, .85fr); gap: 20px; align-items: start; }
.dashboard-panel { padding: 26px; }
.schedule-panel,
.nutrition-panel,
.shopping-panel { min-width: 0; }
.schedule-panel :deep(.weekly-timeline),
.nutrition-panel :deep(.nutrition-report),
.shopping-panel :deep(.shopping-list) { margin-bottom: 0; }
.insights-column { display: grid; gap: 20px; min-width: 0; }
.validation-card { padding: 22px; box-shadow: none; }
.validation-title-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.validation-title-row > span { padding: 6px 10px; border-radius: 999px; background: $color-lime-soft; color: $color-sage-dark; font-size: 12px; font-weight: 750; }
.validation-heading { display: flex; align-items: center; gap: 8px; }
.validation-heading .premium-icon,
.validation-warning .premium-icon { border-radius: 8px; box-shadow: none; vertical-align: -7px; }
.validation-card h2 { color: $color-text-primary; font-size: 17px; }
.validation-card p { margin-top: 6px; font-size: 14px; color: $color-text-secondary; line-height: 1.6; }
.validation-card.warning { border-color: $color-rose; }
.validation-card.warning .validation-title-row > span { background: $color-rose-light; color: $color-rose-dark; }
.validation-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 18px 0 14px; }
.validation-metrics p { display: grid; gap: 1px; margin: 0; padding: 12px; border-radius: $radius-sm; background: $color-surface-soft; }
.validation-metrics strong { color: $color-text-primary; font-size: 18px; }
.validation-metrics span { color: $color-text-secondary; font-size: 12px; font-weight: 600; }
.validation-ok { color: $color-sage-dark !important; }
.validation-warnings-list { display: grid; gap: 7px; }
.validation-warnings-list.expanded { max-height: 238px; overflow-y: auto; padding-right: 5px; scrollbar-color: rgba($color-sage,.35) transparent; scrollbar-width: thin; }
.validation-warning { display: flex; align-items: flex-start; gap: 8px; margin: 0 !important; }
.validation-warning .premium-icon { flex: 0 0 auto; }
.validation-warning > span { min-width: 0; flex: 1; }
.validation-warning > small { flex: 0 0 auto; margin-top: 2px; padding: 2px 7px; border-radius: 999px; background: $color-rose-light; color: $color-rose-dark; font-size: 10px; font-weight: 700; white-space: nowrap; }
.validation-toggle { width: 100%; margin-top: 12px; padding: 9px 12px; border: 1px solid rgba($color-rose-dark,.16); border-radius: $radius-sm; background: rgba($color-rose-light,.45); color: $color-rose-dark; cursor: pointer; font: inherit; font-size: 12px; font-weight: 750; transition: background-color .2s ease, border-color .2s ease; }
.validation-toggle:hover { border-color: rgba($color-rose-dark,.3); background: $color-rose-light; }
.validation-toggle:focus-visible { outline: 2px solid rgba($color-rose-dark,.35); outline-offset: 2px; }
.recipe-section { margin-top: 76px; }
.block-heading { display: flex; align-items: end; justify-content: space-between; gap: 28px; margin-bottom: 20px; }
.top5-list { gap: 12px; }
.result-lower-grid { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(300px, .8fr); gap: 20px; align-items: start; margin-top: 64px; }
.result-lower-grid.single { grid-template-columns: 1fr; }

// ── 总结 ─────────────────────────────────

.summary-card {
  position: sticky;
  top: 106px;
  padding: 28px;
  border-color: rgba($color-rose-dark,.1);
  background: $color-surface-warm;
  box-shadow: none;
}
.summary-kicker { margin-bottom: 10px; color: $color-rose-dark; font-size: 12px; font-weight: 850; letter-spacing: .1em; }

.summary-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 22px;
  font-weight: 750;
  color: $color-text-primary;
  margin-bottom: 12px;
}

.summary-content {
  font-size: 13px;
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
  margin: 64px 0 36px;
  padding: clamp(24px, 4vw, 36px);
  border-color: rgba($color-sage,.16);
  background: linear-gradient(135deg, rgba($color-sage-light,.56), rgba(255,255,255,.96));
  box-shadow: none;
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
  font-size: 26px;
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

@media (max-width: 1050px) {
  .plan-dashboard { grid-template-columns: 1fr; }
  .insights-column { grid-template-columns: 1fr 1fr; }
  .result-lower-grid { grid-template-columns: 1fr; }
  .summary-card { position: static; }
}

@media (max-width: $breakpoint-sm) {
  .plan-result-page { padding-top: 24px; }
  .loading-section { padding-top: 4px; }
  .loading-card { padding: 24px 18px; }
  .loading-hero { grid-template-columns: 1fr; gap: 14px; margin-bottom: 24px; text-align: center; }
  .loading-animation { width: 100px; height: 100px; margin: 0 auto; }
  .loading-copy { text-align: center; }
  .loading-title { font-size: 24px; }
  .loading-tags { justify-content: center; }
  .progress-panel { padding: 17px 14px; }
  .loading-footer { align-items: center; flex-direction: column; }
  .overview-card { padding: 20px; }
  .overview-heading { flex-direction: column; }
  .overview-grid { gap: 8px; }
  .overview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .overview-grid div { padding: 12px; }
  .overview-grid strong { font-size: 18px; }
  .result-actions { justify-content: stretch; }
  .result-actions :deep(.el-button) { flex: 1; margin: 0; }
  .dashboard-panel { padding: 18px; }
  .insights-column { grid-template-columns: 1fr; }
  .recipe-section { margin-top: 54px; }
  .block-heading { align-items: flex-start; flex-direction: column; gap: 10px; }
  .block-title { font-size: 24px; }
  .result-lower-grid { margin-top: 48px; }
  .conversation-card { margin-top: 48px; }
  .conversation-heading { align-items: flex-start; flex-direction: column; }
  .conversation-input { flex-direction: column; align-items: stretch; }
  .remove-ingredient-row { flex-direction: column; }
}

@media print {
  .result-actions, :global(.app-header), :global(.mobile-nav), :global(.app-footer) { display: none !important; }
  .plan-result-page { max-width: none; padding: 0; }
  .plan-dashboard,
  .result-lower-grid { display: block; }
  .dashboard-panel,
  .summary-card { margin-bottom: 18px; }
  .card { break-inside: avoid; box-shadow: none; }
}
</style>
