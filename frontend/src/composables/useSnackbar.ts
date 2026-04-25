import { ref } from 'vue'

const message = ref('')
const color = ref('error')
const visible = ref(false)
let timeoutId: ReturnType<typeof setTimeout> | null = null

export function useSnackbar() {
  function show(msg: string, type: 'error' | 'success' | 'info' = 'error') {
    if (timeoutId) clearTimeout(timeoutId)
    message.value = msg
    color.value = type === 'error' ? 'error' : type === 'success' ? 'success' : 'info'
    visible.value = true
    timeoutId = setTimeout(() => {
      visible.value = false
    }, 5000)
  }

  return { message, color, visible, show }
}
