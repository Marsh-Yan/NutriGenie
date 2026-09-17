<script setup lang="ts">
import { computed } from 'vue'

export type PremiumIconName =
  | 'target'
  | 'nutrition'
  | 'shopping'
  | 'timeline'
  | 'salad'
  | 'home'
  | 'profile'
  | 'plan'
  | 'flame'
  | 'strength'
  | 'blood'
  | 'leaf'
  | 'thinking'
  | 'alert'
  | 'check'
  | 'trophy'
  | 'clipboard'

const props = withDefaults(defineProps<{
  name: PremiumIconName
  size?: number | string
  boxSize?: number | string
  strokeWidth?: number
  label?: string
}>(), {
  size: 28,
  boxSize: 52,
  strokeWidth: 1.8,
})

const toCssSize = (value: number | string) => typeof value === 'number' ? `${value}px` : value

const iconStyle = computed(() => ({
  '--icon-size': toCssSize(props.size),
  '--icon-box-size': toCssSize(props.boxSize),
}))

const svgAttrs = computed(() => {
  if (props.label) return { role: 'img' as const, 'aria-label': props.label }
  return { 'aria-hidden': true as const }
})
</script>

<template>
  <span class="premium-icon" :class="`premium-icon--${name}`" :style="iconStyle">
    <svg viewBox="0 0 24 24" fill="none" v-bind="svgAttrs" :stroke-width="strokeWidth">
      <g stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <template v-if="name === 'target'">
          <circle cx="12" cy="12" r="8.5" opacity=".34" />
          <circle cx="12" cy="12" r="5.1" opacity=".62" />
          <circle cx="12" cy="12" r="1.65" fill="currentColor" stroke="none" />
          <path d="M14.6 4.8 20.4 2.6l-2.2 5.8-1.8-1.8-4 5.1" stroke-width="1.65" />
        </template>

        <template v-else-if="name === 'nutrition'">
          <path d="M5 19V10M10 19V6M15 19v-4M20 19V4" />
          <path d="M4 19.5h17" stroke-width="1.5" />
          <path d="m4.8 7.8 4-2.4 4.2 2 5.5-4" opacity=".66" />
          <circle cx="18.5" cy="3.4" r="1" fill="currentColor" stroke="none" />
        </template>

        <template v-else-if="name === 'shopping'">
          <path d="M4.5 9.5h15l-1.25 10H5.75L4.5 9.5Z" />
          <path d="M8 9.5a4 4 0 0 1 8 0" />
          <path d="M8 13.5h.01M12 13.5h.01M16 13.5h.01" stroke-width="2.4" />
          <path d="M7.2 17h9.6" opacity=".46" />
        </template>

        <template v-else-if="name === 'timeline'">
          <path d="M7 4.5v15M7 7h6.5a3 3 0 1 0 0-6H7" opacity=".55" />
          <circle cx="7" cy="5" r="2.1" fill="currentColor" stroke="none" opacity=".92" />
          <circle cx="7" cy="12" r="2.1" fill="currentColor" stroke="none" opacity=".66" />
          <circle cx="7" cy="19" r="2.1" fill="currentColor" stroke="none" opacity=".42" />
          <path d="M12 12h7M12 19h5" opacity=".6" />
        </template>

        <template v-else-if="name === 'salad'">
          <path d="M4 12.5h16c-.7 4.5-3.6 7-8 7s-7.3-2.5-8-7Z" />
          <path d="M6.5 20h11" />
          <path d="M8.2 11.7c-.8-2.6.6-4.7 3.2-5.2 1.2 2.2.4 4.4-1.6 5.2" fill="currentColor" opacity=".52" />
          <path d="M12.4 11.1c.5-3 2.7-4.3 5.2-3.7.1 2.6-1.8 4.3-4.4 4.2" fill="currentColor" opacity=".76" />
          <circle cx="7.2" cy="11" r="1.35" fill="currentColor" stroke="none" opacity=".42" />
          <circle cx="16.6" cy="11.1" r="1.45" fill="currentColor" stroke="none" opacity=".58" />
        </template>

        <template v-else-if="name === 'home'">
          <path d="m3.7 10.8 8.3-7 8.3 7v8.7a1 1 0 0 1-1 1H4.7a1 1 0 0 1-1-1v-8.7Z" />
          <path d="M9.3 20.5v-5.8h5.4v5.8M4 10.8h16" opacity=".6" />
        </template>

        <template v-else-if="name === 'profile'">
          <circle cx="12" cy="8" r="3.3" />
          <path d="M5.2 20c.5-3.6 3.1-5.7 6.8-5.7s6.3 2.1 6.8 5.7" />
          <path d="M4.2 20h15.6" opacity=".42" />
        </template>

        <template v-else-if="name === 'plan'">
          <path d="M6.5 4.2h7.1l3.9 3.9v11.7H6.5V4.2Z" />
          <path d="M13.5 4.2v4h4M9.3 13h5.4M9.3 16.3h3.8" opacity=".66" />
          <path d="m18.8 3 .45 1.55L20.8 5l-1.55.45-.45 1.55-.45-1.55L16.8 5l1.55-.45L18.8 3Z" fill="currentColor" stroke="none" />
        </template>

        <template v-else-if="name === 'flame'">
          <path d="M12.4 3.5c1.5 3.2-.3 4.7-1.8 6.1-1.4 1.3-2.6 2.4-1.8 4.8.4 1.3 1.5 2.2 3.1 2.5-1.1-1.5-.4-3.4.9-4.5 1.2-1 1.8-2 1.6-3.6 2.3 2.1 3.4 4.5 3.1 6.7-.4 3.1-2.7 5-5.8 5-3.7 0-6.3-2.5-6.3-5.9 0-3.2 2.3-5.7 4.1-7.3 1.1-1 2-2.1 2.9-3.8Z" fill="currentColor" opacity=".78" />
          <path d="M12.2 15.1c1.1 1.2.9 2.6-.2 3.5" opacity=".7" />
        </template>

        <template v-else-if="name === 'strength'">
          <path d="M7 8v8M4.5 9.5v5M9.5 10v4M17 8v8M19.5 9.5v5M14.5 10v4M9.5 12h5" />
          <path d="M4.5 9.5h2.5M4.5 14.5h2.5M17 9.5h2.5M17 14.5h2.5" stroke-width="2.4" />
        </template>

        <template v-else-if="name === 'blood'">
          <path d="M12 3.6S6.8 9 6.8 13.4a5.2 5.2 0 0 0 10.4 0C17.2 9 12 3.6 12 3.6Z" />
          <path d="M12 10.8v5M9.5 13.3h5" opacity=".68" />
        </template>

        <template v-else-if="name === 'leaf'">
          <path d="M19.7 4.5C12.1 4.8 6.1 6.8 5 12c-.7 3.3 1.3 6.3 4.7 6.1 5.6-.3 8.6-6.1 10-13.6Z" fill="currentColor" opacity=".42" />
          <path d="M4.4 20.3c2.5-4.2 5.7-7.1 10.1-9.1" />
          <path d="M10.4 7.4c1.1 1.8 1.5 3.5 1.3 5.2" opacity=".7" />
        </template>

        <template v-else-if="name === 'thinking'">
          <path d="M8.2 18.4a3.5 3.5 0 0 1-1.1-6.7A4.4 4.4 0 0 1 11 5.1a4.2 4.2 0 0 1 6 2.1 3.9 3.9 0 0 1 .6 7.5 3.6 3.6 0 0 1-3.5 4.5H8.2Z" />
          <path d="M9.3 9.3c1.2-.5 2.1-.2 2.6.5M14.1 9.1c.9-.2 1.6.1 2 .8M10.1 14.4c.9.7 2 .7 2.9 0M13.7 15.9c.8.3 1.6.1 2.1-.5" opacity=".62" />
          <path d="m19 3 .5 1.6L21 5l-1.5.4L19 7l-.5-1.6L17 5l1.5-.4L19 3Z" fill="currentColor" stroke="none" />
        </template>

        <template v-else-if="name === 'alert'">
          <path d="m12 4 8.1 14a1.3 1.3 0 0 1-1.1 2H5a1.3 1.3 0 0 1-1.1-2L12 4Z" fill="currentColor" opacity=".2" />
          <path d="M12 8.8v4.8M12 16.8h.01" stroke-width="2.1" />
        </template>

        <template v-else-if="name === 'check'">
          <circle cx="12" cy="12" r="8.5" fill="currentColor" opacity=".18" />
          <path d="m7.4 12.2 3 3 6.4-6.4" stroke-width="2.1" />
        </template>

        <template v-else-if="name === 'trophy'">
          <path d="M8 4.5h8v4.2a4 4 0 0 1-8 0V4.5Z" fill="currentColor" opacity=".24" />
          <path d="M8 6H5.5v1.7A3.3 3.3 0 0 0 8.8 11M16 6h2.5v1.7a3.3 3.3 0 0 1-3.3 3.3M12 12.7v3.1M8.5 19.2h7M9.5 15.8h5" />
        </template>

        <template v-else-if="name === 'clipboard'">
          <path d="M7 4.8h10v15.4H7V4.8Z" />
          <path d="M9.3 4.8V3.5h5.4v1.3M9.7 9.2h4.6M9.7 12.6h4.6M9.7 16h3" opacity=".66" />
          <path d="m17.6 16.1 1 1 2-2" />
        </template>
      </g>
    </svg>
  </span>
