"""
Generate a demo Vue 3 + FastAPI project for integration testing.

Creates a realistic project structure with:
- backend/  — FastAPI app with routers, models, services
- frontend/ — Vue 3 + Vite app with components and views

Usage:
    python generate_fake_project.py <target_dir>

Or programmatically:
    from generate_fake_project import create_structure
    create_structure("./my-test-project")
"""

import os
import argparse


def create_structure(base_dir: str) -> None:
    """Create the full demo project tree under base_dir."""
    _create_dirs(base_dir)
    _create_backend(base_dir)
    _create_frontend(base_dir)


# ─── Directory skeleton ──────────────────────────────────────────────


def _create_dirs(base: str) -> None:
    dirs = [
        "backend/app/routers",
        "backend/app/services",
        "backend/app/models",
        "frontend/src/components",
        "frontend/src/views",
        "frontend/src/assets",
        "frontend/public",
    ]
    for d in dirs:
        os.makedirs(os.path.join(base, d), exist_ok=True)


# ─── Backend (FastAPI) ───────────────────────────────────────────────


def _create_backend(base: str) -> None:
    _write(
        base,
        "backend/app/main.py",
        '''\
from fastapi import FastAPI
from .routers import auth, users, items

app = FastAPI(title="WebAI Demo", version="0.1.0")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(items.router)


@app.get("/")
def read_root():
    return {"status": "ok"}
''',
    )

    _write(
        base,
        "backend/app/routers/__init__.py",
        "",
    )

    _write(
        base,
        "backend/app/routers/auth.py",
        '''\
from fastapi import APIRouter
from ..models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(user: User):
    """Authenticate user and return a JWT token."""
    return {"token": "fake-jwt-token"}


@router.post("/register")
def register(user: User):
    """Register a new user."""
    return {"msg": "User created"}


# TODO: Add logout endpoint
''',
    )

    _write(
        base,
        "backend/app/routers/users.py",
        '''\
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def get_current_user():
    """Return the currently authenticated user."""
    return {"username": "admin", "role": "admin"}


@router.get("/{user_id}")
def get_user(user_id: int):
    """Return user by ID."""
    return {"id": user_id, "username": f"user_{user_id}"}
''',
    )

    _write(
        base,
        "backend/app/routers/items.py",
        '''\
from fastapi import APIRouter

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/")
def list_items():
    """Return all items."""
    return [{"id": 1, "name": "Widget"}, {"id": 2, "name": "Gadget"}]


@router.post("/")
def create_item(name: str):
    """Create a new item."""
    return {"id": 3, "name": name}
''',
    )

    _write(
        base,
        "backend/app/models/__init__.py",
        "",
    )

    _write(
        base,
        "backend/app/models/user.py",
        '''\
from pydantic import BaseModel


class User(BaseModel):
    username: str
    password: str
    email: str | None = None
    full_name: str | None = None
''',
    )

    _write(
        base,
        "backend/app/services/auth_service.py",
        '''\
"""Authentication business logic (stub)."""


def verify_password(plain: str, hashed: str) -> bool:
    """Compare plain text password with hashed version."""
    return plain == hashed  # stub — replace with bcrypt


def create_token(username: str) -> str:
    """Generate a JWT token for the given user."""
    return f"fake-token-for-{username}"
''',
    )


# ─── Frontend (Vue 3 + Vite) ────────────────────────────────────────


def _create_frontend(base: str) -> None:
    _write(
        base,
        "frontend/package.json",
        """\
{
  "name": "webai-demo-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-vue": "^5.0.0"
  }
}
""",
    )

    _write(
        base,
        "frontend/src/App.vue",
        """\
<script setup>
import Header from './components/Header.vue'
import Sidebar from './components/Sidebar.vue'
</script>

<template>
  <div class="app-container">
    <Header />
    <div class="content">
      <Sidebar />
      <router-view />
    </div>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.content {
  display: flex;
  flex: 1;
}
</style>
""",
    )

    _write(
        base,
        "frontend/src/components/Header.vue",
        """\
<script setup>
import { ref } from 'vue'

const title = ref('WebAI Demo')
const user = ref({ name: 'Admin' })

function toggleTheme() {
  document.body.classList.toggle('dark')
}
</script>

<template>
  <header class="header">
    <h1>{{ title }}</h1>
    <div class="user-info">
      <span>Welcome, {{ user.name }}</span>
      <button @click="toggleTheme">Theme</button>
      <!-- TODO: Add logout button here -->
    </div>
  </header>
</template>

<style scoped>
.header {
  background-color: #1a1a2e;
  color: #eee;
  padding: 0.75rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.user-info {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
</style>
""",
    )

    _write(
        base,
        "frontend/src/components/Sidebar.vue",
        """\
<script setup>
const links = [
  { name: 'Dashboard', path: '/' },
  { name: 'Users', path: '/users' },
  { name: 'Items', path: '/items' },
  { name: 'Settings', path: '/settings' },
]
</script>

<template>
  <aside class="sidebar">
    <nav>
      <ul>
        <li v-for="link in links" :key="link.path">
          <router-link :to="link.path">{{ link.name }}</router-link>
        </li>
      </ul>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 200px;
  background: #f5f5f5;
  padding: 1rem;
}
ul { list-style: none; padding: 0; }
li { margin-bottom: 0.5rem; }
</style>
""",
    )

    _write(
        base,
        "frontend/src/views/DashboardView.vue",
        """\
<template>
  <main class="dashboard">
    <h2>Dashboard</h2>
    <p>Welcome to the WebAI Demo application.</p>
  </main>
</template>

<style scoped>
.dashboard { padding: 2rem; }
</style>
""",
    )

    _write(
        base,
        "frontend/src/views/UsersView.vue",
        """\
<script setup>
import { ref, onMounted } from 'vue'

const users = ref([])

onMounted(async () => {
  // In real app: const res = await fetch('/api/users')
  users.value = [
    { id: 1, username: 'admin' },
    { id: 2, username: 'user1' },
  ]
})
</script>

<template>
  <main class="users">
    <h2>Users</h2>
    <ul>
      <li v-for="u in users" :key="u.id">{{ u.username }}</li>
    </ul>
  </main>
</template>
""",
    )


# ─── Helpers ─────────────────────────────────────────────────────────


def _write(base: str, relpath: str, content: str) -> None:
    """Write content to base/relpath, creating parent dirs if needed."""
    full = os.path.join(base, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


# ─── CLI ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a demo Vue 3 + FastAPI project for testing."
    )
    parser.add_argument("target_dir", help="Directory to create the project in")
    args = parser.parse_args()

    create_structure(args.target_dir)
    print(f"Generated demo project in {args.target_dir}")
