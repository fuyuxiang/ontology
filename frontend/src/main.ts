import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import './styles/global.css'
import './styles/builder-replica.css'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(i18n)
app.use(Antd)
app.mount('#app')
