import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to attach API key if present
apiClient.interceptors.request.use((config) => {
  const apiKey = localStorage.getItem('apiKey')
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey
  }
  return config
})

// Response interceptor to handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to settings or show login prompt
      console.error('Unauthorized: Please check your API Key in Settings.')
    } else if (error.response?.data?.detail) {
      // Attach backend error detail for display in UI
      error.message = error.response.data.detail
    } else if (error.response?.status >= 500) {
      console.error('Server Error:', error.response.data?.detail || 'Unknown error')
    }
    return Promise.reject(error)
  }
)

export default apiClient
