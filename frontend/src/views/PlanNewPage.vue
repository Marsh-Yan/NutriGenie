<script setup lang="ts">
import { ref, computed, onMounted, useId } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter } from 'vue-router'
import { usePlanStore } from '@/stores/plan'
import { useProfileStore } from '@/stores/profile'
import { useAuthStore } from '@/stores/auth'
import { useDashboardStore } from '@/stores/dashboard'
import { usePantryStore } from '@/stores/pantry'
import { usePlanIndexStore } from '@/stores/planIndex'
import { usePreferenceStore } from '@/stores/preference'
import { MagicStick, Right } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const planStore = usePlanStore()
const profileStore = useProfileStore()
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const pantryStore = usePantryStore()
const planIndexStore = usePlanIndexStore()
const preferenceStore = usePreferenceStore()

const {
  draftInput: userInput,
  draftDurationDays: durationDays,
  draftTotalBudget: totalBudget,
  draftExampleIndex: activeExample,
} = storeToRefs(planStore)
const submitting = ref(false)
const submitError = ref('')
const inputError = ref('')
const profileLoadError = ref('')
const inputId = useId()
const budgetId = useId()
const pantryId = useId()
const preferenceId = useId()
const pantryInput = ref('')

const examples = [
  { text: '减脂一周，预算300元，家里有鸡蛋和番茄', days: 7, budget: 300 },
  { text: '增肌三天，预算200，高蛋白饮食', days: 3, budget: 200 },
  { text: '健康饮食五天，预算500，不吃海鲜', days: 5, budget: 500 },
  { text: '控糖一周，预算400，已有鸡胸肉和西兰花', days: 7, budget: 400 },
]

const profileExists = computed(() => profileStore.hasProfile)
const profileSummary = computed(() => {
  const profile = profileStore.profile
  if (!profile) return []
  const goalLabels: Record<string, string> = { fat_loss: '减脂', muscle_gain: '增肌', blood_sugar: '控糖', healthy: '保持健康' }
  const dietLabels: Record<string, string> = { balanced: '均衡饮食', keto: '生酮饮食', high_protein: '高蛋白', gluten_free: '无麸质', vegan: '素食', healthy: '健康饮食' }
  return [
    { label: '目标', value: goalLabels[profile.health_goal] || profile.health_goal },
    { label: '饮食方式', value: dietLabels[profile.diet_type] || profile.diet_type },
    { label: '每日预算', value: profile.daily_budget ? `¥${profile.daily_budget}` : '未限制' },
    { label: '过敏与忌口', value: profile.allergies?.length ? profile.allergies.join('、') : '未填写' },
  ]
})

onMounted(async () => {
  if (authStore.user?.user_id) {
    pantryStore.hydrate(authStore.user.user_id)
    preferenceStore.hydrate(authStore.user.user_id)
    planIndexStore.hydrate(authStore.user.user_id)
    dashboardStore.hydrate(authStore.user.user_id)
  }
  if (!profileStore.profile) {
    try {
      await profileStore.fetchMyProfile()
    } catch (e: unknown) {
      profileLoadError.value = e instanceof Error ? e.message : '健康画像加载失败'
    }
  }
})

function addPantryItem() {
  if (pantryStore.add(pantryInput.value)) pantryInput.value = ''
}

function selectExample(i: number) {
  activeExample.value = i
  userInput.value = examples[i].text
  durationDays.value = examples[i].days
  totalBudget.value = examples[i].budget
}

