<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProfileStore } from '@/stores/profile'
import { Check, Right } from '@element-plus/icons-vue'
import PremiumIcon from '@/components/common/PremiumIcon.vue'

const router = useRouter()
const store = useProfileStore()

const currentStep = ref(0)
const form = ref({ ...store.defaultForm })
const submitting = ref(false)
const submitError = ref('')
const initialError = ref('')

onMounted(async () => {
  try {
    const existing = await store.fetchMyProfile()
    if (existing) {
      form.value = {
        age: existing.age, gender: existing.gender, height: existing.height, weight: existing.weight,
        activity_level: existing.activity_level || 'moderate',
        diet_type: existing.diet_type, health_goal: existing.health_goal,
        allergies: existing.allergies || [], daily_budget: existing.daily_budget,
      }
    }
  } catch (e: unknown) {
    initialError.value = e instanceof Error ? e.message : '健康画像加载失败，请刷新重试'
  }
})

// BMI/TDEE 实时计算
const computedBmi = computed(() => {
  if (!form.value.height || !form.value.weight) return null
  const h = form.value.height / 100
  return (form.value.weight / (h * h)).toFixed(1)
})

const computedTdee = computed(() => {
  if (!form.value.height || !form.value.weight || !form.value.age || !form.value.gender) return null
  const bmr = form.value.gender === 'male'
    ? 10 * form.value.weight + 6.25 * form.value.height - 5 * form.value.age + 5
    : 10 * form.value.weight + 6.25 * form.value.height - 5 * form.value.age - 161
  const factors = { sedentary: 1.2, light: 1.375, moderate: 1.55, active: 1.725, extra: 1.9 }
  return Math.round(bmr * factors[form.value.activity_level])
})

const steps = [
  { title: '基本信息', desc: '年龄、性别、身体数据' },
  { title: '健康目标', desc: '你想达成什么效果？' },
  { title: '饮食偏好', desc: '饮食习惯与限制' },
  { title: '预算确认', desc: '每日预算与完成' },
]

const healthGoalLabels: Record<string, string> = {
  fat_loss: '减脂',
  muscle_gain: '增肌',
  blood_sugar: '控糖',
  healthy: '健康',
}

const dietTypeLabels: Record<string, string> = {
  balanced: '均衡',
  keto: '生酮',
  high_protein: '高蛋白',
  gluten_free: '无麸质',
  vegan: '素食',
  healthy: '健康',
}

const activityLabels: Record<string, string> = {
  sedentary: '久坐', light: '轻度活动', moderate: '中度活动', active: '高强度活动', extra: '极高强度活动',
}

function nextStep() {
  if (currentStep.value < steps.length - 1) currentStep.value++
}

function prevStep() {
  if (currentStep.value > 0) currentStep.value--
}

