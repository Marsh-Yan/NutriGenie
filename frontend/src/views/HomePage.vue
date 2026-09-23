<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePlanStore } from '@/stores/plan'
import heroImage from '@/assets/editorial/meal-bowl.webp'
import avocadoImage from '@/assets/editorial/avocado.jpg'
import fruitImage from '@/assets/editorial/fruit.jpg'
import adjustmentImage from '@/assets/editorial/adjustment-food.webp'
import bannerImage from '@/assets/editorial/final-banner.webp'

const router = useRouter()
const auth = useAuthStore()
const plan = usePlanStore()

function start(prompt?: string) {
  if (prompt) {
    plan.draftInput = prompt
    plan.draftExampleIndex = -1
  }
  if (auth.isLoggedIn) router.push('/plan/new')
  else router.push({ name: 'auth', query: { mode: 'register', redirect: '/profile' } })
}

const goals = [
  { title: '轻松减脂', detail: '让热量控制融入日常三餐', prompt: '我想制定一周减脂饮食计划，兼顾饱腹感与日常预算' },
  { title: '科学增肌', detail: '重视蛋白质，也照顾做饭时间', prompt: '我想制定高蛋白增肌饮食计划，菜谱要简单易执行' },
  { title: '平稳控糖', detail: '留意碳水搭配与用餐节奏', prompt: '我想制定一周控糖饮食计划，减少精制碳水并保证营养均衡' },
  { title: '吃得均衡', detail: '让一周食材更丰富、采购更清楚', prompt: '我想制定一周均衡饮食计划，食材丰富、做法家常' },
]
</script>

<template>
  <div class="editorial-home">
    <section class="home-hero page-container" aria-labelledby="home-title">
      <div class="home-hero__copy">
        <span class="home-chip">一周三餐，从这里开始</span>
        <h1 id="home-title">吃得好，<br>也安排得好。</h1>
        <p>把健康目标、预算、忌口和已有食材告诉 NutriGenie。得到一份看得懂、买得到、做得出的饮食计划。</p>
        <div class="home-actions">
          <button class="home-primary" type="button" @click="start()">创建我的计划 <span aria-hidden="true">↗</span></button>
          <router-link class="home-secondary" to="/demo">看看方案示例</router-link>
        </div>
        <div class="home-hero__foot"><span>目标与约束一起考虑</span><span>营养与预算清晰可见</span></div>
      </div>
      <div class="home-hero__visual">
        <img :src="heroImage" alt="水果、米饭、鸡蛋和蔬菜组成的餐食" width="1018" height="628" fetchpriority="high">
        <div class="visual-caption"><span>从想法，到今天的每一餐</span><strong>让计划真正落在餐桌上</strong></div>
      </div>
    </section>

    <section class="home-section page-container" aria-labelledby="goal-title">
      <div class="section-intro">
        <div><span class="section-marker">你的目标</span><h2 id="goal-title">从你想改变的事开始</h2></div>
        <p>选一个方向作为起点。进入规划页后，你仍可以补充自己的预算、食材和饮食限制。</p>
      </div>
      <div class="goal-grid">
        <button v-for="(goal, index) in goals" :key="goal.title" class="goal-card" type="button" @click="start(goal.prompt)">
          <span class="goal-card__top"><span>{{ String(index + 1).padStart(2, '0') }}</span><span aria-hidden="true">↗</span></span>
          <span class="goal-card__bottom"><strong>{{ goal.title }}</strong><small>{{ goal.detail }}</small></span>
        </button>
      </div>
    </section>

    <section id="how-it-works" class="home-section page-container" aria-labelledby="work-title">
      <div class="section-intro"><div><span class="section-marker">如何工作</span><h2 id="work-title">一份计划，走完三件事</h2></div><router-link class="section-link" to="/demo">查看完整示例 <span aria-hidden="true">↗</span></router-link></div>
      <div class="story-grid">
        <article class="story-card"><div class="story-card__image"><img :src="avocadoImage" alt="牛油果、鸡蛋和蔬菜餐盘" loading="lazy" width="3072" height="4608"></div><div class="story-card__copy"><span>01 / 了解你</span><h3>先把边界说清楚</h3><p>健康画像、饮食偏好、预算与过敏原共同决定推荐范围。</p></div></article>
        <article class="story-card"><div class="story-card__image"><img :src="fruitImage" alt="苹果、坚果和水果餐食" loading="lazy" width="3648" height="5472"></div><div class="story-card__copy"><span>02 / 安排一周</span><h3>每天都好执行</h3><p>查看每日餐单、菜谱、营养分析和汇总后的采购清单。</p></div></article>
        <article class="story-card"><div class="story-card__image"><img :src="adjustmentImage" alt="日式餐食与茶具" loading="lazy" width="1200" height="1800"></div><div class="story-card__copy"><span>03 / 随时调整</span><h3>计划跟着生活走</h3><p>不满意就继续提出要求，也能查看历史版本，回到适合自己的安排。</p><router-link class="story-card__link" to="/recipes">先逛逛菜谱库 <span aria-hidden="true">↗</span></router-link></div></article>
      </div>
    </section>

    <section class="home-end page-container"><div class="home-end__copy"><span class="section-marker">开始规划</span><h2>下一餐，<br>从更好的安排开始。</h2><button class="home-primary home-primary--light" type="button" @click="start()">创建我的计划 <span aria-hidden="true">↗</span></button></div><img class="home-end__image" :src="bannerImage" alt="鸡蛋、面包与咖啡组成的早餐" width="1800" height="1200" loading="lazy"></section>
  </div>
