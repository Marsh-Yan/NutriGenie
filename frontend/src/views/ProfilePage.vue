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
      <div class="heading-copy">
        <span class="eyebrow">Personal nutrition profile</span>
        <h1>{{ store.profile ? '更新你的健康画像' : '先从了解你开始' }}</h1>
        <p>用几项基础信息建立营养边界，让每一次推荐都更贴近你的身体、偏好与生活节奏。</p>
      </div>
      <div class="heading-meta" aria-label="填写说明">
        <span><strong>4</strong> 个简单步骤</span>
        <span><strong>≈ 2</strong> 分钟完成</span>
      </div>
    </header>

    <p v-if="store.loading && !submitting" class="status-message" aria-live="polite"><i /> 正在加载已有画像…</p>
    <p v-if="initialError" class="submit-error" role="alert">{{ initialError }}</p>

    <div class="mobile-progress card" aria-live="polite">
      <div class="mobile-progress-copy">
        <span>步骤 {{ currentStep + 1 }} / {{ steps.length }}</span>
        <strong>{{ steps[currentStep].title }}</strong>
      </div>
      <el-progress :percentage="((currentStep + 1) / steps.length) * 100" :show-text="false" />
    </div>

    <div class="profile-workspace">
      <aside class="profile-rail card" aria-label="健康画像填写进度">
        <div class="rail-heading">
          <PremiumIcon name="profile" class="rail-icon" :size="22" :box-size="44" />
          <div>
            <strong>你的画像</strong>
            <span>随填写实时更新</span>
          </div>
        </div>

        <div class="stepper">
          <div
            v-for="(s, i) in steps"
            :key="i"
            class="step-item"
            :class="{ active: currentStep === i, done: currentStep > i }"
          >
            <div class="step-circle">
              <el-icon v-if="currentStep > i"><Check /></el-icon>
              <span v-else>{{ String(i + 1).padStart(2, '0') }}</span>
            </div>
            <div class="step-info">
              <div class="step-title">{{ s.title }}</div>
              <div class="step-desc">{{ s.desc }}</div>
            </div>
            <div v-if="i < steps.length - 1" class="step-line" :class="{ active: currentStep > i }" />
          </div>
        </div>

        <div class="rail-snapshot">
          <div class="snapshot-heading">
            <span>实时估算</span>
            <i aria-hidden="true" />
          </div>
          <div class="snapshot-metrics">
            <span><small>BMI</small><strong>{{ computedBmi || '—' }}</strong></span>
            <span><small>每日消耗</small><strong>{{ computedTdee ? `${computedTdee}` : '—' }}<small v-if="computedTdee"> kcal</small></strong></span>
          </div>
          <p>这里展示的是基础估算值，最终方案还会结合你的目标与饮食限制。</p>
        </div>
      </aside>

      <main class="form-card card">
        <div v-show="currentStep === 0" class="step-panel">
          <span class="panel-step-label">STEP 01 · BODY BASICS</span>
          <h2 class="panel-title">基本信息</h2>
          <p class="panel-desc">这些数据用于估算基础代谢与每日能量消耗。</p>
          <el-form label-position="top" class="profile-form">
            <el-row :gutter="20">
              <el-col :xs="24" :sm="12">
                <el-form-item label="年龄" required>
                  <el-input-number v-model="form.age" :min="1" :max="150" controls-position="right" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12">
                <el-form-item label="性别" required>
                  <el-radio-group v-model="form.gender" class="gender-toggle">
                    <el-radio-button value="male">男性</el-radio-button>
                    <el-radio-button value="female">女性</el-radio-button>
                  </el-radio-group>
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12">
              <el-form-item label="身高 (cm)" required>
                <el-input-number v-model="form.height" :min="50" :max="250" :step="0.5" controls-position="right" style="width: 100%" />
              </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="12">
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
              <span class="calc-item"><small>当前 BMI</small><strong>{{ computedBmi }}</strong></span>
              <span class="calc-item"><small>估算每日消耗</small><strong>{{ computedTdee }} <em>kcal</em></strong></span>
            </div>

            <div class="step-actions single-action">
              <el-button type="primary" round @click="nextStep" :disabled="!form.age || !form.gender || !form.height || !form.weight">
                继续选择目标 <el-icon><Right /></el-icon>
              </el-button>
            </div>
          </el-form>
        </div>

        <div v-show="currentStep === 1" class="step-panel">
          <span class="panel-step-label">STEP 02 · YOUR GOAL</span>
          <h2 class="panel-title">你最想改善什么？</h2>
          <p class="panel-desc">选择当前最重要的目标，我们会据此调整能量和营养比例。</p>
          <el-radio-group v-model="form.health_goal" class="goal-group">
            <el-radio value="fat_loss" class="goal-card">
              <PremiumIcon name="flame" class="goal-icon" :size="30" :box-size="58" />
              <span class="goal-text">减脂</span>
              <span class="goal-sub">温和控制热量，优先保证饱腹感</span>
              <span class="goal-check"><el-icon><Check /></el-icon></span>
            </el-radio>
            <el-radio value="muscle_gain" class="goal-card">
              <PremiumIcon name="strength" class="goal-icon" :size="30" :box-size="58" />
              <span class="goal-text">增肌</span>
              <span class="goal-sub">提升蛋白质与训练所需能量</span>
              <span class="goal-check"><el-icon><Check /></el-icon></span>
            </el-radio>
            <el-radio value="blood_sugar" class="goal-card">
              <PremiumIcon name="blood" class="goal-icon" :size="30" :box-size="58" />
              <span class="goal-text">控糖</span>
              <span class="goal-sub">关注碳水质量与进餐节奏</span>
              <span class="goal-check"><el-icon><Check /></el-icon></span>
            </el-radio>
            <el-radio value="healthy" class="goal-card">
              <PremiumIcon name="leaf" class="goal-icon" :size="30" :box-size="58" />
              <span class="goal-text">健康饮食</span>
              <span class="goal-sub">保持营养均衡与长期可执行性</span>
              <span class="goal-check"><el-icon><Check /></el-icon></span>
            </el-radio>
          </el-radio-group>
          <div class="step-actions">
            <el-button round @click="prevStep">上一步</el-button>
            <el-button type="primary" round @click="nextStep">
              继续设置偏好 <el-icon><Right /></el-icon>
            </el-button>
          </div>
        </div>

        <div v-show="currentStep === 2" class="step-panel">
          <span class="panel-step-label">STEP 03 · FOOD PREFERENCES</span>
          <h2 class="panel-title">尊重你的饮食习惯</h2>
          <p class="panel-desc">告诉我们常用的饮食方式，以及必须避开的食物。</p>
          <el-form label-position="top" class="panel-form">
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
              <p class="safety-hint"><strong>安全提示</strong>严重食物过敏请同时核对配料与交叉污染风险；本工具不能替代医生或营养师建议。</p>
            </el-form-item>
          </el-form>
          <div class="step-actions">
            <el-button round @click="prevStep">上一步</el-button>
            <el-button type="primary" round @click="nextStep">
              最后确认预算 <el-icon><Right /></el-icon>
            </el-button>
          </div>
        </div>

        <div v-show="currentStep === 3" class="step-panel">
          <span class="panel-step-label">STEP 04 · BUDGET & REVIEW</span>
          <h2 class="panel-title">让计划也符合日常预算</h2>
          <p class="panel-desc">设定每日预算后，系统会优先选择价格和营养更合适的组合。</p>
          <el-form label-position="top" class="panel-form">
            <div class="budget-control">
              <div>
                <strong>每日预算</strong>
                <span>选填，设为 0 表示不限制</span>
              </div>
              <el-form-item label="金额（元）">
                <el-input-number v-model="form.daily_budget" :min="0" :max="500" :step="10"
                  controls-position="right" style="width: 100%" placeholder="不设置则无限" />
              </el-form-item>
            </div>
          </el-form>

          <div class="summary-card">
            <div class="summary-heading">
              <div><span>PROFILE SUMMARY</span><h4>你的画像概览</h4></div>
              <PremiumIcon name="check" class="summary-icon" :size="18" :box-size="36" />
            </div>
            <div class="summary-grid">
              <div><span>年龄</span><strong>{{ form.age || '-' }} 岁</strong></div>
              <div><span>性别</span><strong>{{ form.gender === 'male' ? '男性' : form.gender === 'female' ? '女性' : '-' }}</strong></div>
              <div><span>身高 / 体重</span><strong>{{ form.height || '-' }}cm / {{ form.weight || '-' }}kg</strong></div>
              <div><span>每日消耗</span><strong>{{ computedTdee || '-' }} kcal</strong></div>
              <div><span>活动水平</span><strong>{{ activityLabels[form.activity_level] }}</strong></div>
              <div><span>健康目标</span><strong>{{ healthGoalLabels[form.health_goal] }}</strong></div>
              <div><span>饮食类型</span><strong>{{ dietTypeLabels[form.diet_type] }}</strong></div>
            </div>
          </div>

          <div class="step-actions">
            <el-button round @click="prevStep">上一步</el-button>
            <el-button type="primary" round :loading="submitting" @click="submitForm">
              保存并开始规划 <el-icon><Check /></el-icon>
            </el-button>
          </div>
          <p v-if="submitError" class="submit-error" role="alert">{{ submitError }}</p>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped lang="scss">
