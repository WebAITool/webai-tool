/**
 * Tests for bugfix-vue-reactivity task.
 * Run with: node test_reactivity.js
 *
 * The buggy code uses Object.assign() on reactive objects which breaks
 * Vue's reactivity tracking. The fix must replace Object.assign with
 * individual property assignments.
 */

function test(name, fn) {
  try { fn(); console.log(`PASS: ${name}`); }
  catch(e) { console.log(`FAIL: ${name} — ${e.message}`); process.exitCode = 1; }
}

function assertTrue(val, msg) {
  if (!val) throw new Error(msg || 'Expected truthy value');
}

function assertFalse(val, msg) {
  if (val) throw new Error(msg || 'Expected falsy value');
}

const fs = require('fs');
const path = require('path');
const source = fs.readFileSync(path.join(__dirname, '..', 'composables', 'useForm.js'), 'utf8');

test("useForm is exported", () => {
  assertTrue(source.includes('useForm'), "useForm not exported");
});

test("resetForm does NOT use Object.assign on form", () => {
  // Object.assign(form, ...) breaks Vue reactivity — must assign fields individually
  assertFalse(/Object\.assign\(form\s*,/.test(source),
    "Object.assign(form, ...) breaks reactivity — use individual field assignments");
});

test("resetForm does NOT use Object.assign on errors", () => {
  assertFalse(/Object\.assign\(errors\s*,/.test(source),
    "Object.assign(errors, ...) breaks reactivity — use individual field assignments");
});

test("resetForm assigns fields individually", () => {
  // The fix should iterate Object.keys and assign each field: form[key] = initialValues[key]
  assertTrue(/Object\.keys/.test(source) || /for\s*\(/.test(source),
    "resetForm should iterate keys and assign individually to preserve reactivity");
});

test("validate does NOT use Object.assign on errors", () => {
  assertFalse(/Object\.assign\(errors/.test(source),
    "validate should not use Object.assign on errors");
});

test("errors is reactive/ref, not plain object", () => {
  // errors must be reactive({}) or ref({}), not const errors = {}
  assertFalse(/const errors = \{\}/.test(source),
    "errors should be reactive({}) or ref({}), not a plain const object");
});

test("uses Vue reactivity primitives", () => {
  assertTrue(source.includes('reactive') || source.includes('ref'),
    "Should use reactive or ref from vue");
  assertTrue(source.includes('computed'), "Should use computed from vue");
});

test("isValid computed accesses form fields", () => {
  assertTrue(source.includes('form[') || source.includes('form.'),
    "isValid computed should access form properties for dependency tracking");
});
