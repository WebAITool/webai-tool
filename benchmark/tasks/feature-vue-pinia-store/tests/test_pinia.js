/**
 * Tests for feature-vue-pinia-store task.
 * Run with: node test_pinia.js
 */

const fs = require('fs');
const path = require('path');

function test(name, fn) {
  try { fn(); console.log(`PASS: ${name}`); }
  catch(e) { console.log(`FAIL: ${name} — ${e.message}`); process.exitCode = 1; }
}

function assertTrue(val, msg) {
  if (!val) throw new Error(msg || 'Expected truthy value');
}

const storePath = path.join(__dirname, '..', 'stores', 'items.js');

test("stores/items.js exists", () => {
  assertTrue(fs.existsSync(storePath), "stores/items.js file not found");
});

test("exports useItemsStore", () => {
  const source = fs.readFileSync(storePath, 'utf8');
  assertTrue(source.includes('useItemsStore'), "Should export useItemsStore");
});

test("uses defineStore", () => {
  const source = fs.readFileSync(storePath, 'utf8');
  assertTrue(source.includes('defineStore'), "Should use defineStore from pinia");
});

test("uses composition API style", () => {
  const source = fs.readFileSync(storePath, 'utf8');
  // Composition style: defineStore('name', () => { ... })
  assertTrue(source.includes('=>') || source.includes('function'), 
    "Should use composition API style (setup function)");
});

test("has state: items, currentItem, loading, error", () => {
  const source = fs.readFileSync(storePath, 'utf8');
  assertTrue(source.includes('items'), "Missing items state");
  assertTrue(source.includes('currentItem'), "Missing currentItem state");
  assertTrue(source.includes('loading'), "Missing loading state");
  assertTrue(source.includes('error'), "Missing error state");
});

test("has getters: itemCount, isLoading, hasError", () => {
  const source = fs.readFileSync(storePath, 'utf8');
  assertTrue(source.includes('itemCount') || source.includes('computed'), 
    "Missing itemCount getter or computed");
  assertTrue(source.includes('isLoading') || source.includes('computed'), 
    "Missing isLoading getter or computed");
  assertTrue(source.includes('hasError') || source.includes('computed'), 
    "Missing hasError getter or computed");
});

test("has actions: loadItems, loadItem, addItem, clearError", () => {
  const source = fs.readFileSync(storePath, 'utf8');
  assertTrue(source.includes('loadItems'), "Missing loadItems action");
  assertTrue(source.includes('loadItem'), "Missing loadItem action");
  assertTrue(source.includes('addItem'), "Missing addItem action");
  assertTrue(source.includes('clearError'), "Missing clearError action");
});

test("actions use api.js functions", () => {
  const source = fs.readFileSync(storePath, 'utf8');
  assertTrue(source.includes('fetchItems') || source.includes('api'), 
    "Actions should import/use api.js functions");
});

test("uses ref/computed from vue", () => {
  const source = fs.readFileSync(storePath, 'utf8');
  assertTrue(source.includes('ref') || source.includes('reactive'), 
    "Should use ref or reactive from vue");
  assertTrue(source.includes('computed'), "Should use computed from vue");
});

test("imports from pinia", () => {
  const source = fs.readFileSync(storePath, 'utf8');
  assertTrue(source.includes('pinia'), "Should import from pinia");
});
