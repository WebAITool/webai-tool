const { paginate } = require('../utils');

function test(name, fn) {
  try { fn(); console.log(`PASS: ${name}`); }
  catch(e) { console.log(`FAIL: ${name} — ${e.message}`); process.exitCode = 1; }
}

function assertEqual(actual, expected, msg) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a !== e) throw new Error(`${msg || ''} Expected ${e}, got ${a}`);
}

const items = [1,2,3,4,5,6,7,8,9,10];

test("page 1 returns first 3 items", () => {
  assertEqual(paginate(items, 1, 3), [1,2,3]);
});

test("page 2 returns next 3 items", () => {
  assertEqual(paginate(items, 2, 3), [4,5,6]);
});

test("page 3 returns items 7-9", () => {
  assertEqual(paginate(items, 3, 3), [7,8,9]);
});

test("page 4 returns last item", () => {
  assertEqual(paginate(items, 4, 3), [10]);
});

test("page beyond range returns empty", () => {
  assertEqual(paginate(items, 5, 3), []);
});

test("page_size equals total length", () => {
  assertEqual(paginate(items, 1, 10), items);
});

test("single item pages", () => {
  assertEqual(paginate(items, 3, 1), [3]);
});
