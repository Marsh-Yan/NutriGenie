<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppFooter from '@/components/layout/AppFooter.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import MobileNavigation from '@/components/layout/MobileNavigation.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()
const mainContent = ref<HTMLElement | null>(null)

const isAdminRoute = computed(() => String(route.name ?? '').startsWith('admin'))
const showMobileNavigation = computed(() => (
  auth.isLoggedIn
  && !isAdminRoute.value
  && !['auth', 'not-found'].includes(String(route.name ?? ''))
))

watch(
  () => route.fullPath,
  async () => {
    await nextTick()
    mainContent.value?.focus({ preventScroll: true })
  },
)
</script>

<template>
  <div class="app-shell" :class="{ 'app-shell--with-mobile-nav': showMobileNavigation }">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <AppHeader />
    <main id="main-content" ref="mainContent" class="main-content" tabindex="-1">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    <AppFooter v-if="!isAdminRoute" />
    <MobileNavigation v-if="showMobileNavigation" />
  </div>
</template>

<style scoped lang="scss">
.app-shell {
  display: flex;
  min-height: 100vh;
  min-height: 100dvh;
  flex-direction: column;
}

.main-content {
  flex: 1;
  outline: none;
  scroll-margin-top: calc(#{$header-height} + 20px);
}

.main-content:focus-visible {
  outline: 3px solid $color-focus-ring;
  outline-offset: -3px;
}

.skip-link {
  position: fixed;
  top: 10px;
  left: 12px;
  z-index: $layer-skip-link;
  padding: 11px 16px;
  border: 2px solid $color-accent;
  border-radius: $radius-sm;
  background: $color-brand;
  box-shadow: $shadow-md;
  color: $color-text-inverse;
  font-weight: 750;
  transform: translateY(-160%);
  transition: transform $motion-fast $ease-standard;
}

.skip-link:focus { transform: translateY(0); }

.page-enter-active,
.page-leave-active {
  transition: opacity $motion-base $ease-standard;
}

.page-enter-from,
.page-leave-to { opacity: 0; }

@media (max-width: 820px) {
  .app-shell--with-mobile-nav {
    padding-bottom: calc(76px + env(safe-area-inset-bottom));
  }
}
</style>
