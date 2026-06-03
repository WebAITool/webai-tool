/**
 * API module with callback hell — needs async/await refactor.
 */

// Simulated async data sources (callback-based)
const _users = {
  1: { id: 1, name: "Alice" },
  2: { id: 2, name: "Bob" },
};

const _posts = {
  1: { id: 1, userId: 1, title: "Hello", likes: 5 },
  2: { id: 2, userId: 1, title: "World", likes: 15 },
  3: { id: 3, userId: 2, title: "Test", likes: 3 },
};

function getUser(userId, callback) {
  setTimeout(() => {
    const user = _users[userId];
    if (user) callback(null, user);
    else callback(new Error("User not found"));
  }, 10);
}

function getPostsByUser(userId, callback) {
  setTimeout(() => {
    const posts = Object.values(_posts).filter(p => p.userId === userId);
    callback(null, posts);
  }, 10);
}

function getPostDetails(postId, callback) {
  setTimeout(() => {
    const post = _posts[postId];
    if (post) callback(null, post);
    else callback(new Error("Post not found"));
  }, 10);
}

// CALLBACK HELL — refactor this to async/await
function fetchUserPosts(userId, callback) {
  getUser(userId, (err, user) => {
    if (err) { callback(err); return; }
    getPostsByUser(userId, (err, posts) => {
      if (err) { callback(err); return; }
      let detailed = [];
      let remaining = posts.length;
      if (remaining === 0) { callback(null, { user, posts: [] }); return; }
      posts.forEach(post => {
        getPostDetails(post.id, (err, detail) => {
          if (err) { callback(err); return; }
          detailed.push(detail);
          remaining--;
          if (remaining === 0) {
            callback(null, { user, posts: detailed });
          }
        });
      });
    });
  });
}

function findPopularPosts(minLikes, callback) {
  setTimeout(() => {
    const all = Object.values(_posts).filter(p => p.likes >= minLikes);
    callback(null, all);
  }, 10);
}

module.exports = { fetchUserPosts, findPopularPosts, getUser, getPostsByUser, getPostDetails };
