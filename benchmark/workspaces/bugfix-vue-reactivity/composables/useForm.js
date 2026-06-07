/**
 * Vue 3 form composable with reactivity bugs.
 */
import { reactive, computed, watch } from 'vue'

export function useForm(initialValues, rules = {}) {
  const form = reactive({ ...initialValues })
  const errors = reactive({})
  const isValid = computed(() => {
    return Object.keys(rules).every(key => {
      const rule = rules[key]
      if (!rule) return true
      const result = rule(form[key])
      return result === true
    })
  })

  function validate() {
    Object.keys(rules).forEach(key => {
      const rule = rules[key]
      if (rule) {
        const result = rule(form[key])
        errors[key] = result === true ? '' : result
      }
    })
    return isValid.value
  }

  function resetForm() {
    Object.keys(initialValues).forEach(key => {
      form[key] = initialValues[key]
    })
    Object.keys(initialValues).forEach(key => {
      errors[key] = ''
    })
  }

  return { form, errors, isValid, validate, resetForm }
}
