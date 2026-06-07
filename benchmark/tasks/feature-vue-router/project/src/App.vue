<template>
  <div>
    <nav>
      <a href="/">Home</a>
      <a href="/about">About</a>
    </nav>
    <main>
      <Home />
      <About />
    </main>
  </div>
</template>

<script setup>
import Home from './views/Home.vue'
import About from './views/About.vue'
</script>