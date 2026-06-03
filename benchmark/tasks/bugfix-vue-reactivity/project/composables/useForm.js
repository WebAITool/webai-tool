/**
 * Vue 3 form composable with reactivity bugs.
 */
import { reactive, computed, watch } from 'vue'

export function useForm(initialValues, rules = {}) {
  // BUG: reactive with Object.assign breaks reactivity tracking
  const form = reactive({ ...initialValues })
  const errors = reactive({})

  // BUG: this computed doesn't properly track dependencies
  const isValid = computed(() => {
    return Object.keys(rules).every(key => {
      const rule = rules[key]
      if (!rule) return true
      const result = rule(form[key])
      return result === true
    })
  })

  function validate() {
    // BUG: assigning to errors directly doesn't trigger reactivity properly
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
    // BUG: Object.assign on reactive doesn't properly trigger watchers
    Object.assign(form, { ...initialValues })
    Object.assign(errors, {})
  }

  return { form, errors, isValid, validate, resetForm }
}
