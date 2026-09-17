<script setup lang="ts">
import { computed } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import PremiumIcon from '@/components/common/PremiumIcon.vue'
import { useAuthStore } from '@/stores/auth'
import { usePlanStore } from '@/stores/plan'
import { useProfileStore } from '@/stores/profile'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const profileStore = useProfileStore()
const planStore = usePlanStore()

type NavigationItem = {
  to: string
  label: string
  routeNames: string[]
}

const userNavigation: NavigationItem[] = [
  { to: '/dashboard', label: '今日', routeNames: ['dashboard'] },
  { to: '/plans', label: '计划', routeNames: ['plan-history', 'plan-result'] },
  { to: '/plan/new', label: '创建', routeNames: ['plan-new'] },
  { to: '/profile', label: '我的', routeNames: ['profile'] },
]

const adminNavigation: NavigationItem[] = [
  { to: '/admin', label: '概览', routeNames: ['admin'] },
  { to: '/admin/ingredients', label: '食材', routeNames: ['admin-ingredients'] },
  { to: '/admin/recipes', label: '菜谱', routeNames: ['admin-recipes'] },
  { to: '/admin/knowledge', label: '知识库', routeNames: ['admin-knowledge'] },
]

const routeName = computed(() => String(route.name ?? ''))
const isHome = computed(() => routeName.value === 'home')
const isAdminRoute = computed(() => routeName.value.startsWith('admin'))
const isTopLevelRoute = computed(() => ['home', 'dashboard', 'plan-history', 'plan-new', 'profile'].includes(routeName.value))
const showBack = computed(() => !isHome.value && !isTopLevelRoute.value)
const accountInitial = computed(() => (auth.user?.nickname || auth.user?.email || '我').trim().slice(0, 1).toUpperCase())

function isCurrent(item: NavigationItem) {
  return item.routeNames.includes(routeName.value)
}

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push(auth.isLoggedIn ? '/dashboard' : '/')
}

async function logout() {
  profileStore.reset()
  planStore.reset()
  auth.logout()
  await router.push('/')
}

async function handleAccountCommand(command: string) {
  if (command === 'logout') {
    await logout()
    return
  }
  if (command === 'admin') await router.push('/admin')
  if (command === 'profile') await router.push('/profile')
}
</script>

<template>
  <header class="app-header">
    <div class="header-inner page-container">
      <button v-if="showBack" class="back-button" type="button" aria-label="返回上一页" @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
      </button>

      <router-link :to="auth.isLoggedIn ? '/dashboard' : '/'" class="brand" aria-label="NutriGenie 首页">
        <PremiumIcon name="salad" class="brand__icon" :size="22" :box-size="42" />
        <span class="brand__copy">
          <strong>NutriGenie</strong>
          <small>营养计划工作台</small>
        </span>
      </router-link>

      <nav v-if="isAdminRoute" class="desktop-navigation" aria-label="管理后台导航">
        <router-link
          v-for="item in adminNavigation"
          :key="item.to"
          :to="item.to"
          class="navigation-link"
          :class="{ 'is-active': isCurrent(item) }"
          :aria-current="isCurrent(item) ? 'page' : undefined"
        >
          {{ item.label }}
        </router-link>
      </nav>

      <nav v-else-if="auth.isLoggedIn" class="desktop-navigation" aria-label="主要导航">
        <router-link
          v-for="item in userNavigation"
          :key="item.to"
          :to="item.to"
          class="navigation-link"
          :class="{ 'is-active': isCurrent(item) }"
          :aria-current="isCurrent(item) ? 'page' : undefined"
        >
          {{ item.label }}
        </router-link>
      </nav>

      <nav v-else class="desktop-navigation public-navigation" aria-label="访客导航">
        <router-link to="/demo" class="navigation-link" :class="{ 'is-active': routeName === 'demo-plan' }">方案示例</router-link>
        <router-link :to="{ path: '/', hash: '#how-it-works' }" class="navigation-link">如何工作</router-link>
      </nav>

      <div class="desktop-account">
        <template v-if="auth.isLoggedIn">
          <el-dropdown trigger="click" placement="bottom-end" @command="handleAccountCommand">
            <button class="account-trigger" type="button" aria-label="打开账号菜单">
              <span class="account-avatar" aria-hidden="true">{{ accountInitial }}</span>
              <span>{{ auth.user?.nickname || '我的账户' }}</span>
              <i aria-hidden="true" />
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">健康画像</el-dropdown-item>
                <el-dropdown-item v-if="auth.isAdmin" command="admin">管理后台</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <router-link :to="{ name: 'auth', query: { mode: 'login' } }" class="login-link">登录</router-link>
          <router-link :to="{ name: 'auth', query: { mode: 'register', redirect: '/profile' } }" class="header-cta">开始规划</router-link>
        </template>
      </div>

      <div class="mobile-account">
        <el-dropdown v-if="auth.isLoggedIn" trigger="click" placement="bottom-end" @command="handleAccountCommand">
          <button class="mobile-account__trigger" type="button" aria-label="打开账号菜单">
            <span aria-hidden="true">{{ accountInitial }}</span>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">健康画像</el-dropdown-item>
              <el-dropdown-item v-if="auth.isAdmin" command="admin">管理后台</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <template v-else>
          <router-link :to="{ name: 'auth', query: { mode: 'login' } }" class="mobile-login">登录</router-link>
          <router-link :to="{ name: 'auth', query: { mode: 'register', redirect: '/profile' } }" class="mobile-start">开始</router-link>
        </template>
      </div>
    </div>

    <nav v-if="isAdminRoute" class="admin-subnavigation" aria-label="移动端管理导航">
      <router-link
        v-for="item in adminNavigation"
        :key="item.to"
        :to="item.to"
        :class="{ 'is-active': isCurrent(item) }"
        :aria-current="isCurrent(item) ? 'page' : undefined"
      >
        {{ item.label }}
      </router-link>
    </nav>
  </header>
