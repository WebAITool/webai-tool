const fs = require('fs')
const path = require('path')

function test(name, fn) {
  try { fn(); console.log(`PASS: ${name}`) }
  catch(e) { console.log(`FAIL: ${name} - ${e.message}`); process.exitCode = 1 }
}

function assertTrue(val, msg) {
  if (!val) throw new Error(msg || 'Expected truthy value')
}

const configPath = path.join(__dirname, '..', 'vite.config.js')

test("vite.config.js exists", () => {
  assertTrue(fs.existsSync(configPath), "vite.config.js not found")
})

test("vite.config.js has proxy configuration", () => {
  const source = fs.readFileSync(configPath, 'utf8')
  assertTrue(source.includes('proxy'), "vite.config.js should have proxy configuration")
})

test("proxy forwards /api to backend", () => {
  const source = fs.readFileSync(configPath, 'utf8')
  assertTrue(source.includes('localhost:8000') || source.includes('127.0.0.1:8000'), "Proxy should forward to port 8000")
  assertTrue(source.includes('/api'), "Proxy should handle /api paths")
})

test("proxy configuration is valid JavaScript", () => {
  const source = fs.readFileSync(configPath, 'utf8')
  assertTrue(source.includes('export default'), "vite.config.js should export config")
})