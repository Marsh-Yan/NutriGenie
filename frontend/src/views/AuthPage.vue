<script setup lang="ts">
import { computed, ref, useId, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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
    <div class="auth-intro">
      <span>专属饮食规划</span>
      <h1>{{ isRegister ? '创建你的 NutriGenie 账户' : '欢迎回来' }}</h1>
      <p>{{ isRegister ? '完成注册后，继续建立健康画像。' : '登录后继续你的个性化饮食方案。' }}</p>
    </div>

    <form class="auth-card card" novalidate @submit.prevent="submit">
      <div class="field">
        <label :for="emailId">邮箱</label>
        <el-input :id="emailId" v-model="email" type="email" autocomplete="email" placeholder="name@example.com" />
      </div>
      <div v-if="isRegister" class="field">
        <label :for="nicknameId">昵称</label>
        <el-input :id="nicknameId" v-model="nickname" autocomplete="nickname" placeholder="怎么称呼你" />
      </div>
      <div class="field">
        <label :for="passwordId">密码</label>
        <el-input :id="passwordId" v-model="password" type="password" show-password :autocomplete="isRegister ? 'new-password' : 'current-password'" placeholder="至少 8 位" />
      </div>
      <div v-if="isRegister" class="field">
        <label :for="codeId">验证码</label>
        <el-input :id="codeId" v-model="code" inputmode="numeric" autocomplete="one-time-code" placeholder="开发环境验证码：123456" />
      </div>
      <p v-if="isRegister" class="dev-note">本地演示模式：验证码固定为 <strong>123456</strong>。生产环境需接入真实邮件验证码。</p>

      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <el-button native-type="submit" type="primary" size="large" :loading="loading">
        {{ isRegister ? '注册并继续' : '登录并继续' }}
      </el-button>
      <button class="switch" type="button" @click="switchMode">
        {{ isRegister ? '已有账号？去登录' : '没有账号？创建账户' }}
      </button>
    </form>
  </div>
</template>

<style scoped lang="scss">
.auth-page { display: grid; grid-template-columns: 1fr 420px; align-items: center; gap: 72px; min-height: 68vh; padding-top: 56px; padding-bottom: 56px; }
.auth-intro span { color: $color-sage-dark; font-size: 14px; font-weight: 700; letter-spacing: .08em; }
.auth-intro h1 { margin: 10px 0; color: $color-text-primary; font-size: clamp(32px, 4vw, 48px); line-height: 1.18; }
.auth-intro p { color: $color-text-secondary; font-size: 16px; }
.auth-card { display: grid; gap: 18px; padding: 32px; }
.field { display: grid; gap: 7px; }
.field label { color: $color-text-primary; font-size: 14px; font-weight: 600; }
.auth-card :deep(.el-input__wrapper) { min-height: 44px; }
.auth-card .el-button { width: 100%; min-height: 44px; }
.error { padding: 10px 12px; border-radius: $radius-sm; background: rgba($color-danger,.1); color: $color-danger; font-size: 13px; }
.dev-note { padding: 10px 12px; border-radius: $radius-sm; background: rgba($color-info,.16); color: $color-text-primary; font-size: 12px; }
.switch { min-height: 40px; border: 0; background: transparent; color: $color-sage-dark; cursor: pointer; font: inherit; }
@media (max-width: $breakpoint-md) { .auth-page { grid-template-columns: 1fr; gap: 28px; max-width: 520px; } .auth-intro { text-align: center; } }
@media (max-width: $breakpoint-sm) { .auth-page { min-height: auto; padding-top: 32px; padding-bottom: 32px; } .auth-intro h1 { font-size: 30px; } .auth-card { padding: 24px; } }
</style>