async function submit() {
  submitError.value = ''
  inputError.value = ''
  if (!userInput.value.trim()) {
    inputError.value = '请先描述你的饮食目标或限制'
    document.getElementById(inputId)?.focus()
    return
  }
  if (userInput.value.trim().length < 6) {
    inputError.value = '描述再具体一点，例如目标、预算或忌口'
    document.getElementById(inputId)?.focus()
    return
  }
  if (submitting.value) return

  if (!profileStore.profile) {
    router.push('/profile')
    return
  }

  const profileId = profileStore.profile?.profile_id
  if (!profileId) {
    throw new Error('用户画像创建失败，请稍后重试')
  }

  submitting.value = true
  try {
    const originalInput = userInput.value.trim()
    const requestParts = [originalInput]
    if (pantryStore.items.length) requestParts.push(`已有食材：${pantryStore.items.join('、')}。`)
    if (preferenceStore.note.trim()) requestParts.push(`本地偏好备注：${preferenceStore.note.trim()}。`)
    const res = await planStore.create(
      requestParts.join('\n'),
      durationDays.value,
      totalBudget.value || 0,
      profileId,
    )
    const now = new Date().toISOString()
    planIndexStore.upsert({
      planId: res.plan_id,
      title: originalInput.length > 28 ? `${originalInput.slice(0, 28)}…` : originalInput,
      userInput: originalInput,
      durationDays: durationDays.value,
      totalBudget: totalBudget.value || 0,
      status: res.status,
      createdAt: res.created_at || now,
      completedAt: null,
      lastOpenedAt: now,
      sourcePlanId: Number.isInteger(Number(route.query.source)) && Number(route.query.source) > 0
        ? Number(route.query.source)
        : undefined,
    })
    dashboardStore.selectPlan(res.plan_id)
    planStore.clearDraft()
    router.push({ path: `/plan/${res.plan_id}`, query: { tab: 'today' } })
  } catch (e: any) {
    submitError.value = e?.message || '创建失败，请检查网络后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="plan-new-page page-container">
    <div class="planning-workspace">
      <aside class="intro-panel" aria-labelledby="plan-new-title">
        <div class="intro-copy">
          <span class="intro-kicker"><i aria-hidden="true" />AI 营养规划工作台</span>
          <h1 id="plan-new-title" class="intro-title">
            把目标说清楚，<br />
            <span>剩下的交给 AI。</span>
          </h1>
          <p class="intro-desc">
            不需要学习复杂的营养术语。告诉我们你的目标、预算和忌口，AI 会把它们整理成一份真正能执行的饮食计划。
          </p>
        </div>

        <ol class="workflow-list" aria-label="规划生成流程">
          <li>
            <span class="workflow-index">01</span>
            <span class="workflow-copy"><strong>描述真实需求</strong><span>目标、周期、预算与已有食材</span></span>
          </li>
          <li>
            <span class="workflow-index">02</span>
            <span class="workflow-copy"><strong>AI 编排与校验</strong><span>兼顾营养、成本和菜品多样性</span></span>
          </li>
          <li>
            <span class="workflow-index">03</span>
            <span class="workflow-copy"><strong>获得可执行方案</strong><span>菜谱、每日餐单和采购清单</span></span>
          </li>
        </ol>

        <div class="profile-readiness" :class="{ ready: profileExists }" aria-live="polite">
          <span class="readiness-dot" aria-hidden="true" />
          <div>
            <strong v-if="profileStore.loading">正在同步健康画像</strong>
            <strong v-else-if="profileExists">健康画像已准备好</strong>
            <strong v-else>还差一份健康画像</strong>
            <span v-if="profileStore.loading">正在核对你的身体数据与偏好…</span>
            <span v-else-if="profileExists">提交需求后即可开始生成</span>
            <span v-else>提交时会先带你完成基础信息</span>
          </div>
        </div>
      </aside>

      <form class="prompt-card card" novalidate @submit.prevent="submit">
        <header class="prompt-heading">
          <div>
            <span class="eyebrow">创建新方案</span>
            <h2>今天，想怎样好好吃饭？</h2>
            <p>像和营养师聊天一样自然地描述，细节越具体，方案越贴合。</p>
          </div>
          <span class="time-badge">约 30–90 秒</span>
        </header>

        <section v-if="profileSummary.length" class="profile-summary" aria-label="当前健康画像摘要">
          <div v-for="item in profileSummary" :key="item.label">
            <span>{{ item.label }}</span><strong>{{ item.value }}</strong>
          </div>
          <button type="button" @click="router.push('/profile')">更新画像</button>
        </section>

        <div class="input-area">
          <label class="section-label" :for="inputId"><span>01</span>描述你的需求</label>
          <el-input
            :id="inputId"
            v-model="userInput"
            type="textarea"
            :rows="7"
            placeholder="例如：我想减脂一周，总预算 300 元，家里有鸡蛋和番茄，不吃海鲜，希望晚餐 20 分钟内做好……"
            maxlength="500"
            show-word-limit
            class="plan-input"
            :aria-invalid="Boolean(inputError)"
            :aria-describedby="inputError ? `${inputId}-hint ${inputId}-error` : `${inputId}-hint`"
            @update:model-value="inputError = ''"
          />
          <p :id="`${inputId}-hint`" class="constraint-hint">
            <span aria-hidden="true">✦</span>
            文本中明确写出的天数、预算和忌口会优先生效；下方选项用于最后核对。
          </p>
          <p v-if="inputError" :id="`${inputId}-error`" class="submit-error" role="alert">{{ inputError }}</p>
        </div>

        <section class="examples" aria-labelledby="example-title">
          <div class="section-heading">
            <div>
              <span id="example-title" class="section-label"><span>02</span>从灵感模板开始</span>
              <small>点击后仍可继续修改</small>
            </div>
          </div>
          <div class="example-grid">
            <button
              v-for="(ex, i) in examples"
              :key="i"
              class="example-tag"
              :class="{ active: activeExample === i }"
              type="button"
              @click="selectExample(i)"
            >
              <span class="example-index">0{{ i + 1 }}</span>
              <span class="example-copy">{{ ex.text }}</span>
              <el-icon aria-hidden="true"><MagicStick /></el-icon>
            </button>
          </div>
        </section>

        <section class="local-context" aria-labelledby="local-context-title">
          <div class="controls-heading">
            <span id="local-context-title" class="section-label"><span>03</span>补充家中食材与偏好</span>
            <small>保存在当前设备，下次创建仍可使用</small>
          </div>
          <div class="pantry-entry">
            <label class="field-label" :for="pantryId">家中已有食材</label>
            <el-input
              :id="pantryId"
              v-model="pantryInput"
              maxlength="30"
              placeholder="例如：鸡蛋"
              @keydown.enter.prevent="addPantryItem"
            />
            <el-button type="primary" plain @click="addPantryItem">加入食材</el-button>
          </div>
          <div v-if="pantryStore.items.length" class="pantry-tags" aria-label="已有食材">
            <button v-for="item in pantryStore.items" :key="item" type="button" @click="pantryStore.remove(item)">
              {{ item }}<span aria-hidden="true">×</span>
            </button>
          </div>
          <label class="field-label" :for="preferenceId">偏好备注（选填）</label>
          <el-input
            :id="preferenceId"
            :model-value="preferenceStore.note"
            type="textarea"
            :rows="2"
            maxlength="300"
            show-word-limit
            placeholder="可选：例如工作日晚餐希望 20 分钟内完成，口味清淡"
            class="preference-input"
            @update:model-value="preferenceStore.setNote(String($event))"
          />
          <p class="constraint-hint"><span aria-hidden="true">✦</span>提交时会明确写入“已有食材”和“本地偏好备注”，不会覆盖上方原始需求。</p>
        </section>

        <section class="controls-panel" aria-labelledby="controls-title">
          <div class="controls-heading">
            <span id="controls-title" class="section-label"><span>04</span>核对规划范围</span>
            <small>这些选项会和上方文字一起提交</small>
          </div>
          <div class="options-row">
            <fieldset class="option-item days-option">
              <legend>规划天数</legend>
              <el-radio-group v-model="durationDays" size="small">
                <el-radio-button :value="3">3 天</el-radio-button>
                <el-radio-button :value="5">5 天</el-radio-button>
                <el-radio-button :value="7">7 天</el-radio-button>
              </el-radio-group>
              <span>适合短期尝试或完整一周安排</span>
            </fieldset>
            <div class="option-item budget-option">
              <label :for="budgetId">总预算（元）</label>
              <el-input-number
                :id="budgetId"
                v-model="totalBudget"
                :min="0"
                :max="9999"
                :step="50"
                size="small"
                controls-position="right"
                class="budget-input"
                placeholder="不限制"
              />
              <span>填写 0 代表本次不限制预算</span>
            </div>
          </div>
        </section>

        <section class="request-review" aria-labelledby="request-review-title">
          <div class="controls-heading">
            <h3 id="request-review-title" class="section-label"><span>05</span>生成前确认</h3>
            <small>请核对本次描述与画像中的硬性限制</small>
          </div>
          <dl class="review-grid">
            <div class="review-request"><dt>本次需求</dt><dd>{{ userInput.trim() || '请先填写需求' }}</dd></div>
            <div><dt>规划周期</dt><dd>{{ durationDays }} 天</dd></div>
            <div><dt>本次总预算</dt><dd>{{ totalBudget ? `¥${totalBudget}` : '未限制' }}</dd></div>
            <div v-for="item in profileSummary" :key="item.label"><dt>画像{{ item.label }}</dt><dd>{{ item.value }}</dd></div>
            <div><dt>家中已有食材</dt><dd>{{ pantryStore.items.join('、') || '未填写' }}</dd></div>
            <div v-if="preferenceStore.note.trim()" class="review-request"><dt>偏好备注</dt><dd>{{ preferenceStore.note.trim() }}</dd></div>
          </dl>
          <p class="review-note">若本次描述中写明了天数、预算或忌口，将优先按描述解析；过敏原仍以画像中的硬性排除为准。</p>
        </section>

        <div v-if="submitError || profileLoadError" class="error-stack">
          <p v-if="submitError" class="submit-error" role="alert">{{ submitError }}</p>
          <p v-if="profileLoadError" class="submit-error" role="alert">{{ profileLoadError }}</p>
        </div>

        <footer class="submit-row">
          <div class="profile-hint" aria-live="polite">
            <span class="hint-check" :class="{ ready: profileExists }" aria-hidden="true">✓</span>
            <span>
              <strong v-if="profileStore.loading">正在检查健康画像…</strong>
              <strong v-else-if="profileExists">信息已就绪，可以开始规划</strong>
              <strong v-else>需要先完成健康画像</strong>
              <small v-if="!profileStore.loading && !profileExists">点击后将自动前往画像页面</small>
              <small v-else>你的草稿会一直保留到成功创建方案</small>
            </span>
          </div>
          <el-button
            type="primary"
            size="large"
            round
            :loading="submitting"
            :disabled="!userInput.trim() || profileStore.loading"
            native-type="submit"
            class="submit-btn"
          >
            <el-icon><MagicStick /></el-icon>
            {{ submitting ? 'AI 规划中...' : '生成我的饮食方案' }}
            <el-icon v-if="!submitting"><Right /></el-icon>
          </el-button>
        </footer>
      </form>
    </div>
  </div>
</template>

<style scoped lang="scss">
.plan-new-page {
  padding-block: clamp(36px, 5vw, 72px) 96px;
}

.planning-workspace {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  align-items: start;
  gap: clamp(24px, 3vw, 48px);
}

.intro-panel {
  position: sticky;
  top: 92px;
  grid-column: span 4;
  display: flex;
  min-height: 676px;
  overflow: hidden;
  flex-direction: column;
  padding: clamp(30px, 3vw, 46px);
  border: 1px solid rgba($color-sage, .18);
  border-radius: $radius-xl;
  background:
    radial-gradient(circle at 100% 0, rgba($color-blue-soft, .88), transparent 18rem),
    radial-gradient(circle at 0 100%, rgba($color-rose-light, .7), transparent 20rem),
    linear-gradient(155deg, $color-surface-muted 0%, $color-surface-warm 100%);
  box-shadow: $shadow-lg;
  color: $color-text-secondary;
}

.intro-panel::before,
.intro-panel::after {
  position: absolute;
  border: 1px solid rgba($color-sage, .16);
  border-radius: 50%;
  content: '';
  pointer-events: none;
}

.intro-panel::before {
  top: -110px;
  right: -120px;
  width: 300px;
  height: 300px;
}

.intro-panel::after {
  right: 36px;
  bottom: 130px;
  width: 72px;
  height: 72px;
  background: rgba($color-rose-light, .58);
}

.intro-copy,
.workflow-list,
.profile-readiness { position: relative; z-index: 1; }

.intro-kicker {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: $color-sage-dark;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.intro-kicker i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 0 5px rgba($color-sage, .12);
}

.intro-title {
  margin-top: 22px;
  color: $color-text-primary;
  font-size: clamp(38px, 3.5vw, 56px);
  font-weight: 780;
  letter-spacing: -.055em;
  line-height: 1.04;
}

.intro-title span { color: $color-rose-dark; }

.intro-desc {
  max-width: 38rem;
  margin-top: 22px;
  color: $color-text-secondary;
  font-size: 14px;
  line-height: 1.85;
}

.workflow-list {
  display: grid;
  gap: 2px;
  margin-top: 40px;
  list-style: none;
}

.workflow-list li {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 15px 0;
  border-top: 1px solid rgba($color-sage, .16);
}

.workflow-index {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid rgba($color-sage, .2);
  border-radius: 12px;
  background: rgba($color-card, .58);
  color: $color-sage-dark;
  font-size: 12px;
  font-weight: 800;
}

.workflow-copy { display: grid; gap: 2px; }
.workflow-copy strong { color: $color-text-primary; font-size: 13px; }
.workflow-copy > span { color: $color-text-secondary; font-size: 12px; font-weight: 550; }

.profile-readiness {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: auto;
  padding: 15px;
  border: 1px solid rgba($color-sage, .16);
  border-radius: $radius-md;
  background: rgba($color-card, .52);
}

.readiness-dot {
  width: 10px;
  height: 10px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: $color-butter;
  box-shadow: 0 0 0 6px rgba($color-butter, .1);
}

.profile-readiness.ready .readiness-dot {
  background: $color-sage;
  box-shadow: 0 0 0 6px rgba($color-sage, .12);
}

.profile-readiness div { display: grid; gap: 2px; }
.profile-readiness strong { color: $color-text-primary; font-size: 12px; }
.profile-readiness div span { color: $color-text-secondary; font-size: 12px; }

.prompt-card {
  grid-column: span 8;
  padding: clamp(28px, 4vw, 52px);
  border-radius: $radius-xl;
  background: rgba($color-card, .96);
  box-shadow: $shadow-md;
}

.prompt-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 34px;
}

.prompt-heading h2 {
  margin-top: 10px;
  font-size: clamp(28px, 3vw, 40px);
  letter-spacing: -.045em;
  line-height: 1.12;
}

.prompt-heading p {
  max-width: 34rem;
  margin-top: 10px;
  color: $color-text-secondary;
  font-size: 14px;
}

.time-badge {
  flex: 0 0 auto;
  padding: 8px 12px;
  border: 1px solid rgba($color-sage, .14);
  border-radius: 999px;
  background: $color-lime-soft;
  color: $color-sage-dark;
  font-size: 12px;
  font-weight: 750;
}

.profile-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr)) auto;
  align-items: stretch;
  gap: 8px;
  margin: -8px 0 30px;
  padding: 10px;
  border: 1px solid rgba($color-sage, .13);
  border-radius: $radius-md;
  background: $color-surface-soft;
}
.profile-summary > div { display: grid; gap: 3px; min-width: 0; padding: 9px 10px; }
.profile-summary span { color: $color-text-placeholder; font-size: 12px; font-weight: 700; }
.profile-summary strong { overflow: hidden; color: $color-text-primary; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.profile-summary button { min-height: 44px; padding: 8px 12px; border: 0; border-radius: $radius-sm; background: $color-card; color: $color-sage-dark; cursor: pointer; font: inherit; font-size: 13px; font-weight: 750; }

.section-label {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: $color-text-primary;
  font-size: 14px;
  font-weight: 750;
}

.section-label > span {
  display: grid;
  width: 26px;
  height: 26px;
  place-items: center;
  border-radius: 9px;
  background: $color-sage-dark;
  color: #fff;
  font-size: 12px;
  letter-spacing: .04em;
}

.plan-input { margin-top: 12px; }

.plan-input :deep(.el-textarea__inner) {
  min-height: 206px !important;
  padding: 20px 22px 34px;
  border: 1px solid transparent;
  border-radius: $radius-md;
  background: $color-surface-soft;
  font-size: 15px;
  line-height: 1.75;
  resize: vertical;
  box-shadow: none !important;
}

.plan-input :deep(.el-textarea__inner:hover) {
  border-color: rgba($color-sage, .3);
}

.plan-input :deep(.el-textarea__inner:focus) {
  border-color: $color-sage;
  background: #fff;
  box-shadow: 0 0 0 4px rgba($color-sage, .1) !important;
}

.plan-input :deep(.el-input__count) {
  right: 16px;
  bottom: 10px;
  background: transparent;
  color: $color-text-placeholder;
}

.constraint-hint {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  margin-top: 10px;
  color: $color-text-secondary;
  font-size: 12px;
  line-height: 1.65;
}

.constraint-hint span { color: $color-rose; }

.examples { margin-top: 34px; }

.section-heading,
.controls-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 13px;
}

