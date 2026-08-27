<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PremiumIcon from '@/components/common/PremiumIcon.vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const mode = ref<'login' | 'register'>(route.query.mode === 'register' ? 'register' : 'login')
const email = ref('')
const nickname = ref('')
const password = ref('')
const code = ref('123456')
const loading = ref(false)
const error = ref('')
const emailId = useId()
const nicknameId = useId()
const passwordId = useId()
const codeId = useId()

const isRegister = computed(() => mode.value === 'register')

watch(() => route.query.mode, value => {
  if (value === 'register' || value === 'login') mode.value = value
})

function validate() {
  if (!/^\S+@\S+\.\S+$/.test(email.value.trim())) return '请输入有效的邮箱地址'
  if (isRegister.value && nickname.value.trim().length < 2) return '昵称至少需要 2 个字符'
  if (password.value.length < 8) return '密码至少需要 8 位'
  if (isRegister.value && !code.value.trim()) return '请输入验证码'
  return ''
}

async function submit() {
  error.value = validate()
  if (error.value || loading.value) return
  loading.value = true
  try {
    if (mode.value === 'login') await auth.login(email.value.trim(), password.value)
    else await auth.register(email.value.trim(), nickname.value.trim(), password.value, code.value.trim())
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
      ? route.query.redirect
      : '/plan/new'
    await router.replace(redirect)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '操作失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function switchMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  error.value = ''
}
</script>

<template>
  <div class="auth-page page-container">
    <section class="auth-shell">
      <div class="auth-story">
        <span class="story-orb story-orb-one" aria-hidden="true" />
        <span class="story-orb story-orb-two" aria-hidden="true" />

        <div class="story-copy">
          <span class="story-eyebrow">NutriGenie · AI Nutrition</span>
          <h1>把每一餐，变成更懂你的选择。</h1>
          <p>从身体数据、饮食偏好到每日预算，把复杂的营养规划整理成一份真正能执行的生活方案。</p>

          <div class="benefit-list" aria-label="产品特点">
            <div>
              <span class="benefit-mark">01</span>
              <span><strong>贴合目标</strong><small>热量与营养边界实时核算</small></span>
            </div>
            <div>
              <span class="benefit-mark">02</span>
              <span><strong>照顾日常</strong><small>预算、忌口与时间一起考虑</small></span>
            </div>
          </div>
        </div>

        <div class="story-preview" aria-label="今日规划预览">
          <div class="preview-heading">
            <span>今日计划</span>
            <span class="preview-status"><i /> 营养均衡</span>
          </div>
          <div class="preview-meal">
            <PremiumIcon name="salad" class="preview-icon" :size="28" :box-size="52" />
            <span><strong>香煎鸡胸藜麦碗</strong><small>午餐 · 25 分钟完成</small></span>
            <b>520<small>kcal</small></b>
          </div>
          <div class="preview-metrics">
            <span><small>蛋白质</small><strong>42g</strong></span>
            <span><small>预计成本</small><strong>¥18</strong></span>
            <span><small>匹配程度</small><strong>92%</strong></span>
          </div>
        </div>
      </div>

      <div class="auth-panel">
        <div class="panel-heading">
          <span class="panel-eyebrow">{{ isRegister ? '开启专属计划' : '继续你的计划' }}</span>
          <h2>{{ isRegister ? '创建账户' : '欢迎回来' }}</h2>
          <p>{{ isRegister ? '只需一分钟，下一步完善你的健康画像。' : '登录后继续查看与调整你的饮食方案。' }}</p>
        </div>

        <form class="auth-form" novalidate @submit.prevent="submit">
          <div class="field">
            <label :for="emailId">邮箱地址</label>
            <el-input :id="emailId" v-model="email" type="email" autocomplete="email" placeholder="name@example.com" />
          </div>
          <div v-if="isRegister" class="field">
            <label :for="nicknameId">怎么称呼你</label>
            <el-input :id="nicknameId" v-model="nickname" autocomplete="nickname" placeholder="输入你的昵称" />
          </div>
          <div class="field">
            <div class="field-heading">
              <label :for="passwordId">密码</label>
              <span>至少 8 位</span>
            </div>
            <el-input :id="passwordId" v-model="password" type="password" show-password :autocomplete="isRegister ? 'new-password' : 'current-password'" placeholder="输入密码" />
          </div>
          <div v-if="isRegister" class="field">
            <label :for="codeId">邮箱验证码</label>
            <el-input :id="codeId" v-model="code" inputmode="numeric" autocomplete="one-time-code" placeholder="输入 6 位验证码" />
          </div>
          <p v-if="isRegister" class="dev-note"><strong>演示环境提示</strong><span>验证码固定为 123456，生产环境需接入真实邮件服务。</span></p>

          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <el-button native-type="submit" type="primary" size="large" :loading="loading">
            {{ isRegister ? '注册并继续' : '登录并继续' }}
          </el-button>
          <button class="switch" type="button" @click="switchMode">
            <span>{{ isRegister ? '已经有账户？' : '第一次使用 NutriGenie？' }}</span>
            <strong>{{ isRegister ? '直接登录' : '创建账户' }}</strong>
          </button>
        </form>

        <p class="privacy-note"><span aria-hidden="true">●</span> 你的健康信息仅用于生成个人饮食方案</p>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.auth-page {
  display: grid;
  min-height: calc(100vh - 64px);
  padding-top: clamp(32px, 5vw, 68px);
  padding-bottom: clamp(42px, 6vw, 84px);
}

.auth-shell {
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(400px, .88fr);
  align-self: center;
  width: min(100%, 1120px);
  min-height: 650px;
  margin-inline: auto;
  overflow: hidden;
  border: 1px solid rgba($color-sage-dark, .13);
  border-radius: $radius-xl;
  background: $color-card;
  box-shadow: $shadow-lg;
}

.auth-story {
  position: relative;
  isolation: isolate;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-width: 0;
  overflow: hidden;
  padding: clamp(38px, 5vw, 66px);
  color: $color-text-primary;
  background:
    radial-gradient(circle at 88% 12%, rgba($color-blue-soft, .9), transparent 18rem),
    radial-gradient(circle at 4% 92%, rgba($color-rose-light, .82), transparent 20rem),
    linear-gradient(135deg, #D8E1DA 0%, #E3E6DE 55%, #ECE0DB 100%);
}

.auth-story::before {
  position: absolute;
  right: -14%;
  bottom: 18%;
  z-index: -1;
  width: 430px;
  height: 430px;
  border: 1px solid rgba($color-sage, .18);
  border-radius: 48% 52% 58% 42%;
  transform: rotate(24deg);
  content: '';
}

.story-orb {
  position: absolute;
  z-index: -1;
  border-radius: 50%;
  pointer-events: none;
}

.story-orb-one {
  top: -90px;
  right: -70px;
  width: 280px;
  height: 280px;
  background: rgba($color-sage-light, .72);
  filter: blur(2px);
}

.story-orb-two {
  bottom: 86px;
  left: -96px;
  width: 230px;
  height: 230px;
  background: rgba($color-rose-light, .78);
  filter: blur(4px);
}

.story-copy {
  position: relative;
  z-index: 1;
  max-width: 520px;
}

.story-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: $color-sage-dark;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .16em;
  text-transform: uppercase;
}

.story-eyebrow::before {
  width: 24px;
  height: 1px;
  background: currentColor;
  content: '';
}

.story-copy h1 {
  max-width: 500px;
  margin-top: 28px;
  color: $color-text-primary;
  font-size: clamp(38px, 4.4vw, 58px);
  font-weight: 780;
  letter-spacing: -.045em;
  line-height: 1.08;
}

.story-copy > p {
  max-width: 470px;
  margin-top: 22px;
  color: $color-text-secondary;
  font-size: 15px;
  line-height: 1.85;
}

.benefit-list {
  display: grid;
  gap: 14px;
  margin-top: 34px;
}

.benefit-list > div {
  display: flex;
  align-items: center;
  gap: 14px;
}

.benefit-mark {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  border: 1px solid rgba($color-sage, .2);
  border-radius: 50%;
  color: $color-sage-dark;
  background: rgba($color-card, .58);
  font-size: 12px;
  font-weight: 800;
}

.benefit-list div > span:last-child {
  display: grid;
  gap: 1px;
}

.benefit-list strong { color: $color-text-primary; font-size: 14px; }
.benefit-list small { color: $color-text-secondary; font-size: 13px; }

.story-preview {
  position: relative;
  z-index: 1;
  margin-top: 44px;
  padding: 18px;
  border: 1px solid rgba($color-sage, .18);
  border-radius: $radius-md;
  background: rgba($color-card, .54);
  box-shadow: inset 0 1px 0 rgba($color-card, .74), $shadow-sm;
  backdrop-filter: blur(16px);
}

.preview-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: $color-text-secondary;
  font-size: 12px;
  font-weight: 700;
}

