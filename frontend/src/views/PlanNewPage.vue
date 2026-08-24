<script setup lang="ts">
import { ref, computed, onMounted, useId } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { usePlanStore } from '@/stores/plan'
import { useProfileStore } from '@/stores/profile'
import { MagicStick, Right } from '@element-plus/icons-vue'

const router = useRouter()
const planStore = usePlanStore()
const profileStore = useProfileStore()

const {
  draftInput: userInput,
  draftDurationDays: durationDays,
  draftTotalBudget: totalBudget,
  draftExampleIndex: activeExample,
} = storeToRefs(planStore)
const submitting = ref(false)
const submitError = ref('')
const profileLoadError = ref('')
const inputId = useId()
const budgetId = useId()

const examples = [
  { text: '减脂一周，预算300元，家里有鸡蛋和番茄', days: 7, budget: 300 },
  { text: '增肌三天，预算200，高蛋白饮食', days: 3, budget: 200 },
  { text: '健康饮食五天，预算500，不吃海鲜', days: 5, budget: 500 },
  { text: '控糖一周，预算400，已有鸡胸肉和西兰花', days: 7, budget: 400 },
]

const profileExists = computed(() => profileStore.hasProfile)

onMounted(async () => {
  if (!profileStore.profile) {
    try {
      await profileStore.fetchMyProfile()
    } catch (e: unknown) {
      profileLoadError.value = e instanceof Error ? e.message : '健康画像加载失败'
    }
  }
})

function selectExample(i: number) {
  activeExample.value = i
  userInput.value = examples[i].text
  durationDays.value = examples[i].days
  totalBudget.value = examples[i].budget
}

async function submit() {
  submitError.value = ''
  if (!userInput.value.trim()) {
    submitError.value = '请先描述你的饮食目标或限制'
    return
  }
  if (userInput.value.trim().length < 6) {
    submitError.value = '描述再具体一点，例如目标、预算或忌口'
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
    const res = await planStore.create(
      userInput.value.trim(),
      durationDays.value,
      totalBudget.value || 0,
      profileId,
    )
    planStore.clearDraft()
    router.push(`/plan/${res.plan_id}`)
  } catch (e: any) {
    submitError.value = e?.message || '创建失败，请检查网络后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="plan-new-page page-container">
    <div class="hero-section">
      <h1 class="page-title">创建饮食规划</h1>
      <p class="page-desc">描述你的需求，AI 为你量身定制方案</p>
    </div>

    <form class="input-card card" novalidate @submit.prevent="submit">
      <!-- 输入框 -->
      <div class="input-area">
        <label class="input-label" :for="inputId">告诉 AI 你的需求</label>
        <el-input
          :id="inputId"
          v-model="userInput"
          type="textarea"
          :rows="4"
          placeholder="例如：减脂一周，预算300元，家里有鸡蛋和番茄"
          maxlength="500"
          show-word-limit
          class="plan-input"
        />
        <p class="constraint-hint">文本中明确写出的天数、预算和忌口会优先生效；下方选项可用于核对。</p>
      </div>

      <!-- 快捷示例 -->
      <div class="examples">
        <span class="examples-label">试试这些：</span>
        <div class="example-chips">
          <button
            v-for="(ex, i) in examples"
            :key="i"
            class="example-tag"
            :class="{ active: activeExample === i }"
            type="button"
            @click="selectExample(i)"
          >
            <el-icon><MagicStick /></el-icon>
            {{ ex.text.slice(0, 20) }}...
          </button>
        </div>
      </div>

      <!-- 选项 -->
      <div class="options-row">
        <div class="option-item">
          <label>规划天数</label>
          <el-radio-group v-model="durationDays" size="small">
            <el-radio-button :value="3">3天</el-radio-button>
            <el-radio-button :value="5">5天</el-radio-button>
            <el-radio-button :value="7">7天</el-radio-button>
          </el-radio-group>
        </div>
        <div class="option-item">
          <label :for="budgetId">预算（元）</label>
          <el-input-number :id="budgetId" v-model="totalBudget" :min="0" :max="9999" :step="50"
            size="small" controls-position="right" style="width: 140px"
            placeholder="不限制" />
        </div>
      </div>

      <div class="submit-row">
        <p class="profile-hint" v-if="profileStore.loading">正在检查健康画像…</p>
        <p class="profile-hint" v-else-if="!profileExists">
          需要先完成健康画像，才能生成准确方案
        </p>
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
          {{ submitting ? 'AI 规划中...' : '开始规划' }}
          <el-icon v-if="!submitting"><Right /></el-icon>
        </el-button>
      </div>
      <p v-if="submitError" class="submit-error" role="alert">{{ submitError }}</p>
      <p v-if="profileLoadError" class="submit-error" role="alert">{{ profileLoadError }}</p>
    </form>
  </div>
</template>

<style scoped lang="scss">
.plan-new-page {
  padding: 48px 20px;
  max-width: 680px;
}

.hero-section {
  text-align: center;
  margin-bottom: 36px;
}

.page-title {
  font-size: 32px;
  font-weight: 700;
  color: $color-text-primary;
  margin-bottom: 8px;
}

.page-desc {
  font-size: 16px;
  color: $color-text-secondary;
}

.input-card {
  padding: 36px;
}

.input-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 8px;
}

.plan-input {
  :deep(.el-textarea__inner) {
    border-radius: $radius-md;
    font-size: 15px;
    line-height: 1.6;
    padding: 14px 16px;
    resize: none;
  }
}

.constraint-hint { margin-top: 8px; color: $color-text-secondary; font-size: 12px; }

// ── 快捷示例 ─────────────────────────────

.examples {
  margin-top: 16px;
}

.examples-label {
  font-size: 13px;
  color: $color-text-secondary;
  margin-bottom: 8px;
  display: block;
}

.example-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.example-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 32px;
  padding: 5px 11px;
  border: 1px solid $color-border;
  border-radius: 999px;
  background: $color-card;
  color: $color-text-secondary;
  font: inherit;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    transform: translateY(-1px);
  }

  &.active { border-color: $color-sage; background: rgba($color-sage, .1); color: $color-sage-dark; }
}

// ── 选项 ─────────────────────────────────

.options-row {
  display: flex;
  gap: 24px;
  margin-top: 24px;
  flex-wrap: wrap;

  @media (max-width: $breakpoint-sm) {
    flex-direction: column;
    gap: 16px;
  }
}

.option-item {
  display: flex;
  align-items: center;
  gap: 12px;

  label {
    font-size: 14px;
    font-weight: 500;
    color: $color-text-primary;
    white-space: nowrap;
  }
}

// ── 提交 ─────────────────────────────────

.submit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 28px;

  @media (max-width: $breakpoint-sm) {
    flex-direction: column;
    gap: 12px;
  }
}

.profile-hint {
  font-size: 12px;
  color: $color-text-placeholder;
}

.submit-btn {
  padding-left: 24px;
  padding-right: 24px;
  font-size: 15px;

  .el-icon {
    margin: 0 4px;
  }
}

.submit-error {
  margin-top: 16px;
  padding: 10px 12px;
  border-radius: $radius-sm;
  background: rgba($color-danger, 0.1);
  color: $color-danger;
  font-size: 13px;
}

@media (max-width: $breakpoint-sm) {
  .plan-new-page { padding-top: 32px; }
  .input-card { padding: 24px 18px; }
  .submit-btn { width: 100%; min-height: 46px; }
}
</style>