.section-heading > div { display: flex; align-items: center; gap: 10px; }
.section-heading small,
.controls-heading small { color: $color-text-secondary; font-size: 12px; }

.example-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.example-tag {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-height: 62px;
  padding: 11px 13px;
  border: 1px solid $color-border;
  border-radius: $radius-sm;
  background: #fff;
  color: $color-text-primary;
  cursor: pointer;
  text-align: left;
  transition: border-color .2s ease, background-color .2s ease, transform .2s ease;
}

.example-tag:hover {
  border-color: rgba($color-sage, .5);
  transform: translateY(-2px);
}

.example-tag.active {
  border-color: $color-sage;
  background: $color-lime-soft;
}

.example-index {
  color: $color-rose-dark;
  font-size: 12px;
  font-weight: 800;
}

.example-copy {
  overflow: hidden;
  font-size: 13px;
  line-height: 1.45;
  text-overflow: ellipsis;
}

.example-tag .el-icon { color: $color-sage; font-size: 15px; }

.local-context {
  margin-top: 34px;
  padding: 20px;
  border: 1px solid rgba($color-sage, .14);
  border-radius: $radius-md;
  background: linear-gradient(145deg, rgba($color-lime-soft, .55), rgba($color-surface-warm, .62));
}

.pantry-entry { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; }
.field-label { display: block; color: $color-text-primary; font-size: 14px; font-weight: 700; }
.pantry-entry .field-label { grid-column: 1 / -1; }
.local-context > .field-label { margin-top: 17px; }
.pantry-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.pantry-tags button {
  min-height: 38px;
  padding: 7px 11px;
  border: 1px solid rgba($color-sage, .24);
  border-radius: $radius-round;
  background: $color-card;
  color: $color-sage-dark;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
}
.pantry-tags button span { margin-left: 7px; color: $color-text-placeholder; }
.preference-input { margin-top: 8px; }
.preference-input :deep(.el-textarea__inner) { border-radius: $radius-sm; background: rgba($color-card, .9); font-size: 14px; line-height: 1.65; }

