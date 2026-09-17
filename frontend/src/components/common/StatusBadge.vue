<script setup lang="ts">
withDefaults(defineProps<{
  label: string
  tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info'
}>(), {
  tone: 'neutral',
})
</script>

<template>
  <span class="status-badge" :class="`status-badge--${tone}`">
    <i aria-hidden="true" />
    {{ label }}
  </span>
</template>

<style scoped lang="scss">
.status-badge {
  display: inline-flex;
  min-height: 30px;
  align-items: center;
  gap: 7px;
  padding: 5px 10px;
  border: 1px solid $color-border;
  border-radius: $radius-round;
  background: $color-surface;
  color: $color-text-secondary;
  font-size: 12px;
  font-weight: 720;
}

.status-badge i { width: 8px; height: 8px; border-radius: 50%; background: $color-text-placeholder; }
.status-badge--success { border-color: rgba($color-success, .28); background: $color-surface-muted; color: $color-success; }
.status-badge--success i { background: $color-success; }
.status-badge--warning { border-color: rgba($color-warning, .3); background: $amber-100; color: $color-warning; }
.status-badge--warning i { background: $color-warning; }
.status-badge--danger { border-color: rgba($color-danger, .3); background: $color-surface-danger; color: $color-danger; }
.status-badge--danger i { background: $color-danger; }
.status-badge--info { border-color: rgba($color-info, .26); background: $blue-100; color: $color-info; }
.status-badge--info i { background: $color-info; }
</style>
