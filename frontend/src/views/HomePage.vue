<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Right } from '@element-plus/icons-vue'
import PremiumIcon from '@/components/common/PremiumIcon.vue'
import type { PremiumIconName } from '@/components/common/PremiumIcon.vue'
import { useAuthStore } from '@/stores/auth'
import { usePlanStore } from '@/stores/plan'

const router = useRouter()
const auth = useAuthStore()
const planStore = usePlanStore()
const loaded = ref(false)

onMounted(() => {
  window.setTimeout(() => { loaded.value = true }, 80)
})

function viewExample() {
  router.push('/demo')
}

function startUsing() {
  if (auth.isLoggedIn) router.push('/profile')
  else router.push({ name: 'auth', query: { mode: 'register', redirect: '/profile' } })
}

function startWithGoal(prompt: string) {
  planStore.draftInput = prompt
  planStore.draftExampleIndex = -1
  startUsing()
}

const goals: { icon: PremiumIconName; label: string; prompt: string }[] = [
  { icon: 'flame', label: '轻松减脂', prompt: '我想制定一周减脂饮食计划，兼顾饱腹感与日常预算' },
  { icon: 'strength', label: '科学增肌', prompt: '我想制定高蛋白增肌饮食计划，菜谱要简单易执行' },
  { icon: 'blood', label: '平稳控糖', prompt: '我想制定一周控糖饮食计划，减少精制碳水并保证营养均衡' },
  { icon: 'leaf', label: '均衡饮食', prompt: '我想制定一周均衡饮食计划，食材丰富、做法家常' },
]

const features: { icon: PremiumIconName; kicker: string; title: string; desc: string; metric: string; tone: string }[] = [
  { icon: 'target', kicker: '真正个性化', title: '目标、忌口与预算一起考虑', desc: '不是泛泛推荐菜谱，而是根据你的身体数据、饮食偏好和现实约束生成可执行方案。', metric: '画像驱动', tone: 'green' },
  { icon: 'nutrition', kicker: '清晰可解释', title: '每一餐都看得懂为什么', desc: '热量和宏量营养一目了然，同时展示匹配依据与需要留意的偏差。', metric: '营养校验', tone: 'blue' },
  { icon: 'timeline', kicker: '一周安排', title: '把“今天吃什么”变成时间线', desc: '三餐按天组织，菜谱、用量与烹饪步骤都在同一个计划里。', metric: '3–7 天', tone: 'peach' },
  { icon: 'shopping', kicker: '少浪费一点', title: '计划自动变成采购清单', desc: '按食材分类合并数量、估算成本，买什么、买多少更有把握。', metric: '预算核算', tone: 'yellow' },
]

const steps = [
  { no: '01', title: '建立健康画像', desc: '填写身体数据、目标和饮食限制，约 2 分钟。' },
  { no: '02', title: '用一句话描述需求', desc: '告诉 AI 天数、预算、现有食材和特别偏好。' },
  { no: '03', title: '获得并继续调整', desc: '查看完整方案，再用自然语言降低预算或替换餐食。' },
]
</script>

