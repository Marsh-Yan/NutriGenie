<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import BrandLogo from '@/components/common/BrandLogo.vue'

const auth = useAuthStore()
const links = computed(() => auth.isLoggedIn
  ? [
      { to: '/dashboard', label: '今日计划' },
      { to: '/plans', label: '我的计划' },
      { to: '/recipes', label: '菜谱库' },
      { to: '/plan/new', label: '创建计划' },
      { to: '/profile', label: '健康画像' },
    ]
  : [
      { to: '/demo', label: '方案示例' },
      { to: '/recipes', label: '菜谱库' },
      { to: '/auth?mode=login', label: '登录' },
      { to: '/auth?mode=register&redirect=/profile', label: '开始规划' },
    ])
</script>

<template>
  <footer class="app-footer">
    <div class="footer-inner page-container">
      <BrandLogo />

      <nav class="footer-links" aria-label="页脚导航">
        <router-link v-for="link in links" :key="link.to" :to="link.to">{{ link.label }}</router-link>
      </nav>

      <p class="footer-note">
        NutriGenie 提供一般健康饮食参考，不构成医疗诊断、治疗或个体化营养处方。
      </p>
    </div>
  </footer>
</template>

<style scoped lang="scss">
.app-footer {
  margin-top: clamp(72px, 10vw, 128px);
  padding: 52px 0 32px;
  border-top: 1px solid $color-border;
  background: $color-surface;
}

.footer-inner {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) auto;
  align-items: center;
  gap: $space-6 $space-8;
}

.footer-links { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 10px 22px; }
.footer-links a { min-height: 44px; display: inline-flex; align-items: center; color: $color-text-secondary; font-size: 13px; font-weight: 680; }
.footer-links a:hover { color: $color-brand; }
.footer-note { grid-column: 1 / -1; padding-top: $space-5; border-top: 1px solid $color-divider; color: $color-text-placeholder; font-size: 12px; }

@media (max-width: $breakpoint-md) {
  .footer-inner { grid-template-columns: 1fr; }
  .footer-links { justify-content: flex-start; }
}

@media (max-width: $breakpoint-sm) {
  .app-footer { margin-top: 64px; padding: 36px 0 24px; }
}
</style>
