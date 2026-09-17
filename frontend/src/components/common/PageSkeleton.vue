<script setup lang="ts">
withDefaults(defineProps<{ rows?: number }>(), { rows: 3 })
</script>

<template>
  <div class="page-skeleton" aria-live="polite" aria-busy="true">
    <span class="sr-only">正在加载内容</span>
    <div class="page-skeleton__heading" aria-hidden="true" />
    <div v-for="row in rows" :key="row" class="page-skeleton__row" aria-hidden="true" />
  </div>
</template>

<style scoped lang="scss">
.page-skeleton { display: grid; gap: $space-4; }
.page-skeleton__heading,
.page-skeleton__row {
  overflow: hidden;
  border-radius: $radius-sm;
  background: $color-divider;
}
.page-skeleton__heading { width: min(420px, 72%); height: 38px; }
.page-skeleton__row { height: 92px; }
.page-skeleton__heading::after,
.page-skeleton__row::after {
  display: block;
  width: 45%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba($color-surface, .72), transparent);
  content: '';
  animation: skeleton-scan 1.3s ease-in-out infinite;
}
@keyframes skeleton-scan { from { transform: translateX(-110%); } to { transform: translateX(260%); } }
</style>