<template>
  <div class="home" :class="{ loaded }">
    <section class="hero page-container">
      <div class="hero-shell">
        <div class="hero-copy">
          <span class="hero-kicker"><i />AI-NATIVE NUTRITION PLANNER</span>
          <h1>一周吃什么，<br /><em>交给懂你的 AI。</em></h1>
          <p>从健康目标到每日预算，NutriGenie 把复杂的营养约束变成一份看得懂、买得到、做得出的饮食计划。</p>
          <div class="hero-actions">
            <el-button type="primary" size="large" round @click="startUsing">
              免费创建我的方案 <el-icon><Right /></el-icon>
            </el-button>
            <button class="text-action" type="button" @click="viewExample">
              先看完整示例 <span aria-hidden="true">↗</span>
            </button>
          </div>
          <div class="hero-proof" aria-label="产品特点">
            <span><b>✓</b> 约束与预算双重校验</span>
            <span><b>✓</b> 支持自然语言调整</span>
          </div>
        </div>

        <div class="hero-product" aria-label="NutriGenie 产品方案预览">
          <div class="product-orbit orbit-one" />
          <div class="product-orbit orbit-two" />
          <div class="product-window">
            <div class="window-bar">
              <div class="window-brand"><PremiumIcon name="salad" :size="15" :box-size="30" /><span>今日计划</span></div>
              <span class="ai-status"><i /> AI 已完成</span>
            </div>
            <div class="daily-heading">
              <div><small>星期三 · 第 3 天</small><strong>均衡与高蛋白</strong></div>
              <div class="score-orb"><b>92</b><span>匹配分</span></div>
            </div>
            <div class="ai-advice">
              <span>AI 建议</span>
              <p>午餐增加 15g 蛋白质，能更接近你的增肌目标。</p>
            </div>
            <div class="meal-preview">
              <div class="meal-art" aria-hidden="true">
                <span class="food food-one" /><span class="food food-two" /><span class="food food-three" /><span class="food food-four" />
              </div>
              <div class="meal-copy"><small>今日午餐</small><strong>香煎鸡胸藜麦碗</strong><span>25 分钟 · ¥18</span></div>
              <button type="button" aria-label="查看菜谱示例" @click="viewExample">→</button>
            </div>
            <div class="macro-grid">
              <div><span><i class="protein" />蛋白质</span><strong>42g</strong><b><i style="width: 84%" /></b></div>
              <div><span><i class="carb" />碳水</span><strong>54g</strong><b><i style="width: 68%" /></b></div>
              <div><span><i class="fat" />脂肪</span><strong>16g</strong><b><i style="width: 52%" /></b></div>
            </div>
          </div>
          <div class="floating-card budget-float"><span>本周预算</span><strong>¥286 <small>/ ¥300</small></strong></div>
          <div class="floating-card streak-float"><b>7</b><span>天完整计划</span></div>
        </div>
      </div>
    </section>

    <section class="goal-entry page-container" aria-labelledby="goal-title">
      <div class="goal-heading">
        <span>从你的目标开始</span>
        <h2 id="goal-title">现在最想改善什么？</h2>
      </div>
      <div class="goal-list">
        <button v-for="goal in goals" :key="goal.label" type="button" @click="startWithGoal(goal.prompt)">
          <PremiumIcon :name="goal.icon" :size="20" :box-size="40" />
          <span>{{ goal.label }}</span><b aria-hidden="true">→</b>
        </button>
      </div>
    </section>

    <section class="feature-section page-container" aria-labelledby="feature-title">
      <div class="section-heading">
        <span class="section-kicker">ONE PLAN, THE WHOLE WEEK</span>
        <h2 id="feature-title">不止给你菜谱，<br />还给你一套可执行的方法。</h2>
        <p>营养、时间和预算本来就不该分开考虑。</p>
      </div>
      <div class="bento-grid">
        <article v-for="(feature, index) in features" :key="feature.title" class="feature-card" :class="[`tone-${feature.tone}`, { wide: index < 2 }]">
          <div class="feature-top"><PremiumIcon :name="feature.icon" :size="25" :box-size="48" /><span>{{ feature.metric }}</span></div>
          <div><small>{{ feature.kicker }}</small><h3>{{ feature.title }}</h3><p>{{ feature.desc }}</p></div>
        </article>
      </div>
    </section>

    <section class="workflow page-container" aria-labelledby="workflow-title">
      <div class="workflow-panel">
        <div class="workflow-intro">
          <span class="section-kicker">HOW IT WORKS</span>
          <h2 id="workflow-title">三步，把想法变成一周饮食计划。</h2>
          <p>不用研究复杂的营养公式，也不用从上千道菜里逐个筛选。</p>
          <el-button type="primary" size="large" round @click="startUsing">开始建立画像 <el-icon><Right /></el-icon></el-button>
        </div>
        <ol class="steps-list">
          <li v-for="step in steps" :key="step.no"><span>{{ step.no }}</span><div><h3>{{ step.title }}</h3><p>{{ step.desc }}</p></div></li>
        </ol>
      </div>
    </section>

    <section class="final-cta page-container">
      <div class="cta-card">
        <div><span>今天就从一顿饭开始</span><h2>让下一周的每一餐，都更接近你的目标。</h2></div>
        <el-button size="large" round @click="startUsing">创建免费方案 <el-icon><Right /></el-icon></el-button>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.home { opacity: 0; transform: translateY(12px); transition: opacity .55s ease, transform .55s ease; }