.profile-page {
  max-width: 1220px;
  padding-top: clamp(38px, 5vw, 68px);
  padding-bottom: clamp(60px, 7vw, 96px);
}

.profile-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 48px;
  margin-bottom: 36px;
}

.heading-copy { max-width: 720px; }

.heading-copy h1 {
  margin-top: 12px;
  font-size: clamp(34px, 4vw, 50px);
  font-weight: 780;
  letter-spacing: -.045em;
  line-height: 1.12;
}

.heading-copy p {
  max-width: 660px;
  margin-top: 14px;
  color: $color-text-secondary;
  font-size: 15px;
  line-height: 1.8;
}

.heading-meta {
  display: flex;
  flex: 0 0 auto;
  gap: 10px;
}

.heading-meta > span {
  display: flex;
  align-items: baseline;
  gap: 5px;
  padding: 10px 14px;
  border: 1px solid rgba($color-sage-dark, .1);
  border-radius: 999px;
  background: rgba($color-card, .76);
  color: $color-text-secondary;
  font-size: 12px;
}

.heading-meta strong { color: $color-sage-dark; font-size: 14px; }

.status-message {
  display: flex;
  align-items: center;
  gap: 9px;
  width: fit-content;
  margin-bottom: 18px;
  padding: 9px 13px;
  border-radius: 999px;
  background: rgba($color-sage, .08);
  color: $color-text-secondary;
  font-size: 12px;
}

