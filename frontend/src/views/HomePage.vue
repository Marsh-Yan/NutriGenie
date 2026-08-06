<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ref, onMounted } from 'vue'
import { Right } from '@element-plus/icons-vue'
import PremiumIcon from '@/components/common/PremiumIcon.vue'
import type { PremiumIconName } from '@/components/common/PremiumIcon.vue'

const router = useRouter()
const loaded = ref(false)

onMounted(() => {
  setTimeout(() => { loaded.value = true }, 100)
})

function viewExample() {
  router.push('/demo')
}

const features: { icon: PremiumIconName; title: string; desc: string }[] = [
  { icon: 'target', title: '个性化规划', desc: '基于你的健康目标、饮食偏好和预算，量身定制' },
  { icon: 'nutrition', title: '科学营养分析', desc: '热量、蛋白质、脂肪、碳水平衡，数据驱动决策' },
  { icon: 'shopping', title: '智能采购清单', desc: '按分类列出所需食材，省时省力不浪费' },
  { icon: 'timeline', title: '一周饮食时间线', desc: '早中晚三餐规划，告别"今天吃什么"的烦恼' },
]
</script>

<template>
  <div class="home" :class="{ loaded }">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-bg" />
      <div class="page-container hero-content">
        <div class="hero-text">
          <h1 class="hero-title">
            <span class="gradient-text">AI 饮食规划</span>
            <br />
            从「吃什么」到「最合适」
          </h1>
          <p class="hero-subtitle">
            输入你的目标、偏好和预算，NutriGenie 为你生成<br />
            科学、个性、可执行的饮食方案
          </p>
          <div class="hero-actions">
            <el-button type="primary" size="large" round @click="router.push('/profile')">
              开始使用
              <el-icon class="btn-icon"><Right /></el-icon>
            </el-button>
            <el-button size="large" round @click="viewExample">
              查看方案示例
            </el-button>
          </div>
        </div>
        <div id="example-plan" class="hero-visual" aria-label="方案预览示例">
          <div class="plan-preview card">
            <div class="preview-head">
              <span>今日推荐</span><el-tag size="small" type="success" effect="light">匹配良好</el-tag>
            </div>
            <div class="preview-meal">
              <PremiumIcon name="salad" class="meal-icon" :size="30" :box-size="54" />
              <div><strong>香煎鸡胸藜麦碗</strong><small>高蛋白 · 约 25 分钟</small></div>
            </div>
            <div class="preview-stats">
              <div><strong>520</strong><span>kcal</span></div>
              <div><strong>42g</strong><span>蛋白质</span></div>
              <div><strong>¥18</strong><span>预计成本</span></div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Features -->
    <section class="features page-container">
      <div class="section-header">
        <h2 class="section-title">为什么选择 NutriGenie</h2>
        <p class="section-desc">不只是推荐菜谱，而是提供完整的饮食规划方案</p>
      </div>
      <div class="features-grid">
        <div
          v-for="(f, i) in features"
          :key="i"
          class="feature-card card"
          :style="{ transitionDelay: `${i * 0.1}s` }"
        >
          <span class="feature-icon">
            <PremiumIcon :name="f.icon" :size="36" :box-size="64" />
          </span>
          <h3 class="feature-title">{{ f.title }}</h3>
          <p class="feature-desc">{{ f.desc }}</p>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta page-container">
      <div class="cta-card">
        <h2 class="cta-title">准备好开始了吗？</h2>
        <p class="cta-desc">填写你的健康画像，3 分钟获得专属饮食规划</p>
        <el-button type="primary" size="large" round @click="router.push('/profile')">
          创建我的画像
        </el-button>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.home {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s ease, transform 0.6s ease;

  &.loaded {
    opacity: 1;
    transform: translateY(0);
  }
}

// ── Hero ──────────────────────────────────

.hero {
  position: relative;
  overflow: hidden;
  min-height: 68vh;
  display: flex;
  align-items: center;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, $color-sage 0%, $color-rose 50%, $color-sage-light 100%);
  opacity: 0.08;
  mask-image: radial-gradient(ellipse at 80% 40%, black 30%, transparent 70%);
  -webkit-mask-image: radial-gradient(ellipse at 80% 40%, black 30%, transparent 70%);
}