.home.loaded { opacity: 1; transform: none; }

.hero { padding-top: clamp(22px, 3vw, 42px); }
.hero-shell {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, .94fr) minmax(460px, 1.06fr);
  align-items: center;
  min-height: 620px;
  padding: clamp(48px, 6vw, 82px);
  overflow: hidden;
  border: 1px solid rgba($color-sage, .18);
  border-radius: 42px;
  background:
    radial-gradient(circle at 6% 100%, rgba($color-rose-light, .72), transparent 28rem),
    radial-gradient(circle at 88% 4%, rgba($color-blue-soft, .82), transparent 24rem),
    linear-gradient(135deg, #DDE4DE 0%, #E7E7DF 52%, #EEE2DD 100%);
  box-shadow: 0 30px 80px rgba(79, 88, 82, .13);
}
.hero-shell::before { position: absolute; top: -150px; right: 34%; width: 360px; height: 360px; border: 1px solid rgba($color-sage,.14); border-radius: 50%; content: ''; }
.hero-copy { position: relative; z-index: 2; max-width: 590px; }
.hero-kicker { display: inline-flex; align-items: center; gap: 9px; margin-bottom: 24px; color: $color-sage-dark; font-size: 11px; font-weight: 800; letter-spacing: .14em; }
.hero-kicker i { width: 8px; height: 8px; border-radius: 50%; background: $color-rose; box-shadow: 0 0 0 6px rgba($color-rose,.12); }
.hero h1 { color: $color-text-primary; font-size: clamp(46px, 5.2vw, 72px); font-weight: 850; letter-spacing: -.065em; line-height: 1.05; }
.hero h1 em { position: relative; color: $color-rose-dark; font-style: normal; }
.hero-copy > p { max-width: 540px; margin-top: 24px; color: $color-text-secondary; font-size: clamp(16px, 1.35vw, 18px); line-height: 1.78; }
.hero-actions { display: flex; align-items: center; gap: 20px; margin-top: 34px; }
.hero-actions :deep(.el-button--primary) { border-color: $color-sage-dark; background: $color-sage-dark; box-shadow: 0 12px 28px rgba(79,88,82,.18); color: $color-text-inverse; }
.hero-actions :deep(.el-button--primary:hover) { border-color: $color-sage; background: $color-sage; }
.text-action { min-height: 48px; border: 0; background: transparent; color: $color-sage-dark; cursor: pointer; font-size: 14px; font-weight: 750; }
.text-action span { margin-left: 5px; color: $color-rose-dark; }
.hero-proof { display: flex; flex-wrap: wrap; gap: 14px 22px; margin-top: 28px; color: $color-text-secondary; font-size: 12px; }
.hero-proof span { display: inline-flex; align-items: center; gap: 7px; }
.hero-proof b { display: grid; place-items: center; width: 20px; height: 20px; border-radius: 50%; background: rgba($color-card,.72); color: $color-sage-dark; font-size: 12px; }

