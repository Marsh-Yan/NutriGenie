<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <router-link :to="auth.isLoggedIn ? '/dashboard' : '/'" class="brand" aria-label="NutriGenie 首页">
    <span class="brand__mark" aria-hidden="true">N<span>.</span></span>
    <span class="brand__copy">
      <strong>NutriGenie</strong>
      <small>把饮食计划落在每一餐</small>
    </span>
  </router-link>
</template>

<style scoped lang="scss">
.brand {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 11px;
  color: $color-text-primary;
}

.brand:hover { color: $color-text-primary; }
.brand__mark { display: flex; width: 42px; height: 42px; align-items: center; justify-content: center; border-radius: 14px; background: $color-brand; color: white; font-size: 23px; font-weight: 750; letter-spacing: -.09em; }
.brand__mark span { color: $color-accent; }
.brand__copy { display: grid; line-height: 1.05; }
.brand__copy strong { font-size: 19px; font-weight: 750; letter-spacing: -.035em; }
.brand__copy small { margin-top: 4px; color: $color-text-secondary; font-size: 11px; font-weight: 500; }

@media (max-width: 820px) {
  .brand__copy small { display: none; }
  .brand__copy strong { font-size: 18px; }
  .brand__mark { width: 38px; height: 38px; font-size: 21px; }
}
</style>
