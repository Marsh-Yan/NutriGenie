<script setup lang="ts">
import PremiumIcon from '@/components/common/PremiumIcon.vue'
</script>

<template>
  <footer class="app-footer">
    <div class="footer-inner page-container">
      <div class="footer-brand">
        <PremiumIcon name="salad" class="footer-logo" :size="22" :box-size="42" />
        <div><strong>NutriGenie</strong><span>把营养建议，变成每一天都能执行的计划。</span></div>
      </div>
      <nav class="footer-links" aria-label="页脚导航">
        <router-link to="/demo">方案示例</router-link>
        <router-link to="/profile">健康画像</router-link>
        <router-link to="/plan/new">开始规划</router-link>
      </nav>
      <p class="footer-meta">AI 建议仅供健康管理参考，不替代专业医疗诊断。</p>
    </div>
  </footer>
</template>

<style scoped lang="scss">
.app-footer {
  margin-top: clamp(72px, 10vw, 128px);
  padding: 54px 0 34px;
  overflow: hidden;
  border-top: 1px solid rgba($color-sage, .14);
  background: linear-gradient(135deg, $color-surface-soft, $color-surface-warm);
  color: $color-text-secondary;
}
.footer-inner { display: grid; grid-template-columns: minmax(280px, 1fr) auto; align-items: center; gap: 34px 60px; }
.footer-brand { display: flex; align-items: center; gap: 14px; }
.footer-logo { --icon-color: #{$color-sage-dark}; --icon-bg: #{$color-sage-light}; border: 1px solid rgba($color-sage,.18); border-radius: 14px; box-shadow: none; }
.footer-brand > div { display: grid; gap: 2px; }
.footer-brand strong { color: $color-text-primary; font-size: 20px; letter-spacing: -.03em; }
.footer-brand span { font-size: 13px; }
.footer-links { display: flex; align-items: center; gap: 24px; }
.footer-links a { color: $color-text-secondary; font-size: 13px; font-weight: 650; }
.footer-links a:hover { color: $color-sage-dark; }
.footer-meta { grid-column: 1 / -1; padding-top: 22px; border-top: 1px solid rgba($color-sage,.16); color: $color-text-placeholder; font-size: 11px; }

@media (max-width: $breakpoint-md) {
  .footer-inner { grid-template-columns: 1fr; }
  .footer-links { flex-wrap: wrap; gap: 12px 22px; }
}

@media (max-width: $breakpoint-sm) {
  .app-footer { margin-top: 64px; padding: 38px 0 26px; }
}
</style>
