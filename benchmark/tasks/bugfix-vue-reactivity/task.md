# Fix Vue 3 reactivity bug in form component

The `useForm` composable in `composables/useForm.js` has a reactivity bug. When form fields are updated, the `isValid` computed property doesn't react to changes.

## Bug
- `isValid` always returns `false` even when all fields are filled
- The `errors` object doesn't update when fields change
- Root cause: `reactive()` is used with plain object assignment which breaks Vue's reactivity tracking for nested properties

## Current behavior
```js
const form = reactive({ username: '', email: '' })
form.username = 'alice'  // this works
```
But when resetting: `Object.assign(form, initialValues)` breaks reactivity because the validation watcher doesn't detect the change.

## Requirements
1. Fix `isValid` to correctly react to field changes
2. Fix `validate()` to update `errors` reactively
3. Fix `resetForm()` to preserve reactivity when resetting fields
4. Keep the same API: `useForm(initialValues, rules)` returns `{ form, errors, isValid, validate, resetForm }`