.controls-panel {
  margin-top: 34px;
  padding: 20px;
  border: 1px solid rgba($color-sage, .1);
  border-radius: $radius-md;
  background: $color-surface-soft;
}

.options-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.option-item {
  display: grid;
  align-content: start;
  gap: 8px;
  min-width: 0;
  padding: 15px;
  border: 0;
  border-radius: $radius-sm;
  background: rgba($color-card, .86);
}

.option-item legend,
.option-item > label {
  color: $color-text-primary;
  font-size: 12px;
  font-weight: 750;
}

.option-item > span {
  color: $color-text-secondary;
  font-size: 12px;
}

.days-option .el-radio-group { display: flex; width: 100%; }
.days-option :deep(.el-radio-button) { flex: 1; }
.days-option :deep(.el-radio-button__inner) {
  width: 100%;
  justify-content: center;
  padding-inline: 10px;
  background: transparent;
}

.budget-input { width: 100%; }
.budget-input :deep(.el-input__wrapper) { background: transparent; }

.request-review {
  margin-top: 26px;
  padding: 20px;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  background: $color-surface-soft;
}

.request-review h3 { margin: 0; }
.review-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin: 18px 0 0; }
.review-grid > div { min-width: 0; padding: 12px 14px; border-radius: $radius-sm; background: $color-card; }
.review-grid .review-request { grid-column: 1 / -1; }
.review-grid dt { margin-bottom: 5px; color: $color-text-secondary; font-size: 12px; }
.review-grid dd { margin: 0; overflow-wrap: anywhere; color: $color-text-primary; font-size: 14px; font-weight: 650; line-height: 1.6; }
.review-note { margin: 14px 0 0; color: $color-text-secondary; font-size: 13px; line-height: 1.65; }