</template>

<style scoped lang="scss">
.app-header {
  position: sticky;
  top: 0;
  z-index: $layer-header;
  border-bottom: 1px solid rgba($color-brand, .13);
  background: rgba($color-background, .96);
  backdrop-filter: blur(16px) saturate(120%);
}

.header-inner {
  display: flex;
  min-height: $header-height;
  align-items: center;
  gap: clamp(18px, 3vw, 38px);
}

.back-button { display: none; }

.brand {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 11px;
  color: $color-text-primary;
}

.brand:hover { color: $color-text-primary; }
.brand__icon {
  --icon-color: #{$color-brand};
  --icon-bg: #{$color-accent};
  border-color: rgba($color-brand, .12);
  border-radius: 50%;
  box-shadow: none;
}
.brand__copy { display: grid; line-height: 1.05; }
.brand__copy strong { font-size: 19px; font-weight: 850; letter-spacing: -.035em; }
.brand__copy small { margin-top: 4px; color: $color-text-secondary; font-size: 11px; font-weight: 650; }

.desktop-navigation {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  margin-left: auto;
}

.navigation-link {
  position: relative;
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  padding: 9px 15px;
  border-radius: $radius-round;
  color: $color-text-secondary;
  font-size: 14px;
  font-weight: 680;
}

.navigation-link::after {
  position: absolute;
  right: 15px;
  bottom: 5px;
  left: 15px;
  height: 3px;
  border-radius: $radius-round;
  background: $color-accent-strong;
  content: '';
  opacity: 0;
  transform: scaleX(.45);
  transition: opacity $motion-fast $ease-standard, transform $motion-fast $ease-standard;
}

.navigation-link:hover,
.navigation-link.is-active { color: $color-brand; }
.navigation-link.is-active::after { opacity: 1; transform: scaleX(1); }

.desktop-account { display: flex; align-items: center; gap: 8px; }
.login-link,
.account-trigger {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  border: 0;
  background: transparent;
  color: $color-text-secondary;
  cursor: pointer;
  font-size: 13px;
  font-weight: 680;
}
.login-link { padding: 9px 12px; }
.account-trigger { gap: 8px; padding: 6px 8px; border-radius: $radius-round; }
.account-trigger:hover { background: $color-surface-muted; color: $color-brand; }
.account-avatar,
.mobile-account__trigger span {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 50%;
  background: $color-brand;
  color: $color-text-inverse;
  font-family: $font-numeric;
  font-weight: 800;
}
.account-trigger > i {
  width: 7px;
  height: 7px;
  border-right: 1.5px solid currentColor;
  border-bottom: 1.5px solid currentColor;
  transform: translateY(-2px) rotate(45deg);
}
.header-cta,
.mobile-start {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  padding: 9px 18px;
  border: 1px solid rgba($color-brand, .16);
  border-radius: $radius-round;
  background: $color-accent;
  box-shadow: 0 7px 18px rgba($color-brand, .12);
  color: $color-brand;
  font-size: 13px;
  font-weight: 800;
  transition: background $motion-fast $ease-standard, transform $motion-fast $ease-standard;
}
.header-cta:hover,
.mobile-start:hover { background: $color-accent-strong; color: $color-brand; transform: translateY(-1px); }

.mobile-account,
.admin-subnavigation { display: none; }

@media (max-width: 820px) {
  .header-inner { min-height: 64px; gap: 10px; }
  .desktop-navigation,
  .desktop-account { display: none; }
  .brand { margin-right: auto; }
  .brand__copy small { display: none; }
  .brand__copy strong { font-size: 18px; }
  .brand__icon { --icon-box-size: 38px; --icon-size: 20px; }
  .mobile-account { display: flex; align-items: center; gap: 6px; }
  .mobile-login { display: grid; min-width: 44px; min-height: 44px; place-items: center; font-size: 13px; font-weight: 730; }
  .mobile-start { min-height: 40px; padding-inline: 14px; }
  .mobile-account__trigger {
    display: grid;
    width: 44px;
    height: 44px;
    place-items: center;
    border: 0;
    border-radius: 50%;
    background: transparent;
    cursor: pointer;
  }
  .mobile-account__trigger span { width: 36px; height: 36px; }
  .back-button {
    display: grid;
    width: 44px;
    height: 44px;
    flex: 0 0 auto;
    place-items: center;
    border: 1px solid $color-border;
    border-radius: 50%;
    background: $color-surface;
    color: $color-brand;
    cursor: pointer;
  }
  .admin-subnavigation {
    display: flex;
    gap: 4px;
    padding: 0 18px 8px;
    overflow-x: auto;
    scrollbar-width: none;
  }
  .admin-subnavigation::-webkit-scrollbar { display: none; }
  .admin-subnavigation a {
    min-height: 40px;
    padding: 9px 13px;
    border-radius: $radius-round;
    color: $color-text-secondary;
    font-size: 13px;
    font-weight: 680;
    white-space: nowrap;
  }
  .admin-subnavigation a.is-active { background: $color-surface-muted; color: $color-brand; }
}
</style>
