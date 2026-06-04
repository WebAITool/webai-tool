# Refactor callback hell to async/await

The `api.js` file uses deeply nested callbacks (callback hell). Refactor to use async/await.

## Current problems
- `fetchUserPosts()` has 4 levels of nesting
- `findPopularPosts()` has 3 levels of nesting
- Hard to read, hard to add error handling
- No proper error handling at all — errors are silently swallowed

## Requirements

1. **Rewrite using async/await** — no `.then()`, no nested callbacks
2. **Add proper error handling** — use try/catch, throw meaningful errors
3. **Keep the same public API** — `fetchUserPosts(userId)` and `findPopularPosts(minLikes)` must work identically
4. **Add `getUserSummary(userId)`** — new function that returns `{user, posts, totalLikes}` using the refactored code