.error-stack {
  display: grid;
  gap: 8px;
  margin-top: 18px;
}

.submit-error {
  padding: 11px 13px;
  border: 1px solid rgba($color-danger, .16);
  border-radius: $radius-sm;
  background: rgba($color-danger, .07);
  color: $color-danger;
  font-size: 12px;
}

.submit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 22px;
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid $color-divider;
}

.profile-hint {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.hint-check {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  background: $color-surface-warm;
  color: $color-warning;
  font-size: 13px;
  font-weight: 900;
}

.hint-check.ready { background: $color-lime-soft; color: $color-sage-dark; }
.profile-hint > span:last-child { display: grid; gap: 1px; min-width: 0; }
.profile-hint strong { color: $color-text-primary; font-size: 13px; }
.profile-hint small { color: $color-text-secondary; font-size: 12px; }

.submit-btn {
  flex: 0 0 auto;
  min-width: 226px;
  font-size: 14px;
}

.submit-btn .el-icon { margin-inline: 3px; }

@media (max-width: $breakpoint-lg) {
  .planning-workspace { grid-template-columns: 1fr; }

  .intro-panel,
  .prompt-card { grid-column: auto; }

  .intro-panel {
    position: relative;
    top: auto;
    min-height: auto;
  }

  .intro-desc { max-width: 48rem; }

  .workflow-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    margin-top: 28px;
  }

  .workflow-list li {
    align-items: flex-start;
    padding: 14px;
    border: 1px solid rgba($color-sage, .15);
    border-radius: $radius-sm;
    background: rgba($color-card, .46);
  }

  .profile-readiness { margin-top: 24px; }
}

