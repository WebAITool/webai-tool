# Add Pinia store for API data management

The Vue 3 app has an `api.js` module for fetching data but no state management. Add a Pinia store.

## Current code
- `api.js` has `fetchItems()`, `fetchItem(id)`, `createItem(data)` functions that return promises
- Components call `api.js` directly and manage loading/error states locally

## Requirements

1. Create `stores/items.js` with a Pinia store using `defineStore`:
   - **State**: `items` (array), `currentItem` (object|null), `loading` (boolean), `error` (string|null)
   - **Getters**: `itemCount` (returns items.length), `isLoading` (returns loading), `hasError` (returns !!error)
   - **Actions**:
     - `loadItems()` — calls `fetchItems()`, sets items, handles loading/error
     - `loadItem(id)` — calls `fetchItem(id)`, sets currentItem
     - `addItem(data)` — calls `createItem(data)`, pushes to items on success
     - `clearError()` — sets error to null

2. Import and use `api.js` functions inside actions
3. Store should use composition API style (`defineStore('items', () => { ... })`)
4. Export the store as `useItemsStore`
