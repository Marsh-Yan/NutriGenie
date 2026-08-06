import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import './assets/styles/global.scss'
import { useAuthStore } from './stores/auth'
import { pinia } from './stores/pinia'

const app = createApp(App)
app.use(pinia)
app.use(router)
useAuthStore().restore()
app.mount('#app')
