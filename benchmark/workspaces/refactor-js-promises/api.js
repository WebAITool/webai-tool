const _users = {
  1: { id: 1, name: "Alice" },
  2: { id: 2, name: "Bob" },
};

const _posts = {
  1: { id: 1, userId: 1, title: "Hello", likes: 5 },
  2: { id: 2, userId: 1, title: "World", likes: 15 },
  3: { id: 3, userId: 2, title: "Test", likes: 3 },
};

async function getUser(userId, callback) {
  setTimeout(() => {
    const user = _users[userId];
    if (user) callback(null, user);
    else callback(new Error("User not found"));
  }, 10);
}

async function getPostsByUser(userId, callback) {
  setTimeout(() => {
    const posts = Object.values(_posts).filter(p => p.userId === userId);
    callback(null, posts);
  }, 10);
}

async function getPostDetails(postId, callback) {
  setTimeout(() => {
    const post = _posts[postId];
    if (post) callback(null, post);
    else callback(new Error("Post not found"));
  }, 10);
}

async function fetchUserPosts(userId, callback) {
  try {
    const user = await new Promise((resolve, reject) => getUser(userId, (err, data) => err ? reject(err) : resolve(data)));
    const posts = await new Promise((resolve, reject) => getPostsByUser(userId, (err, data) => err ? reject(err) : resolve(data)));
    const detailed = await Promise.all(posts.map(post => new Promise((resolve, reject) => getPostDetails(post.id, (err, data) => err ? reject(err) : resolve(data)))));
    callback(null, { user, posts: detailed });
  } catch (err) {
    callback(err);
  }
}

async function findPopularPosts(minLikes, callback) {
  try {
    const all = Object.values(_posts).filter(p => p.likes >= minLikes);
    callback(null, all);
  } catch (err) {
    callback(err);
  }
}

async function getUserSummary(userId, callback) {
  try {
    const { user, posts } = await new Promise((resolve, reject) => fetchUserPosts(userId, (err, data) => err ? reject(err) : resolve(data)));
    const totalLikes = posts.reduce((sum, post) => sum + post.likes, 0);
    callback(null, { user, posts, totalLikes });
  } catch (err) {
    callback(err);
  }
}

module.exports = { 
  fetchUserPosts, 
  findPopularPosts, 
  getUser, 
  getPostsByUser, 
  getPostDetails,
  getUserSummary
};
