/**
 * Paginate an array — returns items for the given page (1-indexed).
 * BUG: off-by-one in end index calculation.
 */
function paginate(items, page, pageSize) {
  const start = (page - 1) * pageSize;
  const end = page * pageSize - 1;  // BUG: should be page * pageSize, not -1
  return items.slice(start, end);
}

module.exports = { paginate };
