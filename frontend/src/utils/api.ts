import axios from 'axios'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api'

const apiClient = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add API key if present
apiClient.interceptors.request.use(
  (config) => {
    const apiKey = localStorage.getItem('api_key')
    if (apiKey) {
      config.headers['X-API-Key'] = apiKey
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response) {
      const status = error.response.status
      const message = error.response.data?.detail || error.message

      if (status === 401) {
        // Redirect to settings or handle unauthorized access
        console.error('Unauthorized access. Redirecting to settings.')
        // window.location.href = '/settings' 
      } else if (status === 500) {
        console.error('Server Error:', message)
        // Dispatch event for global snackbar
        window.dispatchEvent(new CustomEvent('show-snackbar', { 
          detail: { text: message, color: 'error' } 
        }))
      }
    } else if (error.request) {
      console.error('Network Error:', error.message)
      window.dispatchEvent(new CustomEvent('show-snackbar', { 
        detail: { text: 'Network Error. Please check your connection.', color: 'error' } 
      }))
    } else {
      console.error('Error:', error.message)
    }

    return Promise.reject(error)
  }
)

export default apiClient
