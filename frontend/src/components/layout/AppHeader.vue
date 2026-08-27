<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import PremiumIcon from '@/components/common/PremiumIcon.vue'
import type { PremiumIconName } from '@/components/common/PremiumIcon.vue'
import { useAuthStore } from '@/stores/auth'
import { useProfileStore } from '@/stores/profile'
import { usePlanStore } from '@/stores/plan'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const profileStore = useProfileStore()
const planStore = usePlanStore()
const isHome = computed(() => route.name === 'home')
const isAdminRoute = computed(() => String(route.name || '').startsWith('admin'))
const isAppRoute = computed(() => !isAdminRoute.value)
const showConsumerMobileNav = computed(() => isAppRoute.value && !['auth', 'not-found'].includes(String(route.name || '')))

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/')
}

const navItems = computed<{ to: string; label: string; icon: PremiumIconName }[]>(() => [
  { to: '/', label: '首页', icon: 'home' },
  { to: '/profile', label: '健康画像', icon: 'profile' },
  { to: '/plan/new', label: 'AI 规划', icon: 'plan' },
  { to: '/plans', label: '我的方案', icon: 'clipboard' },
])

const adminNavItems: { to: string; label: string; icon: PremiumIconName }[] = [
  { to: '/admin', label: '概览', icon: 'home' },
  { to: '/admin/ingredients', label: '食材', icon: 'leaf' },
  { to: '/admin/recipes', label: '菜谱', icon: 'nutrition' },
  { to: '/admin/knowledge', label: '知识库', icon: 'clipboard' },
]