.status-message i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: $color-sage;
  box-shadow: 0 0 0 5px rgba($color-sage, .1);
}

.submit-error {
  margin: 0 0 18px;
  padding: 11px 14px;
  border: 1px solid rgba($color-danger, .16);
  border-radius: $radius-sm;
  background: rgba($color-danger, .08);
  color: $color-danger;
  font-size: 13px;
}

.mobile-progress { display: none; }

.profile-workspace {
  display: grid;
  grid-template-columns: 286px minmax(0, 1fr);
  align-items: start;
  gap: 24px;
}

.profile-rail {
  position: sticky;
  top: 92px;
  overflow: hidden;
  padding: 26px;
  background:
    radial-gradient(circle at 100% 0, rgba($color-lime, .18), transparent 12rem),
    rgba($color-card, .94);
}

.rail-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 24px;
  border-bottom: 1px solid $color-divider;
}

.rail-icon { border-radius: 14px; box-shadow: none; }
.rail-heading > div { display: grid; gap: 1px; }
.rail-heading strong { color: $color-text-primary; font-size: 15px; }
.rail-heading span { color: $color-text-secondary; font-size: 12px; }

.stepper {
  display: grid;
  gap: 7px;
  padding: 24px 0;
}

.step-item {
  position: relative;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  min-height: 62px;
  padding: 8px 8px 8px 0;
  border-radius: $radius-sm;
}

