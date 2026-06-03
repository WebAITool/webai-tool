# Fix off-by-one error in array pagination

The `paginate()` function in `utils.js` returns wrong results for the last page.
When there are 10 items and page_size=3, page 4 should return 1 item but returns empty array.

## Bug
`paginate([1,2,3,4,5,6,7,8,9,10], 4, 3)` returns `[]` instead of `[10]`.

The slice indices are off by one — the end index is calculated incorrectly.

## Expected behavior
- `paginate(items, page, page_size)` returns items for that page (1-indexed)
- Page 1: items[0..page_size], Page 2: items[page_size..2*page_size], etc.
- Last page may have fewer items than page_size
