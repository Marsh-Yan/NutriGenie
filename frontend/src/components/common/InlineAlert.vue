<script setup lang="ts">
import PremiumIcon from '@/components/common/PremiumIcon.vue'

withDefaults(defineProps<{
  title: string
  tone?: 'info' | 'warning' | 'danger' | 'success'
}>(), {
  tone: 'info',
})
</script>

<template>
  <div class="inline-alert" :class="`inline-alert--${tone}`" :role="tone === 'danger' ? 'alert' : 'status'">
    <PremiumIcon :name="tone === 'success' ? 'check' : 'alert'" :size="20" :box-size="40" />
    <div><strong>{{ title }}</strong><p><slot /></p></div>
  </div>
</template>

<style scoped lang="scss">
.inline-alert {
  display: flex;
  align-items: flex-start;
  gap: $space-3;
  padding: $space-4;
  border: 1px solid rgba($color-info, .25);
  border-radius: $radius-md;
  background: $blue-100;
  color: $color-text-primary;
}
.inline-alert :deep(.premium-icon) { border: 0; border-radius: 50%; box-shadow: none; }
.inline-alert strong { display: block; font-size: $text-sm; }
.inline-alert p { margin-top: 2px; color: $color-text-secondary; font-size: $text-sm; }
.inline-alert--warning { border-color: rgba($color-warning, .28); background: $amber-100; }
.inline-alert--danger { border-color: rgba($color-danger, .28); background: $color-surface-danger; }
.inline-alert--success { border-color: rgba($color-success, .24); background: $color-surface-muted; }
</style>