.hero-content {
  display: flex;
  align-items: center;
  gap: 60px;
  padding: 80px 20px;
  position: relative;
  z-index: 1;

  @media (max-width: $breakpoint-md) {
    flex-direction: column;
    text-align: center;
    gap: 40px;
  }
}

.hero-text {
  flex: 1;
}

.hero-title {
  font-size: 48px;
  font-weight: 800;
  line-height: 1.2;
  color: $color-text-primary;
  margin-bottom: 20px;

  @media (max-width: $breakpoint-md) {
    font-size: 36px;
  }
}

.hero-subtitle {
  font-size: 18px;
  color: $color-text-secondary;
  line-height: 1.7;
  margin-bottom: 36px;
}

.hero-actions {
  display: flex;
  gap: 12px;

  @media (max-width: $breakpoint-md) {
    justify-content: center;
  }
}

.btn-icon {
  margin-left: 4px;
}

.hero-visual {
  width: min(100%, 410px);
  flex-shrink: 0;
}

.plan-preview { padding: 24px; transform: rotate(1.5deg); box-shadow: $shadow-lg; }
.preview-head { display: flex; align-items: center; justify-content: space-between; color: $color-text-primary; font-size: 14px; font-weight: 700; }
.preview-meal { display: flex; align-items: center; gap: 14px; margin: 22px 0; padding: 16px; border-radius: $radius-md; background: rgba($color-sage,.08); }
.meal-icon { border-radius: 16px; }
.preview-meal div { display: flex; flex-direction: column; gap: 3px; }
.preview-meal strong { color: $color-text-primary; font-size: 16px; }
.preview-meal small { color: $color-text-secondary; }
.preview-stats { display: grid; grid-template-columns: repeat(3,1fr); gap: 8px; }
.preview-stats div { display: flex; flex-direction: column; padding: 10px; border-radius: $radius-sm; background: $color-bg; text-align: center; }
.preview-stats strong { color: $color-text-primary; font-size: 18px; }
.preview-stats span { color: $color-text-secondary; font-size: 11px; }

.hero-plate {
  position: relative;
  width: 240px;
  height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;

  @media (max-width: $breakpoint-md) {
    width: 180px;
    height: 180px;
  }
}

.plate-emoji {
  font-size: 80px;
  position: relative;
  z-index: 1;
  animation: float 3s ease-in-out infinite;

  @media (max-width: $breakpoint-md) {
    font-size: 60px;
  }
}

.plate-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid rgba($color-sage, 0.2);
  animation: pulse-ring 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-12px); }
}

@keyframes pulse-ring {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.08); opacity: 0.5; }
}

// ── Features ──────────────────────────────

.features {
  padding: 80px 20px;
}

.section-header {
  text-align: center;
  margin-bottom: 48px;
}

.section-title {
  font-size: 32px;
  font-weight: 700;
  color: $color-text-primary;
  margin-bottom: 12px;
}

.section-desc {
  font-size: 16px;
  color: $color-text-secondary;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 24px;
}

.feature-card {
  padding: 32px 24px;
  text-align: center;
  transition: all 0.3s;
  transition-delay: inherit;

  &:hover {
    transform: translateY(-4px);
  }
}

.feature-icon {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

.feature-title {
  font-size: 18px;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: 8px;
}

.feature-desc {
  font-size: 14px;
  color: $color-text-secondary;
  line-height: 1.6;
}

// ── CTA ───────────────────────────────────

.cta {
  padding: 40px 20px 80px;
}

.cta-card {
  background: linear-gradient(135deg, $color-sage, $color-sage-dark);
  border-radius: $radius-xl;
  padding: 60px 40px;
  text-align: center;
  color: #fff;
}

@media (max-width: $breakpoint-sm) {
  .hero { min-height: auto; }
  .hero-content { padding-top: 52px; padding-bottom: 60px; }
  .hero-title { font-size: 34px; }
  .hero-subtitle { font-size: 16px; }
  .hero-subtitle br { display: none; }
  .hero-actions { display: grid; grid-template-columns: 1fr; }
  .hero-actions .el-button { width: 100%; min-height: 46px; margin-left: 0; }
  .plan-preview { transform: none; padding: 18px; text-align: left; }
  .features { padding-top: 56px; }
  .cta-card { padding: 42px 22px; }
}

.cta-title {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 12px;
}

.cta-desc {
  font-size: 16px;
  opacity: 0.85;
  margin-bottom: 28px;
}
</style>
