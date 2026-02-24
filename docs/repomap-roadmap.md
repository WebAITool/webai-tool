# Repomap Roadmap: From File Tree to Aider-Level Context

Current state: `src/repomap.py` walks directories, lists files, extracts class/function **names** via tree-sitter AST walking. No cross-references, no ranking, no token budget.

Target: aider-level repomap that understands **who uses what**, ranks symbols by relevance, and fits into LLM context window.

Scope: Python, JavaScript, TypeScript, Vue.

---

## Phase 1: Switch from AST Walking to `.scm` Tag Queries

**Problem:** Current code manually walks tree-sitter AST nodes with per-language `_NODE_CONFIG` dicts. This only extracts definitions, can't extract references, and is tedious to maintain.

**Solution:** Use tree-sitter `.scm` query files (S-expression pattern matching). These are declarative — one file per language describes what to capture.

**What to do:**
- Grab `.scm` tag files for: `python-tags.scm`, `javascript-tags.scm`, `typescript-tags.scm`, `tsx-tags.scm`
  - **Source option 1:** aider's repo (`aider/queries/tree-sitter-language-pack/`) — Apache 2.0 license, requires attribution
  - **Source option 2:** tree-sitter official grammar repos (each repo ships `tags.scm`) — typically MIT licensed, more permissive
- Store them in `src/queries/` or similar
- Replace `_extract_items()` + `_NODE_CONFIG` with a single function that:
  1. Loads the `.scm` file for the language
  2. Runs `Query(language, scm_text).captures(tree.root_node)`
  3. Classifies captures by tag name prefix:
     - `@name.definition.*` → `kind="def"`
     - `@name.reference.*` → `kind="ref"`
- Output: list of `Tag(file, symbol_name, line, kind)` tuples

**Key detail:** `.scm` queries capture both definitions AND references (function calls, imports, type usages). This is the foundation for everything else.

**Vue handling:** Keep the existing `_parse_vue` logic for splitting SFC into sections, but parse `<script>` contents using the `.scm` query approach instead of AST walking.

**Result:** Same output quality for definitions, plus you now have **references** for free.

---

## Phase 2: Build the Cross-File Reference Graph

**Problem:** Knowing that `auth.py` defines `login()` and `Header.vue` calls `login()` is useless if they're not connected.

**Solution:** Build a directed graph where edges go from files that **reference** a symbol to files that **define** it.

**What to do:**
- Collect all tags into two dicts:
  ```
  defines:    symbol_name -> {set of files that define it}
  references: symbol_name -> [list of files that reference it]
  ```
- For each symbol that appears in both dicts, create edges:
  ```
  for each referencer_file, definer_file:
      add edge(referencer -> definer, weight=sqrt(ref_count))
  ```
- Use `rustworkx.PyDiGraph` for the graph (Rust-backed, 3-100x faster than NetworkX, supports parallel edges — parallel edge weights are summed automatically during PageRank)
- Weight multipliers (optional but valuable):
  - Symbol uses camelCase/snake_case and len >= 8: `*10` (specific names are more meaningful)
  - Symbol starts with `_`: `*0.1` (private, less relevant)
  - Symbol defined in >5 files: `*0.1` (too generic, like `__init__`)

**Dependencies:** `rustworkx` (add to pyproject.toml)

**Result:** A graph that encodes "Header.vue depends on auth.py via `login`".

---

## Phase 3: PageRank Ranking

**Problem:** Dumping the entire graph into LLM context doesn't fit. Need to rank what matters most.

**Solution:** Personalized PageRank biased toward the files the agent is currently working with.

**What to do:**
- Store edge data as dicts: `G.add_edge(src, dst, {"weight": w, "ident": symbol_name})`
- Run `rustworkx.pagerank(G, personalization=pers_dict, weight_fn=lambda e: e["weight"], dangling=pers_dict)`
- Personalization vector: files the agent is actively editing/reading get ~100x weight vs others
- Distribute each file's PageRank score to its individual definitions proportionally to edge weights:
  ```
  for each outgoing edge from file:
      definition_rank[target_file, symbol] += file_rank * edge_weight / total_outgoing_weight
  ```
