<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'

const route = useRoute()
const mainContent = ref<HTMLElement | null>(null)

watch(
  () => route.fullPath,
  async () => {
    await nextTick()
    mainContent.value?.focus({ preventScroll: true })
    window.scrollTo({ top: 0, behavior: 'auto' })
  },
)
</script>

<template>
  <div class="app-root">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <AppHeader />
    <main id="main-content" ref="mainContent" class="main-content" tabindex="-1">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    <AppFooter />
  </div>
</template>

<style scoped lang="scss">
.app-root {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.main-content {
  flex: 1;
  outline: none;
}

.skip-link {
  position: fixed;
  top: 8px;
  left: 8px;
  z-index: 1000;
  padding: 10px 14px;
  border-radius: $radius-sm;
  background: $color-card;
  color: $color-sage-dark;
  box-shadow: $shadow-md;
  transform: translateY(-150%);

  &:focus {
    transform: translateY(0);
  }
}

// 页面过渡动画
.page-enter-active,
.page-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