.step-item.active {
  padding-left: 8px;
  background: rgba($color-sage, .08);
}

.step-circle {
  position: relative;
  z-index: 2;
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  border: 1px solid $color-border;
  border-radius: 50%;
  background: $color-card;
  color: $color-text-placeholder;
  font-size: 12px;
  font-weight: 800;
  transition: border-color .25s ease, background-color .25s ease, color .25s ease, box-shadow .25s ease;
}

.active .step-circle {
  border-color: $color-sage-dark;
  background: $color-sage-dark;
  color: #fff;
  box-shadow: 0 0 0 5px rgba($color-sage, .1);
}

.done .step-circle {
  border-color: rgba($color-sage, .18);
  background: $color-sage-light;
  color: $color-sage-dark;
}

.step-info { display: grid; gap: 2px; min-width: 0; }
.step-title { color: $color-text-secondary; font-size: 13px; font-weight: 750; }
.step-desc { overflow: hidden; color: $color-text-secondary; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.active .step-title { color: $color-sage-dark; }
.done .step-title { color: $color-text-primary; }

.step-line {
  position: absolute;
  top: 50px;
  bottom: -19px;
  left: 18px;
  z-index: 1;
  width: 1px;
  background: $color-border;
}

.step-item.active .step-line { left: 26px; }
.step-line.active { background: rgba($color-sage, .42); }

.rail-snapshot {
  padding: 18px;
  border: 1px solid rgba($color-sage, .16);
  border-radius: $radius-md;
  background: linear-gradient(145deg, $color-sage-light, $color-surface-warm);
  color: $color-text-primary;
}

.snapshot-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: $color-text-secondary;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .08em;
}

.snapshot-heading i { width: 7px; height: 7px; border-radius: 50%; background: $color-sage; }

.snapshot-metrics {
  display: grid;
  grid-template-columns: .72fr 1.28fr;
  gap: 8px;
  margin-top: 13px;
}

.snapshot-metrics > span {
  display: grid;
  gap: 1px;
  min-width: 0;
  padding: 10px;
  border-radius: $radius-xs;
  background: rgba($color-card, .56);
}

.snapshot-metrics small { color: $color-text-secondary; font-size: 12px; }
.snapshot-metrics strong { overflow: hidden; color: $color-text-primary; font-size: 18px; line-height: 1.35; text-overflow: ellipsis; white-space: nowrap; }
.snapshot-metrics strong small { font-size: 12px; font-weight: 600; }
.rail-snapshot p { margin-top: 12px; color: $color-text-secondary; font-size: 12px; line-height: 1.6; }

.form-card {
  position: relative;
  min-height: 650px;
  overflow: hidden;
  padding: clamp(36px, 5vw, 60px);
  background:
    radial-gradient(circle at 100% 0, rgba($color-peach, .1), transparent 20rem),
    rgba($color-card, .96);
  box-shadow: $shadow-md;
}

.form-card::before {
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: linear-gradient($color-lime, $color-sage 52%, $color-peach);
  content: '';
}

.step-panel { max-width: 760px; }

.panel-step-label {
  color: $color-sage;
  font-size: 12px;
  font-weight: 850;
  letter-spacing: .13em;
}

.panel-title {
  margin-top: 10px;
  font-size: clamp(27px, 3vw, 36px);
  font-weight: 760;
  letter-spacing: -.035em;
  line-height: 1.18;
}

.panel-desc {
  max-width: 620px;
  margin-top: 10px;
  margin-bottom: 34px;
  color: $color-text-secondary;
  font-size: 14px;
  line-height: 1.75;
}

.profile-form,
.panel-form { width: 100%; }

.profile-form :deep(.el-form-item),
.panel-form :deep(.el-form-item) { margin-bottom: 22px; }

.profile-form :deep(.el-form-item__label),
.panel-form :deep(.el-form-item__label) {
  padding-bottom: 8px;
  color: $color-text-primary;
  font-size: 13px;
  font-weight: 750;
  line-height: 1.4;
}

