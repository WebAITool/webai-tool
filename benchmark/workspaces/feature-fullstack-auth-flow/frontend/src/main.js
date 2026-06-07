import { createApp } from 'vue'
import App from './App.vue'
import Vuetify from 'vuetify'
import 'vuetify/dist/vuetify.min.css'
import axios from 'axios'

// Configure axios base URL (adjust if needed)
axios.defaults.baseURL = 'http://localhost:8000'

// Intercept 401 responses to clear token
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      delete axios.defaults.headers.common['Authorization']
      window.location.reload() // Force reload to show login
    }
    return Promise.reject(error)
  }
)

// Restore token from localStorage on app load
const token = localStorage.getItem('token')
if (token) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
}

const app = createApp(App)
app.use(Vuetify)
app.mount('#app')
