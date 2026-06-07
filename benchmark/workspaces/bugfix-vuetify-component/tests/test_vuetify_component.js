const fs = require('fs')
const path = require('path')

function test(name, fn) {
  try { fn(); console.log(`PASS: ${name}`) }
  catch(e) { console.log(`FAIL: ${name} - ${e.message}`); process.exitCode = 1 }
}

function assertTrue(val, msg) {
  if (!val) throw new Error(msg || 'Expected truthy value')
}

const mainJs = path.join(__dirname, '..', 'src', 'main.js')

test("main.js imports vuetify plugin", () => {
  const source = fs.readFileSync(mainJs, 'utf8')
  assertTrue(source.includes('vuetify'), "main.js should import vuetify")
})

test("main.js imports vuetify/styles", () => {
  const source = fs.readFileSync(mainJs, 'utf8')
  assertTrue(source.includes('vuetify/styles'), "main.js should import vuetify/styles CSS")
})

test("main.js registers vuetify plugin", () => {
  const source = fs.readFileSync(mainJs, 'utf8')
  assertTrue(source.includes('.use('), "main.js should call app.use() for vuetify")
})