.profile-form :deep(.el-input__wrapper),
.profile-form :deep(.el-select__wrapper),
.panel-form :deep(.el-input__wrapper),
.panel-form :deep(.el-select__wrapper) {
  min-height: 48px;
  background: rgba($color-surface-soft, .42);
}

.gender-toggle { display: grid; grid-template-columns: repeat(2, 1fr); width: 100%; }
.gender-toggle :deep(.el-radio-button) { width: 100%; }
.gender-toggle :deep(.el-radio-button__inner) { justify-content: center; width: 100%; min-height: 48px; }

.calc-preview {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 4px;
  margin-bottom: 26px;
  padding: 10px;
  border: 1px solid rgba($color-sage, .13);
  border-radius: $radius-md;
  background: rgba($color-sage, .055);
}

.calc-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 13px;
  border-radius: $radius-sm;
  background: rgba($color-card, .8);
}

.calc-item small { color: $color-text-secondary; font-size: 13px; }
.calc-item strong { color: $color-sage-dark; font-size: 18px; }
.calc-item em { font-size: 12px; font-style: normal; font-weight: 600; }

.goal-group {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  width: 100%;
}

.goal-card {
  position: relative;
  display: block !important;
  width: 100%;
  height: auto !important;
  margin: 0 !important;
  overflow: hidden;
  border: 1px solid $color-border !important;
  border-radius: $radius-md !important;
  background: rgba($color-card, .84);
  white-space: normal !important;
  transition: border-color .2s ease, background-color .2s ease, box-shadow .2s ease, transform .2s ease;
}

.goal-card:hover {
  border-color: rgba($color-sage, .5) !important;
  transform: translateY(-2px);
  box-shadow: $shadow-sm;
}

.goal-card:focus-within { outline: 3px solid rgba($color-sage, .24); outline-offset: 2px; }

.goal-card.is-checked {
  border-color: $color-sage !important;
  background: linear-gradient(145deg, rgba($color-sage-light, .54), rgba($color-lime-soft, .42)) !important;
  box-shadow: 0 12px 28px rgba($color-sage-dark, .08);
}

.goal-card :deep(.el-radio__input) {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  opacity: 0;
}

.goal-card :deep(.el-radio__label) {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  min-height: 178px;
  padding: 22px;
  color: inherit;
  white-space: normal;
}

.goal-icon { margin-bottom: 17px; border-radius: 17px; box-shadow: none; }
.goal-text { color: $color-text-primary; font-size: 16px; font-weight: 780; }
.goal-sub { max-width: 220px; margin-top: 5px; color: $color-text-secondary; font-size: 13px; line-height: 1.6; }

.goal-check {
  position: absolute;
  top: 18px;
  right: 18px;
  display: grid;
  place-items: center;
  width: 25px;
  height: 25px;
  border: 1px solid $color-border;
  border-radius: 50%;
  background: $color-card;
  color: transparent;
  transition: all .2s ease;
}

.goal-card.is-checked .goal-check { border-color: $color-sage-dark; background: $color-sage-dark; color: #fff; }

.safety-hint {
  display: grid;
  gap: 2px;
  width: 100%;
  margin-top: 12px;
  padding: 13px 15px;
  border: 1px solid rgba($color-warning, .16);
  border-radius: $radius-sm;
  background: rgba($color-butter, .12);
  color: $color-text-secondary;
  font-size: 13px;
  line-height: 1.65;
}

.safety-hint strong { color: $color-warning; font-size: 13px; }

.budget-control {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 280px);
  align-items: end;
  gap: 28px;
  margin-bottom: 24px;
  padding: 22px;
  border: 1px solid rgba($color-sage, .13);
  border-radius: $radius-md;
  background: $color-surface-soft;
}

.budget-control > div { display: grid; gap: 4px; align-self: center; }
.budget-control > div strong { color: $color-text-primary; font-size: 15px; }
.budget-control > div span { color: $color-text-secondary; font-size: 13px; }
.budget-control :deep(.el-form-item) { margin-bottom: 0; }

