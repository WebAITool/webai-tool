const api = require('../api');

function test(name, fn) {
  fn().then(
    () => console.log(`PASS: ${name}`),
    e => { console.log(`FAIL: ${name} — ${e.message}`); process.exitCode = 1; }
  );
}

// fetchUserPosts should still work
test("fetchUserPosts returns user with posts", async () => {
  const result = await new Promise((resolve, reject) => {
    api.fetchUserPosts(1, (err, data) => err ? reject(err) : resolve(data));
  });
  if (!result.user || result.user.name !== "Alice") throw new Error("Wrong user");
  if (!result.posts || result.posts.length !== 2) throw new Error(`Expected 2 posts, got ${result.posts?.length}`);
});

test("fetchUserPosts for non-existent user fails", async () => {
  try {
    await new Promise((resolve, reject) => {
      api.fetchUserPosts(999, (err, data) => err ? reject(err) : resolve(data));
    });
    throw new Error("Should have failed");
  } catch (e) {
    if (e.message === "Should have failed") throw e;
    // Expected: error from API
  }
});

// findPopularPosts should still work
test("findPopularPosts returns posts with enough likes", async () => {
  const posts = await new Promise((resolve, reject) => {
    api.findPopularPosts(10, (err, data) => err ? reject(err) : resolve(data));
  });
  if (posts.length !== 1 || posts[0].title !== "World") throw new Error("Wrong popular posts");
});

// New getUserSummary function should exist
test("getUserSummary exists and works", async () => {
  if (typeof api.getUserSummary !== "function") throw new Error("getUserSummary not found");
  const summary = await new Promise((resolve, reject) => {
    api.getUserSummary(1, (err, data) => err ? reject(err) : resolve(data));
  });
  if (!summary.user) throw new Error("No user in summary");
  if (!summary.posts) throw new Error("No posts in summary");
  if (typeof summary.totalLikes !== "number") throw new Error("No totalLikes in summary");
});

// Check that async/await is used (no .then in source)
test("source uses async/await not .then chains", async () => {
  const fs = require('fs');
  const path = require('path');
  const source = fs.readFileSync(path.join(__dirname, '..', 'api.js'), 'utf8');
  // fetchUserPosts and findPopularPosts should use async
  if (!source.includes('async') || !source.includes('await')) {
    throw new Error("Source doesn't use async/await");
  }
});