async function logout() {
  profileStore.reset()
  planStore.reset()
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
        <PremiumIcon name="salad" class="logo-icon" :size="22" :box-size="42" />
        <span class="logo-copy">
          <strong class="logo-text">NutriGenie</strong>
          <small>AI nutrition studio</small>
        </span>
      </router-link>

      <nav v-if="isAdminRoute" class="desktop-nav" aria-label="管理后台导航">
        <router-link v-for="item in adminNavItems" :key="item.to" :to="item.to" class="nav-link">
          {{ item.label }}
        </router-link>
      </nav>
      <nav v-else class="desktop-nav" aria-label="主导航">
        <router-link to="/demo" class="nav-link">方案示例</router-link>
        <router-link v-for="item in navItems.slice(1)" :key="item.to" :to="item.to" class="nav-link">
          {{ item.label }}
        </router-link>
      </nav>

      <div class="desktop-account">
        <template v-if="auth.isLoggedIn">
          <span class="account-name"><i />{{ auth.user?.nickname || '我的账户' }}</span>
          <button class="logout-button" type="button" @click="logout">退出</button>
        </template>
        <template v-else>
          <router-link :to="{ name: 'auth', query: { mode: 'login' } }" class="login-link">登录</router-link>
          <router-link :to="{ name: 'auth', query: { mode: 'register', redirect: '/profile' } }" class="header-cta">免费开始</router-link>
        </template>
      </div>

      <div class="mobile-account">
        <button v-if="auth.isLoggedIn" type="button" @click="logout">退出</button>
        <router-link v-else :to="{ name: 'auth', query: { mode: 'login' } }">登录</router-link>
      </div>
    </div>
  </header>

  <nav v-if="isAdminRoute" class="mobile-nav" aria-label="移动端管理导航">
    <router-link v-for="item in adminNavItems" :key="item.to" :to="item.to" class="mobile-nav-link">
      <PremiumIcon :name="item.icon" class="mobile-nav-icon" :size="18" :box-size="34" />
      <span>{{ item.label }}</span>
    </router-link>
  </nav>
  <nav v-else-if="showConsumerMobileNav" class="mobile-nav" aria-label="移动端主导航">
    <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="mobile-nav-link">
      <PremiumIcon :name="item.icon" class="mobile-nav-icon" :size="18" :box-size="34" />
      <span>{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<style scoped lang="scss">
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  border-bottom: 1px solid rgba($color-sage-dark, .1);
  background: rgba($color-bg, .86);
  box-shadow: 0 1px 0 rgba(255, 255, 255, .72) inset;
  backdrop-filter: blur(18px) saturate(140%);
}

.header-inner { display: flex; align-items: center; min-height: 76px; gap: 28px; }
.btn-back { display: none; }

.logo { display: flex; align-items: center; gap: 11px; flex: 0 0 auto; color: $color-text-primary; }
.logo:hover { color: $color-text-primary; }
.logo-icon {
  --icon-color: #{$color-sage-dark};
  --icon-bg: #{$color-sage-light};
  border-color: rgba($color-sage, .22);
  border-radius: 14px;
  box-shadow: 0 8px 20px rgba(79, 88, 82, .11);
}
.logo-copy { display: grid; gap: 0; line-height: 1.05; }
.logo-text { font-size: 19px; font-weight: 850; letter-spacing: -.04em; }
.logo-copy small { margin-top: 4px; color: $color-text-secondary; font-size: 9px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }

.desktop-nav { display: flex; align-items: center; justify-content: center; gap: 3px; margin-left: auto; }
.nav-link {
  position: relative;
  min-height: 42px;
  padding: 10px 14px;
  border-radius: 999px;
  color: $color-text-secondary;
  font-size: 14px;
  font-weight: 650;
}
.nav-link::after {
  position: absolute;
  right: 14px;
  bottom: 6px;
  left: 14px;
  height: 2px;
  border-radius: 999px;
  background: $color-sage;
  content: '';
  opacity: 0;
  transform: scaleX(.4);
  transition: opacity .2s ease, transform .2s ease;
}
.nav-link:hover,
.nav-link.router-link-active { color: $color-sage-dark; }
.nav-link.router-link-active::after { opacity: 1; transform: scaleX(1); }

.desktop-account { display: flex; align-items: center; gap: 10px; }
.account-name { display: inline-flex; align-items: center; gap: 7px; color: $color-text-secondary; font-size: 13px; white-space: nowrap; }
.account-name i { width: 8px; height: 8px; border-radius: 50%; background: $color-sage; box-shadow: 0 0 0 4px rgba($color-sage, .16); }
.logout-button,
.login-link {
  min-height: 40px;
  padding: 9px 12px;
  border: 0;
  background: transparent;
  color: $color-text-secondary;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 650;
}
.header-cta {
  min-height: 42px;
  padding: 10px 18px;
  border-radius: 999px;
  background: $color-sage-dark;
  box-shadow: 0 8px 18px rgba($color-sage-dark, .16);
  color: #fff;
  font-size: 13px;
  font-weight: 750;
}
.header-cta:hover { background: $color-sage; color: #fff; transform: translateY(-1px); }

.mobile-account,
.mobile-nav { display: none; }

@media (max-width: 820px) {
  .header-inner { min-height: 68px; gap: 12px; }
  .btn-back {
    display: grid;
    place-items: center;
    width: 42px;
    height: 42px;
    flex: 0 0 auto;
    border: 1px solid $color-border;
    border-radius: 50%;
    background: rgba(255,255,255,.72);
    color: $color-sage-dark;
    cursor: pointer;
  }
  .desktop-nav,
  .desktop-account { display: none; }
  .logo { margin-right: auto; }
  .mobile-account { display: block; }
  .mobile-account button,
  .mobile-account a { padding: 8px; border: 0; background: transparent; color: $color-sage-dark; font-size: 13px; font-weight: 700; }
}

@media (max-width: 820px) {
  .header-inner { min-height: 64px; }
  .logo-copy small { display: none; }
  .logo-icon { --icon-box-size: 38px; --icon-size: 20px; }
  .logo-text { font-size: 18px; }
  .mobile-nav {
    position: fixed;
    inset: auto 0 0;
    z-index: 120;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    min-height: 72px;
    padding: 4px 6px env(safe-area-inset-bottom);
    border-top: 1px solid rgba($color-sage-dark, .12);
    background: rgba(255,255,255,.94);
    box-shadow: 0 -10px 30px rgba($color-sage-dark,.08);
    backdrop-filter: blur(18px) saturate(140%);
  }
  .mobile-nav-link {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1px;
    min-width: 0;
    min-height: 64px;
    border-radius: 15px;
    color: $color-text-secondary;
    font-size: 10px;
    font-weight: 650;
  }
  .mobile-nav-link.router-link-exact-active { color: $color-sage-dark; background: rgba($color-sage-light, .42); }
  .mobile-nav-icon {
    --icon-box-size: 31px;
    --icon-size: 17px;
    border: 0;
    border-radius: 10px;
    background: transparent;
    box-shadow: none;
    color: currentColor;
  }
  .mobile-nav-icon:hover { transform: none; box-shadow: none; }
}
</style>