.preview-status { display: inline-flex; align-items: center; gap: 6px; }
.preview-status i { width: 6px; height: 6px; border-radius: 50%; background: $color-sage; box-shadow: 0 0 0 4px rgba($color-sage, .12); }

.preview-meal {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 13px;
  margin-top: 14px;
}

.preview-icon {
  border-color: rgba($color-sage, .24);
  border-radius: 16px;
  box-shadow: none;
}

.preview-meal > span { display: grid; min-width: 0; }
.preview-meal strong { overflow: hidden; color: $color-text-primary; font-size: 14px; text-overflow: ellipsis; white-space: nowrap; }
.preview-meal small { color: $color-text-secondary; font-size: 12px; font-weight: 550; }
.preview-meal > b { display: grid; color: $color-sage-dark; font-size: 20px; line-height: 1; text-align: right; }
.preview-meal > b small { margin-top: 4px; }

.preview-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 16px;
}

.preview-metrics > span {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 9px 10px;
  border-radius: $radius-xs;
  background: rgba($color-card, .55);
}

.preview-metrics small { color: $color-text-secondary; font-size: 12px; }
.preview-metrics strong { color: $color-text-primary; font-size: 14px; }

.auth-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  padding: clamp(36px, 5vw, 58px);
  background:
    radial-gradient(circle at 100% 0, rgba($color-peach, .12), transparent 16rem),
    $color-card;
}

