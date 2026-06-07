const fs = require('fs')
const path = require('path')

function test(name, fn) {
  try { fn(); console.log(`PASS: ${name}`) }
  catch(e) { console.log(`FAIL: ${name} - ${e.message}`); process.exitCode = 1 }
}

function assertTrue(val, msg) {
  if (!val) throw new Error(msg || 'Expected truthy value')
}

const routerPath = path.join(__dirname, '..', 'src', 'router', 'index.js')
const mainJs = path.join(__dirname, '..', 'src', 'main.js')
const appVue = path.join(__dirname, '..', 'src', 'App.vue')
const contactVue = path.join(__dirname, '..', 'src', 'views', 'Contact.vue')

test("router/index.js exists", () => {
  assertTrue(fs.existsSync(routerPath), "src/router/index.js not found")
})

test("router/index.js defines routes", () => {
  const source = fs.readFileSync(routerPath, 'utf8')
  assertTrue(source.includes('createRouter'), "Should use createRouter")
  assertTrue(source.includes('Home'), "Should import/define Home route")
  assertTrue(source.includes('About'), "Should import/define About route")
  assertTrue(source.includes('Contact'), "Should import/define Contact route")
})

test("App.vue uses router-link", () => {
  const source = fs.readFileSync(appVue, 'utf8')
  assertTrue(source.includes('router-link'), "App.vue should use router-link instead of a tags")
})

test("App.vue has router-view", () => {
  const source = fs.readFileSync(appVue, 'utf8')
  assertTrue(source.includes('router-view'), "App.vue should have router-view")
})

test("main.js registers router", () => {
  const source = fs.readFileSync(mainJs, 'utf8')
  assertTrue(source.includes('.use('), "main.js should call app.use() for router")
})

test("Contact.vue exists", () => {
  assertTrue(fs.existsSync(contactVue), "src/views/Contact.vue should exist")
})

test("Contact.vue has template", () => {
  const source = fs.readFileSync(contactVue, 'utf8')
  assertTrue(source.includes('<template>'), "Contact.vue should have a template")
})