async function submitForm() {
  submitError.value = ''
  if (!form.value.age || !form.value.gender || !form.value.height || !form.value.weight) {
    submitError.value = '请补全年龄、性别、身高和体重'
    currentStep.value = 0
    return
  }
  submitting.value = true
  try {
    const payload = {
      ...form.value,
      daily_budget: form.value.daily_budget ?? 0,
    }
    if (store.profile) await store.updateProfile(store.profile.profile_id, payload as any)
    else await store.saveProfile(payload as any)
    router.push('/plan/new')
  } catch (e: unknown) {
    submitError.value = e instanceof Error ? e.message : '画像保存失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="profile-page page-container">
    <header class="profile-heading">
      <span>用于估算热量与筛选约束</span>
      <h1>{{ store.profile ? '更新健康画像' : '创建健康画像' }}</h1>
      <p>信息只用于生成更贴合你的饮食方案，之后可以随时修改。</p>
    </header>
    <p v-if="store.loading && !submitting" class="status-message" aria-live="polite">正在加载已有画像…</p>
    <p v-if="initialError" class="submit-error" role="alert">{{ initialError }}</p>
    <div class="mobile-progress" aria-live="polite">
      <div>
        <strong>步骤 {{ currentStep + 1 }}/{{ steps.length }}</strong>
        <span>{{ steps[currentStep].title }}</span>
      </div>
      <el-progress :percentage="((currentStep + 1) / steps.length) * 100" :show-text="false" />
    </div>
    <!-- 步骤指示器 -->
    <div class="stepper">
      <div
        v-for="(s, i) in steps"
        :key="i"
        class="step-item"
        :class="{ active: currentStep === i, done: currentStep > i }"
      >
        <div class="step-circle">
          <el-icon v-if="currentStep > i"><Check /></el-icon>
          <span v-else>{{ i + 1 }}</span>
        </div>
        <div class="step-info">
          <div class="step-title">{{ s.title }}</div>
          <div class="step-desc">{{ s.desc }}</div>
        </div>
        <div v-if="i < steps.length - 1" class="step-line" :class="{ active: currentStep > i }" />
      </div>
    </div>

    <!-- 表单卡片 -->
    <div class="form-card card">
      <!-- Step 0: 基本信息 -->
      <div v-show="currentStep === 0" class="step-panel">
        <h2 class="panel-title">基本信息</h2>
        <p class="panel-desc">让我们先了解你的身体数据</p>
        <el-form label-position="top" class="profile-form">
          <el-form-item label="年龄" required>
            <el-input-number v-model="form.age" :min="1" :max="150" controls-position="right" style="width: 100%" />
          </el-form-item>
          <el-form-item label="性别" required>
            <el-radio-group v-model="form.gender">
              <el-radio-button value="male">男性</el-radio-button>
              <el-radio-button value="female">女性</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="身高 (cm)" required>
                <el-input-number v-model="form.height" :min="50" :max="250" :step="0.5" controls-position="right" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="体重 (kg)" required>
                <el-input-number v-model="form.weight" :min="10" :max="300" :step="0.5" controls-position="right" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="日常活动水平" required>
            <el-select v-model="form.activity_level" style="width: 100%">
              <el-option label="久坐（几乎不运动）" value="sedentary" />
              <el-option label="轻度活动（每周 1–3 次）" value="light" />
              <el-option label="中度活动（每周 3–5 次）" value="moderate" />
              <el-option label="高强度活动（每周 6–7 次）" value="active" />
              <el-option label="极高强度活动（高体力工作或双练）" value="extra" />
            </el-select>
          </el-form-item>

          <div v-if="computedBmi" class="calc-preview">
            <span class="calc-item">BMI: <strong>{{ computedBmi }}</strong></span>
            <span class="calc-item">估算每日消耗: <strong>{{ computedTdee }} kcal</strong></span>
          </div>

          <div class="step-actions">
            <el-button type="primary" round @click="nextStep" :disabled="!form.age || !form.gender || !form.height || !form.weight">
              下一步 <el-icon><Right /></el-icon>
            </el-button>
          </div>
        </el-form>
      </div>

      <!-- Step 1: 健康目标 -->
      <div v-show="currentStep === 1" class="step-panel">
        <h2 class="panel-title">健康目标</h2>
        <p class="panel-desc">你希望达成什么效果？</p>
        <el-radio-group v-model="form.health_goal" class="goal-group">
          <el-radio value="fat_loss" class="goal-card">
            <PremiumIcon name="flame" class="goal-icon" :size="34" :box-size="66" />
            <span class="goal-text">减脂</span>
            <span class="goal-sub">减少体脂，塑造线条</span>
          </el-radio>
          <el-radio value="muscle_gain" class="goal-card">
            <PremiumIcon name="strength" class="goal-icon" :size="34" :box-size="66" />
            <span class="goal-text">增肌</span>
            <span class="goal-sub">增加肌肉，提升力量</span>
          </el-radio>
          <el-radio value="blood_sugar" class="goal-card">
            <PremiumIcon name="blood" class="goal-icon" :size="34" :box-size="66" />
            <span class="goal-text">控糖</span>
            <span class="goal-sub">稳定血糖，健康饮食</span>
          </el-radio>
          <el-radio value="healthy" class="goal-card">
            <PremiumIcon name="leaf" class="goal-icon" :size="34" :box-size="66" />
            <span class="goal-text">健康饮食</span>
            <span class="goal-sub">均衡营养，维持健康</span>
          </el-radio>
        </el-radio-group>
        <div class="step-actions">
          <el-button round @click="prevStep">上一步</el-button>
          <el-button type="primary" round @click="nextStep">
            下一步 <el-icon><Right /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- Step 2: 饮食偏好 -->
      <div v-show="currentStep === 2" class="step-panel">
        <h2 class="panel-title">饮食偏好</h2>
        <p class="panel-desc">选择你的饮食习惯和限制</p>
        <el-form label-position="top">
          <el-form-item label="饮食类型">
            <el-select v-model="form.diet_type" style="width: 100%">
              <el-option label="均衡饮食" value="balanced" />
              <el-option label="生酮饮食" value="keto" />
              <el-option label="高蛋白饮食" value="high_protein" />
              <el-option label="无麸质饮食" value="gluten_free" />
              <el-option label="素食" value="vegan" />
              <el-option label="健康饮食" value="healthy" />
            </el-select>
          </el-form-item>
          <el-form-item label="过敏原 / 必须排除">
            <el-select v-model="form.allergies" multiple filterable allow-create default-first-option
              style="width: 100%" placeholder="输入食物名称后回车添加">
              <el-option label="海鲜" value="海鲜" />
              <el-option label="花生" value="花生" />
              <el-option label="牛奶" value="牛奶" />
              <el-option label="鸡蛋" value="鸡蛋" />
              <el-option label="大豆" value="大豆" />
              <el-option label="麸质" value="麸质" />
              <el-option label="坚果" value="坚果" />
            </el-select>
            <p class="safety-hint">严重食物过敏请同时核对配料与交叉污染风险；本工具不能替代医生或营养师建议。</p>
          </el-form-item>
        </el-form>
        <div class="step-actions">
          <el-button round @click="prevStep">上一步</el-button>
          <el-button type="primary" round @click="nextStep">
            下一步 <el-icon><Right /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- Step 3: 预算 -->
      <div v-show="currentStep === 3" class="step-panel">
        <h2 class="panel-title">预算与确认</h2>
        <p class="panel-desc">最后一步，设定每日预算</p>
        <el-form label-position="top">
          <el-form-item label="每日预算（元，选填）">
            <el-input-number v-model="form.daily_budget" :min="0" :max="500" :step="10"
              controls-position="right" style="width: 100%" placeholder="不设置则无限" />
          </el-form-item>
        </el-form>

        <div class="summary-card">
          <h4>你的画像概览</h4>
          <div class="summary-grid">
            <div><span>年龄</span><strong>{{ form.age || '-' }}</strong></div>
            <div><span>性别</span><strong>{{ form.gender === 'male' ? '男性' : form.gender === 'female' ? '女性' : '-' }}</strong></div>
            <div><span>身高/体重</span><strong>{{ form.height || '-' }}cm / {{ form.weight || '-' }}kg</strong></div>
            <div><span>每日消耗</span><strong>{{ computedTdee || '-' }} kcal</strong></div>
            <div><span>活动水平</span><strong>{{ activityLabels[form.activity_level] }}</strong></div>
            <div><span>健康目标</span><strong>{{ healthGoalLabels[form.health_goal] }}</strong></div>
            <div><span>饮食类型</span><strong>{{ dietTypeLabels[form.diet_type] }}</strong></div>
          </div>
        </div>

        <div class="step-actions">
          <el-button round @click="prevStep">上一步</el-button>
          <el-button type="primary" round :loading="submitting" @click="submitForm">
            完成创建 <el-icon><Check /></el-icon>
          </el-button>
        </div>
        <p v-if="submitError" class="submit-error" role="alert">{{ submitError }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.profile-page {
  padding: 40px 20px;
  max-width: 680px;
}

.profile-heading { margin-bottom: 28px; text-align: center; }
.profile-heading span { color: $color-sage-dark; font-size: 13px; font-weight: 700; letter-spacing: .06em; }
.profile-heading h1 { margin: 6px 0; color: $color-text-primary; font-size: 32px; }
.profile-heading p, .status-message { color: $color-text-secondary; font-size: 14px; }
.status-message { margin-bottom: 14px; text-align: center; }
.safety-hint { margin-top: 8px; color: $color-text-secondary; font-size: 12px; line-height: 1.6; }

.mobile-progress { display: none; }

.submit-error {
  margin-top: 14px;
  padding: 10px 12px;
  border-radius: $radius-sm;
  background: rgba($color-danger, .1);
  color: $color-danger;
  font-size: 13px;
}

// ── 步骤条 ───────────────────────────────

.stepper {
  display: flex;
  gap: 0;
  margin-bottom: 40px;
  padding: 0 20px;

  @media (max-width: $breakpoint-sm) {
    display: none;
  }
}

@media (max-width: $breakpoint-sm) {
  .profile-page { padding-top: 28px; }
  .mobile-progress { display: grid; gap: 10px; margin-bottom: 18px; }
  .mobile-progress > div { display: flex; align-items: center; justify-content: space-between; }
  .mobile-progress strong { color: $color-text-primary; font-size: 14px; }
  .mobile-progress span { color: $color-text-secondary; font-size: 13px; }
  .step-actions .el-button { min-height: 44px; }
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex: 1;
  position: relative;
}

.step-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: $color-border;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: $color-text-secondary;
  flex-shrink: 0;
  transition: all 0.3s;

  .active & {
    background: $color-sage;
    color: #fff;
    box-shadow: 0 0 0 4px rgba($color-sage, 0.2);
  }

  .done & {
    background: $color-sage-light;
    color: $color-sage-dark;
  }
}

.step-info {
  .step-title {
    font-size: 14px;
    font-weight: 600;
    color: $color-text-secondary;
    transition: color 0.3s;

    .active & { color: $color-sage-dark; }
    .done & { color: $color-sage; }
  }

  .step-desc {
    font-size: 12px;
    color: $color-text-placeholder;
  }
}

.step-line {
  position: absolute;
  top: 16px;
  left: 44px;
  right: 0;
  height: 2px;
  background: $color-border;
  transform: translateY(-50%);

  &.active {
    background: $color-sage-light;
  }
}

// ── 表单卡片 ─────────────────────────────

.form-card {
  padding: 40px;

  @media (max-width: $breakpoint-sm) {
    padding: 24px;
  }
}

.panel-title {
  font-size: 24px;
  font-weight: 700;
  color: $color-text-primary;
  margin-bottom: 4px;
}

.panel-desc {
  font-size: 14px;
  color: $color-text-secondary;
  margin-bottom: 28px;
}

.profile-form {
  max-width: 400px;
}

.calc-preview {
  display: flex;
  gap: 20px;
  padding: 12px 16px;
  background: rgba($color-sage, 0.06);
  border-radius: $radius-md;
  margin-bottom: 24px;

  .calc-item {
    font-size: 14px;
    color: $color-text-secondary;

    strong {
      color: $color-sage-dark;
    }
  }
}

// ── 健康目标卡片选择 ─────────────────────

.goal-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  width: 100%;

  @media (max-width: $breakpoint-sm) {
    grid-template-columns: 1fr;
  }
}

.goal-card {
  display: flex !important;
  flex-direction: column;
  align-items: center;
  padding: 24px 16px !important;
  border-radius: $radius-md !important;
  border: 2px solid $color-border !important;
  height: auto !important;
  margin-right: 0 !important;
  transition: all 0.2s;
  text-align: center;

  &:hover {
    border-color: $color-sage-light !important;
  }

  &.is-checked {
    border-color: $color-sage !important;
    background: rgba($color-sage, 0.06) !important;
  }
}

.goal-icon {
  margin: 0 auto 10px;
}

.goal-text {
  font-size: 16px;
  font-weight: 600;
  color: $color-text-primary;
}

.goal-sub {
  font-size: 12px;
  color: $color-text-secondary;
  margin-top: 4px;
}

// ── 操作按钮 ─────────────────────────────

.step-actions {
  display: flex;
  gap: 12px;
  margin-top: 32px;
  justify-content: flex-end;
}

// ── 概览卡片 ─────────────────────────────

.summary-card {
  background: rgba($color-sage, 0.06);
  border-radius: $radius-md;
  padding: 20px;
  margin-top: 16px;

  h4 {
    font-size: 16px;
    font-weight: 600;
    color: $color-text-primary;
    margin-bottom: 16px;
  }
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;

  div {
    display: flex;
    flex-direction: column;
    gap: 2px;

    span {
      font-size: 12px;
      color: $color-text-secondary;
    }

    strong {
      font-size: 14px;
      color: $color-text-primary;
    }
  }
}
</style>