.panel-heading { margin-bottom: 30px; }

.panel-eyebrow {
  color: $color-sage;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .12em;
}

.panel-heading h2 {
  margin-top: 8px;
  font-size: clamp(30px, 3vw, 40px);
  font-weight: 760;
  letter-spacing: -.035em;
  line-height: 1.15;
}

.panel-heading p {
  margin-top: 10px;
  color: $color-text-secondary;
  font-size: 14px;
  line-height: 1.7;
}

.auth-form {
  display: grid;
  gap: 18px;
}

.field { display: grid; gap: 8px; }
.field label { color: $color-text-primary; font-size: 13px; font-weight: 750; }

.field-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.field-heading span { color: $color-text-secondary; font-size: 12px; }

.auth-form :deep(.el-input__wrapper) {
  min-height: 48px;
  padding-inline: 15px;
  background: rgba($color-surface-soft, .42);
}

.auth-form :deep(.el-input__inner) { color: $color-text-primary; font-size: 14px; }
.auth-form .el-button { width: 100%; min-height: 50px; margin-top: 2px; }

.error,
.dev-note {
  border-radius: $radius-sm;
  font-size: 12px;
  line-height: 1.55;
}

.error {
  padding: 11px 13px;
  border: 1px solid rgba($color-danger, .16);
  background: rgba($color-danger, .08);
  color: $color-danger;
}

.dev-note {
  display: grid;
  gap: 2px;
  padding: 11px 13px;
  border: 1px solid rgba($color-butter, .46);
  background: rgba($color-butter, .14);
  color: $color-text-secondary;
}

.dev-note strong { color: $color-warning; }

.switch {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  min-height: 40px;
  padding: 6px;
  border: 0;
  background: transparent;
  color: $color-text-secondary;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
}

.switch strong { color: $color-sage-dark; }
.switch:hover strong { color: $color-sage; }

.privacy-note {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  margin-top: 22px;
  color: $color-text-placeholder;
  font-size: 12px;
}

.privacy-note span { color: $color-success; font-size: 7px; }

@media (max-width: $breakpoint-lg) {
  .auth-shell { grid-template-columns: minmax(0, .9fr) minmax(390px, 1.1fr); }
  .auth-story { padding: 42px 36px; }
  .story-copy h1 { font-size: 42px; }
  .story-preview { margin-top: 36px; }
}

@media (max-width: $breakpoint-md) {
  .auth-page { min-height: auto; }
  .auth-shell { grid-template-columns: 1fr; width: min(100%, 640px); }
  .auth-story { min-height: 430px; padding: 40px; }
  .story-copy h1 { max-width: 480px; font-size: 40px; }
  .story-copy > p { max-width: 520px; }
  .benefit-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .story-preview { display: none; }
  .auth-panel { padding: 42px; }
}

@media (max-width: $breakpoint-sm) {
  .auth-page { padding-top: 22px; padding-bottom: 34px; }
  .auth-shell { border-radius: 26px; }
  .auth-story { min-height: auto; padding: 34px 24px 30px; }
  .story-copy h1 { margin-top: 22px; font-size: 34px; }
  .story-copy > p { margin-top: 16px; font-size: 14px; line-height: 1.75; }
  .benefit-list { grid-template-columns: 1fr; gap: 11px; margin-top: 24px; }
  .benefit-list > div:nth-child(2) { display: none; }
  .auth-panel { padding: 32px 22px; }
  .panel-heading { margin-bottom: 26px; }
  .panel-heading h2 { font-size: 30px; }
}
</style>
