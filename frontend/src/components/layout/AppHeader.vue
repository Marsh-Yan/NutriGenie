<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import PremiumIcon from '@/components/common/PremiumIcon.vue'
import type { PremiumIconName } from '@/components/common/PremiumIcon.vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const isHome = computed(() => route.name === 'home')
const isAppRoute = computed(() => !String(route.name || '').startsWith('admin'))

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/')
}

const navItems = computed<{ to: string; label: string; icon: PremiumIconName }[]>(() => [
  { to: '/', label: '首页', icon: 'home' },
  { to: '/profile', label: '我的画像', icon: 'profile' },
  { to: '/plan/new', label: '开始规划', icon: 'plan' },
  ...(auth.isLoggedIn ? [{ to: '/plans', label: '我的方案', icon: 'clipboard' as PremiumIconName }] : []),
])

async function logout() {
  auth.logout()
  await router.push('/')
}
</script>

<template>
  <header class="app-header">
    <div class="header-inner page-container">
      <button v-if="!isHome" class="btn-back" type="button" aria-label="返回上一页" @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
      </button>

      <router-link to="/" class="logo" aria-label="NutriGenie 首页">
        <PremiumIcon name="salad" class="logo-icon" :size="24" :box-size="40" />
        <span class="logo-text">NutriGenie</span>
      </router-link>

      <nav class="desktop-nav" aria-label="主导航">
        <router-link v-for="item in navItems.slice(1)" :key="item.to" :to="item.to" class="nav-link">
          <PremiumIcon :name="item.icon" class="nav-icon" :size="15" :box-size="28" />
          {{ item.label }}
        </router-link>
        <div v-if="auth.isLoggedIn" class="account-menu">
          <span>{{ auth.user?.nickname }}</span>
          <button type="button" @click="logout">退出</button>
        </div>
        <router-link v-else :to="{ name: 'auth', query: { mode: 'login' } }" class="account-link">登录</router-link>
      </nav>
    </div>
  </header>

  <nav v-if="isAppRoute" class="mobile-nav" aria-label="移动端主导航">
    <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="mobile-nav-link">
      <PremiumIcon :name="item.icon" class="mobile-nav-icon" :size="18" :box-size="34" />
      <span>{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<style scoped lang="scss">
.app-header { position: sticky; top: 0; z-index: 100; background: rgba($color-sage, .94); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(255,255,255,.18); }
.header-inner { display: flex; align-items: center; height: 64px; gap: 16px; }
.btn-back { display: grid; place-items: center; width: 44px; height: 44px; border: 0; border-radius: 50%; background: rgba(255,255,255,.2); color: $color-text-inverse; cursor: pointer; font-size: 18px; }
.btn-back:hover { background: rgba(255,255,255,.35); }
.logo { display: flex; align-items: center; gap: 8px; margin-right: auto; text-decoration: none; }
.logo-icon { border-radius: 12px; box-shadow: inset 0 1px 0 rgba(255,255,255,.6), 0 6px 14px rgba(55,78,68,.16); }
.logo-text { color: $color-text-inverse; font-size: 20px; font-weight: 700; letter-spacing: -.5px; }
.desktop-nav { display: flex; gap: 8px; }
.nav-link { display: flex; align-items: center; gap: 8px; min-height: 40px; padding: 8px 16px; border-radius: 20px; color: rgba(255,255,255,.88); font-size: 14px; }
.nav-link:hover, .nav-link.router-link-active { background: rgba(255,255,255,.18); color: #fff; }
.account-menu { display: flex; align-items: center; gap: 8px; margin-left: 4px; color: #fff; font-size: 13px; }
.account-menu button, .account-link { min-height: 36px; padding: 7px 12px; border: 1px solid rgba(255,255,255,.48); border-radius: 999px; background: transparent; color: #fff; cursor: pointer; font: inherit; }
.nav-icon { --icon-box-size: 28px; --icon-size: 15px; border: 0; border-radius: 9px; background: rgba(255,255,255,.16); box-shadow: none; color: currentColor; }
.mobile-nav { display: none; }

@media (max-width: $breakpoint-sm) {
  .header-inner { height: 60px; }
  .desktop-nav { display: none; }
  .account-menu, .account-link { margin-left: auto; }
  .logo-icon { --icon-box-size: 36px; --icon-size: 22px; }
  .logo-text { font-size: 18px; }
  .mobile-nav { position: fixed; inset: auto 0 0; z-index: 120; display: grid; grid-template-columns: repeat(auto-fit, minmax(72px, 1fr)); min-height: 64px; padding-bottom: env(safe-area-inset-bottom); border-top: 1px solid $color-border; background: rgba(255,255,255,.96); backdrop-filter: blur(14px); box-shadow: 0 -4px 18px rgba(74,74,74,.08); }
  .mobile-nav-link { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; min-height: 64px; color: $color-text-secondary; font-size: 11px; }
  .mobile-nav-link.router-link-exact-active { color: $color-sage-dark; font-weight: 700; }
  .mobile-nav-icon { --icon-box-size: 32px; --icon-size: 18px; border-radius: 10px; box-shadow: none; }
}
</style>