</template>

<style scoped lang="scss">
.editorial-home { overflow: hidden; }
.home-hero { display: grid; grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr); gap: clamp(24px, 4vw, 64px); align-items: center; padding-block: clamp(48px, 7vw, 104px) 80px; }
.home-chip, .section-marker { display: inline-flex; width: fit-content; padding: 7px 12px; border: 1px solid $color-border; border-radius: 12px; background: white; color: $color-text-secondary; font-size: 12px; font-weight: 650; }
.home-hero h1 { margin-top: 26px; font-size: clamp(48px, 5.5vw, 76px); font-weight: 700; letter-spacing: -.06em; line-height: 1.14; }
.home-hero__copy > p { max-width: 44ch; margin-top: 26px; color: $color-text-secondary; font-size: clamp(16px, 1.4vw, 18px); line-height: 1.75; }
.home-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-top: 34px; }
.home-primary, .home-secondary { display: inline-flex; min-height: 50px; align-items: center; justify-content: center; gap: 24px; padding: 12px 19px; border-radius: 14px; font-size: 14px; font-weight: 650; cursor: pointer; }
.home-primary { border: 1px solid #09090b; background: #09090b; color: white; }
.home-primary:hover { background: #27272a; }
.home-secondary { border: 1px solid #d4d4d8; background: white; color: #18181b; }
.home-secondary:hover { color: #09090b; border-color: #09090b; }
.home-hero__foot { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 34px; color: $color-text-secondary; font-size: 12px; }
.home-hero__foot span::before { content: '✓'; margin-right: 7px; color: $color-text-primary; }
.home-hero__visual { position: relative; min-height: 520px; overflow: hidden; border-radius: 36px; background: #ded9cb; }
.home-hero__visual img { width: 100%; height: 100%; min-height: 520px; object-fit: cover; object-position: 52% center; }
.visual-caption { position: absolute; right: 20px; bottom: 20px; left: 20px; display: grid; gap: 3px; width: fit-content; max-width: calc(100% - 40px); padding: 14px 18px; border-radius: 14px; background: white; color: #09090b; }
.visual-caption span { color: #52525b; font-size: 12px; }.visual-caption strong { font-size: 15px; }
.home-section { padding-block: 64px 32px; }.section-intro { display: flex; align-items: end; justify-content: space-between; gap: 32px; margin-bottom: 28px; }.section-intro h2 { margin-top: 18px; font-size: clamp(32px, 4vw, 48px); line-height: 1.18; letter-spacing: -.045em; }.section-intro > p { max-width: 45ch; color: $color-text-secondary; font-size: 15px; }.section-link { color: $color-text-primary; font-weight: 650; }
.goal-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }.goal-card { display: flex; min-height: 220px; flex-direction: column; justify-content: space-between; padding: 24px; border: 1px solid $color-border; border-radius: 28px; background: white; color: $color-text-primary; text-align: left; cursor: pointer; }.goal-card:hover { border-color: #a1a1aa; }.goal-card__top { display: flex; justify-content: space-between; color: $color-text-secondary; font-size: 13px; }.goal-card__top span:last-child { color: #09090b; font-size: 22px; }.goal-card__bottom { display: grid; gap: 9px; }.goal-card strong { font-size: 24px; }.goal-card small { color: $color-text-secondary; font-size: 13px; line-height: 1.6; }
.story-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }.story-card { min-height: 430px; overflow: hidden; border: 1px solid $color-border; border-radius: 36px; background: white; }.story-card__image { height: 240px; overflow: hidden; }.story-card__image img { width: 100%; height: 100%; object-fit: cover; object-position: center 63%; }.story-card__copy { padding: 24px 28px 30px; }.story-card span { color: $color-text-secondary; font-size: 13px; }.story-card h3 { margin-top: 10px; font-size: 24px; }.story-card p { margin-top: 9px; color: $color-text-secondary; font-size: 14px; line-height: 1.7; }.story-card__link { display: inline-block; margin-top: 15px; color: $color-text-primary; font-size: 13px; font-weight: 650; }.story-card__link:hover { text-decoration: underline; }
.home-end { display: grid; min-height: 390px; grid-template-columns: 1fr 1fr; margin-top: 80px; padding: 0; overflow: hidden; border-radius: 36px; background: #18181b; }.home-end__copy { display: flex; flex-direction: column; align-items: flex-start; justify-content: center; padding: clamp(36px, 4vw, 64px); }.home-end .section-marker { border-color: #52525b; background: #27272a; color: white; }.home-end h2 { margin-top: 20px; color: white; font-size: clamp(38px, 4vw, 60px); line-height: 1.14; letter-spacing: -.05em; }.home-end__image { width: 100%; height: 100%; min-height: 390px; object-fit: cover; object-position: center 44%; }.home-primary--light { margin-top: 28px; border-color: white; background: white; color: #09090b; }.home-primary--light:hover { background: #ececee; }
@media (max-width: 1024px) { .home-hero { grid-template-columns: 1fr 1fr; }.goal-grid { grid-template-columns: repeat(2, 1fr); }.story-grid { grid-template-columns: repeat(2, 1fr); }.story-card:last-child { grid-column: 1 / -1; }.story-card:last-child .story-card__image img { object-position: center 52%; } }
@media (max-width: 768px) { .home-hero { grid-template-columns: 1fr; padding-block: 42px; }.home-hero__visual, .home-hero__visual img { min-height: 350px; }.section-intro { align-items: flex-start; flex-direction: column; }.story-grid { grid-template-columns: 1fr; }.story-card:last-child { grid-column: auto; }.home-end { grid-template-columns: 1fr; }.home-end__image { height: 260px; min-height: 0; } }
@media (max-width: 640px) { .home-hero h1 { font-size: 50px; }.home-hero__visual { border-radius: 28px; }.home-hero__visual, .home-hero__visual img { min-height: 310px; }.goal-grid { grid-template-columns: 1fr 1fr; gap: 10px; }.goal-card { min-height: 180px; padding: 18px; border-radius: 20px; }.goal-card strong { font-size: 20px; }.home-section { padding-block: 48px 16px; }.home-end { margin-top: 56px; border-radius: 24px; } }
</style>