.hero-product { position: relative; min-height: 460px; margin-left: 36px; }
.product-orbit { position: absolute; border: 1px solid rgba($color-sage,.25); border-radius: 50%; }
.orbit-one { inset: 10px 0 8px 38px; }
.orbit-two { inset: 58px 54px 56px 0; border-style: dashed; opacity: .45; }
.product-window { position: absolute; inset: 30px 10px 22px 34px; z-index: 2; padding: 22px; border: 1px solid rgba($color-card,.9); border-radius: 28px; background: rgba($color-card,.96); box-shadow: 0 38px 80px rgba(79,88,82,.2); transform: rotate(1.2deg); }
.window-bar { display: flex; align-items: center; justify-content: space-between; }
.window-brand { display: flex; align-items: center; gap: 8px; color: $color-text-primary; font-size: 12px; font-weight: 800; }
.window-brand :deep(.premium-icon) { border-radius: 10px; box-shadow: none; }
.ai-status { display: inline-flex; align-items: center; gap: 6px; padding: 6px 9px; border-radius: 999px; background: $color-lime-soft; color: $color-sage-dark; font-size: 12px; font-weight: 750; }
.ai-status i { width: 6px; height: 6px; border-radius: 50%; background: $color-sage; }
.daily-heading { display: flex; align-items: center; justify-content: space-between; gap: 18px; margin: 22px 0 14px; }
.daily-heading > div:first-child { display: grid; }
.daily-heading small { color: $color-text-secondary; font-size: 12px; }
.daily-heading strong { color: $color-text-primary; font-size: 22px; letter-spacing: -.03em; }
.score-orb { display: grid; place-items: center; width: 58px; height: 58px; border: 5px solid $color-sage-light; border-top-color: $color-sage; border-radius: 50%; line-height: 1; }
.score-orb b { color: $color-sage-dark; font-size: 16px; }
.score-orb span { color: $color-text-secondary; font-size: 7px; }
.ai-advice { display: grid; grid-template-columns: auto 1fr; gap: 9px; padding: 12px; border-radius: 14px; background: $color-blue-soft; }
.ai-advice span { align-self: start; padding: 4px 7px; border-radius: 6px; background: $color-blue; color: #fff; font-size: 11px; font-weight: 800; }
.ai-advice p { color: $color-text-secondary; font-size: 12px; line-height: 1.55; }
.meal-preview { display: grid; grid-template-columns: 80px 1fr auto; align-items: center; gap: 14px; margin-top: 14px; padding: 12px; border: 1px solid $color-border; border-radius: 17px; }
.meal-art { position: relative; width: 80px; height: 64px; overflow: hidden; border-radius: 13px; background: #E9D7A8; }
.meal-art::before { position: absolute; inset: 16px 9px 7px; border-radius: 50% 50% 45% 45%; background: #F7F0D9; box-shadow: inset 0 -8px 0 #DABF87; content: ''; }
.food { position: absolute; z-index: 1; border-radius: 50%; }
.food-one { top: 19px; left: 19px; width: 18px; height: 18px; background: #8FA58F; }
.food-two { top: 23px; left: 34px; width: 22px; height: 16px; border-radius: 50% 30%; background: #B98578; transform: rotate(-14deg); }
.food-three { top: 33px; left: 25px; width: 26px; height: 12px; background: #C8B77D; transform: rotate(9deg); }
.food-four { top: 22px; right: 16px; width: 14px; height: 21px; border-radius: 40%; background: #99AA83; transform: rotate(16deg); }
.meal-copy { display: grid; min-width: 0; }
.meal-copy small { color: $color-text-secondary; font-size: 11px; }
.meal-copy strong { overflow: hidden; color: $color-text-primary; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.meal-copy span { color: $color-text-secondary; font-size: 11px; }
.meal-preview button { display: grid; place-items: center; width: 30px; height: 30px; border: 0; border-radius: 50%; background: $color-sage-dark; color: #fff; cursor: pointer; }
.macro-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 8px; margin-top: 14px; }
.macro-grid > div { display: grid; gap: 4px; padding: 9px; border-radius: 12px; background: $color-bg; }
.macro-grid span { display: flex; align-items: center; gap: 4px; color: $color-text-secondary; font-size: 11px; }
.macro-grid span i { width: 6px; height: 6px; border-radius: 50%; }
.protein { background: $score-utilization; }.carb { background: $score-season; }.fat { background: $score-preference; }
.macro-grid strong { color: $color-text-primary; font-size: 14px; }
.macro-grid > div > b { height: 3px; overflow: hidden; border-radius: 999px; background: $color-divider; }
.macro-grid > div > b i { display: block; height: 100%; border-radius: inherit; background: $color-sage; }
.floating-card { position: absolute; z-index: 3; display: grid; padding: 12px 14px; border: 1px solid rgba($color-card,.86); border-radius: 15px; background: rgba($color-card,.94); box-shadow: 0 18px 34px rgba(79,88,82,.14); backdrop-filter: blur(12px); }
.budget-float { right: -26px; bottom: 3px; }
.budget-float span,.streak-float span { color: $color-text-secondary; font-size: 11px; }
.budget-float strong { color: $color-sage-dark; font-size: 17px; }.budget-float small { font-size: 11px; font-weight: 600; }
.streak-float { top: 2px; left: 3px; grid-template-columns: auto 1fr; align-items: center; gap: 8px; }
.streak-float b { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 11px; background: $color-peach; color: $color-sage-dark; font-size: 17px; }

.goal-entry { display: grid; grid-template-columns: 240px 1fr; align-items: center; gap: 40px; padding-top: 34px; }
.goal-heading span { color: $color-sage; font-size: 11px; font-weight: 800; letter-spacing: .1em; }
.goal-heading h2 { margin-top: 3px; font-size: 22px; letter-spacing: -.03em; }
.goal-list { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; }
.goal-list button { display: flex; align-items: center; gap: 10px; min-height: 62px; padding: 10px 13px; border: 1px solid rgba($color-sage-dark,.11); border-radius: 18px; background: rgba(255,255,255,.78); box-shadow: $shadow-xs; color: $color-text-primary; cursor: pointer; font-weight: 700; text-align: left; transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease; }
.goal-list button:hover { border-color: rgba($color-sage,.4); box-shadow: $shadow-sm; transform: translateY(-2px); }
.goal-list button :deep(.premium-icon) { border-radius: 13px; box-shadow: none; }
.goal-list button b { margin-left: auto; color: $color-sage; }

.feature-section { display: grid; grid-template-columns: .72fr 1.28fr; gap: clamp(48px,7vw,100px); padding-top: clamp(100px,12vw,160px); }
.section-heading { align-self: start; position: sticky; top: 120px; }
.section-kicker { color: $color-sage; font-size: 11px; font-weight: 850; letter-spacing: .14em; }
.section-heading h2 { margin: 16px 0 18px; font-size: clamp(36px,4vw,54px); letter-spacing: -.055em; line-height: 1.08; }
.section-heading p { max-width: 400px; color: $color-text-secondary; font-size: 16px; }
.bento-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.feature-card { display: flex; flex-direction: column; justify-content: space-between; min-height: 280px; padding: 28px; border: 1px solid rgba($color-sage-dark,.09); border-radius: 28px; overflow: hidden; }
.feature-card.wide { grid-column: 1 / -1; min-height: 310px; }
.feature-top { display: flex; align-items: flex-start; justify-content: space-between; }
.feature-top :deep(.premium-icon) { border: 0; border-radius: 15px; box-shadow: none; }
.feature-top > span { padding: 6px 10px; border-radius: 999px; background: rgba(255,255,255,.6); color: $color-text-primary; font-size: 12px; font-weight: 750; }
.feature-card small { color: $color-text-secondary; font-size: 12px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
.feature-card h3 { max-width: 450px; margin: 8px 0; font-size: clamp(22px,2.3vw,31px); letter-spacing: -.04em; line-height: 1.15; }
.feature-card p { max-width: 520px; color: $color-text-secondary; font-size: 13px; line-height: 1.7; }
.tone-green { background: $color-lime-soft; }.tone-blue { background: $color-blue-soft; }.tone-peach { background: $color-surface-warm; }.tone-yellow { background: #EEE9D9; }

.workflow { padding-top: clamp(100px,12vw,160px); }
.workflow-panel { display: grid; grid-template-columns: .86fr 1.14fr; gap: 70px; padding: clamp(42px,6vw,76px); border: 1px solid rgba($color-sage,.16); border-radius: 36px; background: linear-gradient(135deg, $color-blue-soft, $color-rose-light); color: $color-text-primary; }
.workflow-intro h2 { margin: 14px 0 16px; color: $color-text-primary; font-size: clamp(34px,4vw,52px); letter-spacing: -.05em; line-height: 1.08; }
.workflow-intro p { margin-bottom: 28px; color: $color-text-secondary; }
.workflow-intro :deep(.el-button) { border-color: $color-sage-dark; background: $color-sage-dark; color: $color-text-inverse; }
.steps-list { list-style: none; }
.steps-list li { display: grid; grid-template-columns: 54px 1fr; gap: 18px; padding: 23px 0; border-bottom: 1px solid rgba($color-sage,.18); }
.steps-list li:first-child { padding-top: 0; }.steps-list li:last-child { padding-bottom: 0; border-bottom: 0; }
.steps-list > li > span { display: grid; place-items: center; width: 48px; height: 48px; border-radius: 15px; background: rgba($color-card,.65); color: $color-sage-dark; font-size: 12px; font-weight: 850; }
.steps-list h3 { color: $color-text-primary; font-size: 20px; }.steps-list p { margin-top: 4px; color: $color-text-secondary; font-size: 13px; }

.final-cta { padding-top: clamp(80px,10vw,128px); }
.cta-card { display: flex; align-items: center; justify-content: space-between; gap: 40px; padding: clamp(38px,5vw,66px); border: 1px solid rgba($color-rose,.15); border-radius: 34px; background: linear-gradient(135deg, $color-rose-light, $color-surface-warm); }
.cta-card span { color: $color-rose-dark; font-size: 11px; font-weight: 850; letter-spacing: .08em; }
.cta-card h2 { max-width: 760px; margin-top: 7px; font-size: clamp(30px,4vw,48px); letter-spacing: -.05em; line-height: 1.1; }
.cta-card :deep(.el-button) { flex: 0 0 auto; border-color: $color-sage-dark; background: $color-sage-dark; color: #fff; }

@media (max-width: 1080px) {
  .hero-shell { grid-template-columns: 1fr 430px; padding: 54px 46px; }
  .hero-product { margin-left: 12px; transform: scale(.94); transform-origin: right center; }
  .goal-entry { grid-template-columns: 1fr; gap: 16px; }
  .feature-section { grid-template-columns: 1fr; }
  .section-heading { position: static; }
  .section-heading p { max-width: 620px; }
}

@media (max-width: 900px) {
  .hero-shell { grid-template-columns: 1fr; padding: 54px; }
  .hero-copy { max-width: 680px; }
  .hero-product { width: min(100%, 560px); margin: 34px auto 0; transform: none; }
  .goal-list { grid-template-columns: repeat(2,1fr); }
  .workflow-panel { grid-template-columns: 1fr; gap: 48px; }
  .cta-card { align-items: flex-start; flex-direction: column; }
}

@media (max-width: $breakpoint-sm) {
  .hero { padding-top: 14px; }
  .hero-shell { min-height: auto; padding: 42px 22px 28px; border-radius: 28px; }
  .hero h1 { font-size: clamp(38px,12vw,50px); }
  .hero-copy > p { font-size: 15px; line-height: 1.7; }
  .hero-actions { align-items: stretch; flex-direction: column; gap: 8px; }
  .hero-actions :deep(.el-button) { width: 100%; margin: 0; }
  .hero-proof { display: grid; gap: 9px; }
  .hero-product { min-height: 390px; margin-top: 28px; }
  .product-window { inset: 18px 0 20px; padding: 16px; border-radius: 22px; transform: none; }
  .floating-card { display: none; }
  .daily-heading strong { font-size: 18px; }
  .meal-preview { grid-template-columns: 62px 1fr auto; gap: 10px; }
  .meal-art { width: 62px; }
  .macro-grid > div { padding: 7px; }
  .goal-entry { padding-top: 24px; }
  .goal-list { grid-template-columns: 1fr 1fr; gap: 8px; }
  .goal-list button { min-height: 58px; padding: 8px; font-size: 12px; }
  .goal-list button :deep(.premium-icon) { --icon-box-size: 34px; --icon-size: 17px; }
  .feature-section { padding-top: 88px; }
  .section-heading h2 { font-size: 36px; }
  .bento-grid { grid-template-columns: 1fr; }
  .feature-card,
  .feature-card.wide { grid-column: auto; min-height: 250px; padding: 24px; }
  .feature-card h3 { font-size: 24px; }
  .workflow { padding-top: 88px; }
  .workflow-panel { gap: 40px; padding: 38px 22px; border-radius: 28px; }
  .workflow-intro h2 { font-size: 34px; }
  .steps-list li { grid-template-columns: 46px 1fr; gap: 13px; }
  .steps-list > li > span { width: 42px; height: 42px; }
  .final-cta { padding-top: 72px; }
  .cta-card { padding: 34px 24px; border-radius: 28px; }
  .cta-card h2 { font-size: 31px; }
  .cta-card :deep(.el-button) { width: 100%; }
}
</style>