</template>

<style scoped lang="scss">
.premium-icon {
  --icon-color: #{$color-sage-dark};
  --icon-bg: #{$color-surface-soft};
  position: relative;
  display: inline-grid;
  place-items: center;
  width: var(--icon-box-size);
  height: var(--icon-box-size);
  flex: 0 0 auto;
  overflow: hidden;
  color: var(--icon-color);
  border: 1px solid rgba($color-sage-dark, .1);
  border-radius: $radius-sm;
  background: var(--icon-bg);
  box-shadow: none;
  isolation: isolate;
  vertical-align: middle;

  &::after { display: none; }
}

.premium-icon svg {
  width: var(--icon-size);
  height: var(--icon-size);
  overflow: visible;
}

.premium-icon--target,
.premium-icon--flame {
  --icon-color: #{$color-rose-dark};
  --icon-bg: #{$color-rose-light};
}

.premium-icon--nutrition,
.premium-icon--salad,
.premium-icon--leaf {
  --icon-color: #{$color-sage-dark};
  --icon-bg: #{$color-sage-light};
}

.premium-icon--shopping,
.premium-icon--trophy {
  --icon-color: #{$color-warning};
  --icon-bg: #{$amber-100};
}

.premium-icon--timeline,
.premium-icon--clipboard {
  --icon-color: #{$score-preference};
  --icon-bg: #{$plum-100};
}

.premium-icon--home,
.premium-icon--plan,
.premium-icon--thinking {
  --icon-color: #{$color-info};
  --icon-bg: #{$color-blue-soft};
}

.premium-icon--profile,
.premium-icon--strength {
  --icon-color: #{$score-preference};
  --icon-bg: #{$plum-100};
}

.premium-icon--blood,
.premium-icon--alert {
  --icon-color: #{$color-danger};
  --icon-bg: #{$color-rose-light};
}

.premium-icon--check {
  --icon-color: #{$color-success};
  --icon-bg: linear-gradient(145deg, #{$color-sage-light}, #{$color-lime-soft});
}
</style>
