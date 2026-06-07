# Add Vue Router with page navigation

The Vue 3 app has a single-page layout with a navigation bar but no routing. Add Vue Router to enable navigation between pages.

## Current code
- `src/main.js` creates the Vue app and mounts it
- `src/App.vue` has a hardcoded nav bar with Home, About links (using `<a>` tags that reload)
- `src/views/Home.vue` and `src/views/About.vue` exist as standalone pages

## Requirements

1. Install and configure `vue-router` in the project
2. Create `src/router/index.js` with routes:
   - `/` → Home view
   - `/about` → About view
   - `/contact` → Contact view (create `src/views/Contact.vue` with any content)
3. Replace `<a>` tags in App.vue with `<router-link>` components
4. Add `<router-view>` in App.vue for page rendering
5. Register the router in main.js using `app.use(router)`