.summary-card {
  margin-top: 8px;
  padding: 22px;
  border: 1px solid rgba($color-peach, .3);
  border-radius: $radius-md;
  background: linear-gradient(145deg, $color-surface-warm, rgba($color-lime-soft, .26));
}

.summary-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.summary-heading > div { display: grid; gap: 2px; }
.summary-heading span { color: $color-rose-dark; font-size: 12px; font-weight: 800; letter-spacing: .1em; }
.summary-heading h4 { color: $color-text-primary; font-size: 18px; font-weight: 750; }
.summary-icon { border-radius: 12px; box-shadow: none; }

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.summary-grid > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  padding: 11px 12px;
  border-radius: $radius-xs;
  background: rgba($color-card, .66);
}

.summary-grid span { color: $color-text-secondary; font-size: 12px; }
.summary-grid strong { overflow: hidden; color: $color-text-primary; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }

.step-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid $color-divider;
}

.step-actions .el-button { min-width: 112px; }
.step-actions .el-button--primary { min-width: 170px; }

.step-panel > .submit-error { margin-top: 16px; margin-bottom: 0; }

@media (max-width: $breakpoint-lg) {
  .profile-heading { align-items: flex-start; }
  .profile-workspace { grid-template-columns: 1fr; }
  .profile-rail { display: none; }
  .mobile-progress {
    display: grid;
    gap: 12px;
    margin-bottom: 18px;
    padding: 17px 20px;
    border-radius: $radius-md;
    box-shadow: $shadow-xs;
  }
  .mobile-progress-copy { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
  .mobile-progress-copy span { color: $color-sage-dark; font-size: 12px; font-weight: 800; letter-spacing: .08em; }
  .mobile-progress-copy strong { color: $color-text-primary; font-size: 14px; }
  .mobile-progress :deep(.el-progress-bar__outer) { background: rgba($color-sage, .1); }
  .mobile-progress :deep(.el-progress-bar__inner) { background: linear-gradient(90deg, $color-sage-dark, $color-sage); }
  .form-card { min-height: 0; }
  .step-panel { max-width: none; }
}

@media (max-width: $breakpoint-md) {
  .profile-heading { display: grid; gap: 20px; margin-bottom: 26px; }
  .heading-meta { flex-wrap: wrap; }
  .heading-copy h1 { font-size: 38px; }
  .form-card { padding: 38px 30px; }
}

@media (max-width: $breakpoint-sm) {
  .profile-page { padding-top: 28px; padding-bottom: 46px; }
  .heading-copy h1 { margin-top: 10px; font-size: 32px; }
  .heading-copy p { margin-top: 11px; font-size: 13px; line-height: 1.75; }
  .heading-meta > span { padding: 8px 11px; }
  .form-card { padding: 30px 20px; border-radius: 22px; }
  .form-card::before { inset: 0 0 auto; width: auto; height: 4px; }
  .panel-title { font-size: 28px; }
  .panel-desc { margin-bottom: 26px; font-size: 13px; }
  .profile-form :deep(.el-form-item),
  .panel-form :deep(.el-form-item) { margin-bottom: 18px; }
  .calc-preview { grid-template-columns: 1fr; }
  .goal-group { grid-template-columns: 1fr; }
  .goal-card :deep(.el-radio__label) { min-height: 144px; padding: 18px; }
  .goal-icon { margin-bottom: 12px; }
  .goal-check { top: 16px; right: 16px; }
  .budget-control { grid-template-columns: 1fr; gap: 16px; padding: 18px; }
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .step-actions { align-items: stretch; }
  .step-actions .el-button { min-height: 46px; min-width: 0; }
  .step-actions .el-button--primary { flex: 1; min-width: 0; }
}

@media (max-width: 420px) {
  .heading-meta > span:last-child { display: none; }
  .step-actions { display: grid; grid-template-columns: 1fr; }
  .step-actions .el-button { width: 100%; margin-left: 0; }
  .single-action { display: flex; }
  .summary-grid { grid-template-columns: 1fr; }
}
</style>
