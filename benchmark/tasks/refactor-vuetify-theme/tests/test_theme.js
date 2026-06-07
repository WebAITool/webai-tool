import * as fs from 'fs'
import * as path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

function test(name, fn) {
  try { fn(); console.log(`PASS: ${name}`) }
  catch(e) { console.log(`FAIL: ${name} - ${e.message}`); process.exitCode = 1 }
}

function assertTrue(val, msg) {
  if (!val) throw new Error(msg || 'Expected truthy value')
}

const mainJs = path.join(__dirname, '..', 'src', 'main.js')
const appVue = path.join(__dirname, '..', 'src', 'App.vue')

test("main.js defines custom theme colors", () => {
  const source = fs.readFileSync(mainJs, 'utf8')
  assertTrue(source.includes('primary'), "Should define primary color in theme")
  assertTrue(source.includes('secondary'), "Should define secondary color in theme")
  assertTrue(source.includes('accent') || source.includes('accent'), "Should define accent color in theme")
  assertTrue(source.includes('error'), "Should define error color in theme")
})

test("main.js has dark theme variant", () => {
  const source = fs.readFileSync(mainJs, 'utf8')
  assertTrue(source.includes('dark'), "Should define a dark theme variant")
})

test("main.js uses localStorage for theme persistence", () => {
  const source = fs.readFileSync(mainJs, 'utf8')
  assertTrue(source.includes('localStorage') || source.includes('localStorage'), "Should persist theme preference in localStorage")
})

test("App.vue has dark mode toggle button", () => {
  const source = fs.readFileSync(appVue, 'utf8')
  assertTrue(source.includes('toggle') || source.includes('dark') || source.includes('theme'), "App.vue should have a theme toggle button")
})

test("App.vue uses theme composable", () => {
  const source = fs.readFileSync(appVue, 'utf8')
  assertTrue(source.includes('useTheme') || source.includes('theme'), "App.vue should use useTheme composable from vuetify")
})