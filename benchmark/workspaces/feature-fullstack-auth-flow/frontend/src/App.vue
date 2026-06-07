<template>
  <v-app>
    <v-main>
      <v-container v-if="!token">
        <v-row justify="center">
          <v-col cols="12" sm="8" md="4">
            <v-card>
              <v-card-title>Login</v-card-title>
              <v-card-text>
                <v-text-field
                  v-model="username"
                  label="Username"
                  outlined
                  required
                ></v-text-field>
                <v-text-field
                  v-model="password"
                  label="Password"
                  type="password"
                  outlined
                  required
                  @keyup.enter="login"
                ></v-text-field>
                <v-alert v-if="error" type="error" dismissible>{{ error }}</v-alert>
              </v-card-text>
              <v-card-actions>
                <v-btn color="primary" @click="login" :loading="loading">Login</v-btn>
              </v-card-actions>
            </v-card>
          </v-col>
        </v-row>
      </v-container>

      <v-container v-else>
        <v-row>
          <v-col cols="12">
            <v-card>
              <v-card-title>Dashboard</v-card-title>
              <v-card-text>
                <p>Welcome, {{ currentUser }}!</p>
                <v-btn color="error" @click="logout">Logout</v-btn>
              </v-card-text>
            </v-card>
            <v-card v-if="items.length" class="mt-4">
              <v-card-title>Items</v-card-title>
              <v-card-text>
                <v-list>
                  <v-list-item v-for="(item, index) in items" :key="index">
                    <v-list-item-content>{{ item }}</v-list-item-content>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
</template>

<script>
import axios from 'axios'

export default {
  data() {
    return {
      username: '',
      password: '',
      token: localStorage.getItem('token') || null,
      currentUser: localStorage.getItem('username') || '',
      items: [],
      error: '',
      loading: false
    }
  },
  mounted() {
    if (this.token) {
      this.fetchItems()
    }
  },
  methods: {
    async login() {
      this.error = ''
      this.loading = true
      try {
        const response = await axios.post('/api/login', {
          username: this.username,
          password: this.password
        })
        this.token = response.data.access_token
        this.currentUser = this.username
        localStorage.setItem('token', this.token)
        localStorage.setItem('username', this.username)
        axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        this.fetchItems()
      } catch (err) {
        if (err.response && err.response.data && err.response.data.detail) {
          this.error = err.response.data.detail
        } else {
          this.error = 'Login failed'
        }
      } finally {
        this.loading = false
      }
    },
    async fetchItems() {
      if (!this.token) return
      try {
        const response = await axios.get('/api/items')
        this.items = response.data
      } catch (err) {
        if (err.response && err.response.status === 401) {
          this.logout()
        }
      }
    },
    logout() {
      this.token = null
      this.currentUser = ''
      this.items = []
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      delete axios.defaults.headers.common['Authorization']
    }
  }
}
</script>

<style scoped>
</style>