@media (max-width: $breakpoint-sm) {
  .plan-new-page { padding-block: 24px 56px; }
  .planning-workspace { gap: 16px; }

  .intro-panel {
    padding: 26px 22px;
    border-radius: $radius-lg;
  }

  .intro-title { margin-top: 16px; font-size: 35px; }
  .intro-title br { display: none; }
  .intro-desc { margin-top: 14px; font-size: 13px; line-height: 1.7; }

  .workflow-list { grid-template-columns: 1fr; gap: 7px; margin-top: 22px; }
  .workflow-list li { align-items: center; padding: 10px 12px; }
  .workflow-index { width: 30px; height: 30px; border-radius: 10px; }
  .workflow-copy > span { display: none; }
  .profile-readiness { margin-top: 16px; padding: 12px; }

  .prompt-card {
    padding: 24px 18px;
    border-radius: $radius-lg;
  }

  .prompt-heading { flex-direction: column; gap: 13px; margin-bottom: 28px; }
  .prompt-heading h2 { font-size: 29px; }
  .prompt-heading p { font-size: 13px; }
  .time-badge { align-self: flex-start; }
  .profile-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 0; }
  .profile-summary button { grid-column: 1 / -1; }

  .plan-input :deep(.el-textarea__inner) {
    min-height: 180px !important;
    padding: 17px 16px 32px;
    font-size: 14px;
  }

  .examples,
  .controls-panel { margin-top: 28px; }

  .section-heading > div,
  .controls-heading { align-items: flex-start; flex-direction: column; gap: 5px; }
  .example-grid,
  .options-row { grid-template-columns: 1fr; }
  .example-tag { min-height: 56px; }

  .controls-panel { padding: 15px; }
  .option-item { padding: 13px; }
  .request-review { padding: 15px; }
  .review-grid { grid-template-columns: 1fr; }

  .submit-row {
    align-items: stretch;
    flex-direction: column;
    gap: 16px;
  }

  .submit-btn { width: 100%; min-width: 0; }
}

@media (max-width: $breakpoint-sm) {
  .pantry-entry { grid-template-columns: 1fr; }
  .pantry-entry .el-button { width: 100%; }
}
</style>
