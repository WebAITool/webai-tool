# Add custom theme with dark mode toggle

The Vuetify app uses the default light theme. Refactor it to support a custom color palette and a dark mode toggle button.

## Current code
- `src/plugins/vuetify.js` creates Vuetify with default settings (no theme customization)
- `src/App.vue` has a simple layout with v-btn, v-card, v-app-bar using default colors

## Requirements

1. Define a custom light theme in Vuetify config:
   - `primary`: `#1976D2` (blue)
   - `secondary`: `#424242` (grey darken-3)
   - `accent`: `#82B1FF` (blue lighten-2)
   - `error`: `#FF5252` (red accent-2)

2. Define a dark theme variant (same colors but adjusted backgrounds)

3. Add a theme toggle button in the app bar that switches between light/dark

4. Persist the theme preference in `localStorage` so it survives page reload

5. Refactor `src/App.vue` to use `v-theme` or Vuetify's `theme` composable