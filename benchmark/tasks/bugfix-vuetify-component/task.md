# Fix Vuetify component rendering

The Vue 3 app uses Vuetify 3 components (v-btn, v-text-field) in App.vue but the styles are not applied — the components render as unstyled HTML.

## Current code
- `src/main.js` creates the Vue app and mounts it
- `src/App.vue` contains a form with v-btn and v-text-field
- `src/plugins/vuetify.js` defines the Vuetify plugin but it is not imported in main.js

## Requirements

1. Import and register the Vuetify plugin in `src/main.js`
2. Import `vuetify/styles` CSS in `src/main.js`
3. Ensure all Vuetify components render with proper styling