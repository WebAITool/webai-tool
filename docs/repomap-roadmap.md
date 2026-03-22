# Repomap Roadmap: From File Tree to Aider-Level Context

Current state: Phases 1-2 are complete. `src/repo_map.py` uses `.scm` query files to extract definitions and references. `src/repo_graph.py` builds a cross-file reference graph. No ranking, no token budget yet.

Target: aider-level repomap that understands **who uses what**, ranks symbols by relevance, and fits into LLM context window.

Scope: Python, JavaScript, TypeScript, Vue.

---

## Phase 1: Switch from AST Walking to `.scm` Tag Queries -- DONE

Custom `.scm` query files in `src/queries/` (python, javascript, typescript, tsx). `_extract_tags` loads the `.scm` file, runs `Query.captures()`, and returns `Tag` dataclass instances with `kind="def"` or `kind="ref"`. Vue SFC parsing splits sections, then applies `.scm` queries to `<script>` content.

---

## Phase 2: Build the Cross-File Reference Graph -- DONE

`src/repo_graph.py` — `RepoGraph` class builds a directed graph using plain dicts (not rustworkx). Edges go from referencer files to definer files, weighted by raw reference count. Exposed as `get_symbol_graph` LangChain tool with BFS traversal in both directions (uses / used-by) and configurable depth.

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
| `rustworkx` | 3 | PageRank ranking (Phase 2 uses plain dicts instead) |
| `diskcache` | 6 | Tag caching |
| `pygments` | 7 | Fallback reference extraction |

Existing deps already cover tree-sitter (`tree-sitter-language-pack`).

---

## Minimum Viable Improvement

If time is limited, **Phase 1 + Phase 2 alone** give the biggest jump in quality. Just knowing cross-file references and presenting "file X defines `login`, referenced by files Y and Z" is already far more useful to the agent than a flat name list.