- Sort all (file, symbol) pairs by rank descending
- Exclude files the agent already has in full context

**Result:** A ranked list of the most relevant definitions across the whole repo.

---

## Phase 4: Token Budget and Binary Search

**Problem:** The ranked list might still be too large for the LLM context window.

**Solution:** Binary search over the number of top-ranked tags to include, targeting a token budget.

**What to do:**
- Accept `max_map_tokens` parameter (default ~1024, scale up when agent has few files in context)
- Binary search:
  ```
  lo, hi = 0, len(ranked_tags)
  while lo <= hi:
      mid = (lo + hi) // 2
      rendered = render(ranked_tags[:mid])
      tokens = count_tokens(rendered)
      if tokens within 15% of budget: break
      if tokens < budget: lo = mid + 1
      else: hi = mid - 1
  ```
- Token counting: for large texts, sample every 100th line and extrapolate (aider's trick to avoid tokenizing everything)

**Result:** Map output guaranteed to fit the context window, containing the most relevant symbols.

---

## Phase 5: Better Rendering

**Problem:** Current output is a flat indented tree. Doesn't show code context around definitions.

**Solution:** Show definition lines with parent scope headers and ellipsis gaps.

**Target output format:**
```
src/database.py:
|class DatabaseManager:
|    def __init__(self, connection_string):
...
|    def execute_query(self, query, params=None):
...

src/auth.py:
|def login(user: User):
...
|def logout():
...
```

**What to do:**
- For each file in the ranked output, collect the line numbers of included definitions
- Parse the file with tree-sitter to build a scope map (which lines belong to which AST scope)
- For each definition line, include its parent scope headers (e.g., show `class Foo:` above `def bar():`)
- Join non-contiguous regions with `...` ellipsis
- Aider uses `grep_ast.TreeContext` for this — evaluate whether to use it as dependency or reimplement (it's small)

**Result:** Compact, readable code outline that shows structure and hierarchy.

---

## Phase 6: Caching

**Problem:** Re-parsing every file on every agent step is wasteful, especially for large repos.

**Solution:** Disk cache keyed by (filename, mtime).

**What to do:**
- Use `diskcache` or simple SQLite/JSON cache
- Key: absolute file path
- Value: list of Tag tuples + file mtime
- On cache hit: check mtime, return cached tags if unchanged
- Store cache in `.webai.tags.cache/` in project root (add to .gitignore)

**Result:** Near-instant repomap generation after first run.

---

## Phase 7: Pygments Fallback for Missing References

**Problem:** Some `.scm` files only define `@name.definition.*` captures but no `@name.reference.*`. Without references, those files create no graph edges.

**Solution:** Fall back to Pygments lexer tokenization — treat every `Token.Name` as a reference.

**What to do:**
- After running `.scm` query on a file, check if any `"ref"` tags were produced
- If only `"def"` tags exist, run Pygments lexer on the file
- Every `Token.Name` token becomes a `Tag(kind="ref")`
- This is a coarse heuristic but ensures every file contributes edges

**Dependencies:** `pygments` (add to pyproject.toml)

**Priority:** Low — our 4 target languages (py/js/ts/tsx) all have good reference captures in their `.scm` files. This is a safety net.

---

## Dependency Order

```
Phase 1 (scm queries)
   |
   v
Phase 2 (graph)  -->  Phase 7 (pygments fallback, optional)
   |
   v
Phase 3 (pagerank)
   |
   v
Phase 4 (token budget)
   |
   v
Phase 5 (rendering)

Phase 6 (caching) -- independent, can be done anytime after Phase 1
```

## New Dependencies to Add

| Package | Phase | Purpose |
|---------|-------|---------|
| `rustworkx` | 2 | Graph construction + PageRank (Rust-backed, 3-100x faster than NetworkX) |
| `diskcache` | 6 | Tag caching |
| `pygments` | 7 | Fallback reference extraction |

Existing deps already cover tree-sitter (`tree-sitter-language-pack`).

---

## Minimum Viable Improvement

If time is limited, **Phase 1 + Phase 2 alone** give the biggest jump in quality. Just knowing cross-file references and presenting "file X defines `login`, referenced by files Y and Z" is already far more useful to the agent than a flat name list.
