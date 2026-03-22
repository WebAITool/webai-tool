# WebAI Toolkit: Architecture Overview

## Mission

WebAI Toolkit is an autonomous software engineering agent. It reads a goal and a project specification, then writes and executes code until the goal is achieved — without human intervention.

Two operating modes:

1. **Reverse engineering** — scans an existing project and generates an SRS document.
2. **Forward engineering** — takes a goal + spec, plans steps, writes code, executes it, and verifies completion.

---

## Agent Loop

The core is a **LangGraph** cyclic state machine with four nodes:

```
think → state_check → code_action → think  (loop)
              ↘ review → think (with feedback) or END
```

| Node | Role |
|------|------|
| `think` | Analyses context (goal, past actions, project tree). Outputs a natural-language plan for the next step. Does not plan verification — that is handled by `review`. |
| `state_check` | Increments iteration counter. Detects loops via action-based checks: consecutive code failures, stale filesystem (tree unchanged 3+ iters), repeated code blocks (similarity > 0.85). On first detection injects a wakeup message into `think`; on second consecutive detection routes to `review`. Trims action history to `action_memory_size`. Routes to `code_action`, `review`, or `END`. |
| `code_action` | Asks the LLM to write Python code implementing the plan. Executes it via `PythonREPL`. The prompt explains that the REPL is ephemeral and project files must be written to disk via `open()`/`write()`. Retries up to `patience` times on error. Logs generated code for diagnostics. Updates the repo map after success. |
| `review` | Reads actual project files (`_read_project_files`) and asks the LLM (as a reviewer) whether the goal is achieved. If YES → END. If NO → routes back to `think` with specific reviewer feedback in `wakeup` and increments `review_count`. After 3 failed reviews, accepts the result to prevent infinite reviewer↔coder loops. |

### State (`AgentState`)

```python
goal: str              # High-level objective
spec: str              # Project specification / context
plan: str              # Current plan from think node
actions: list[str]     # History of executed code + output
thoughts: list[str]    # History of plans / reasoning
tree: str              # Current repo map (from repo_map.py)
prev_tree: str         # Tree snapshot from previous iteration
stale_count: int       # Consecutive iterations with unchanged tree
review_count: int      # Consecutive failed reviews (capped at 3)
iter_cnt: int          # Loop counter
max_steps: int         # Hard limit on iterations
patience: int          # Max code retries per step
action_memory_size: int # How many past actions to keep in context
decision: str          # Routing flag for conditional edges
wakeup: str            # Message injected on loop detection
prjdir: str            # Working directory (normalized to absolute path)
```

---

## Modules

### `src/lg_agent.py` — Agent Core

LangGraph graph definition, node functions, state management. This is the main entry point for running the agent programmatically:

```python
from lg_agent import run_agent
run_agent(goal="...", spec="...", prjdir="./output", max_steps=30)
```

### `src/repo_map.py` — Repository Map Generator

Generates a tree-like map of the project with code-level annotations (classes, functions, methods, Vue SFC sections) via tree-sitter `.scm` query files stored in `src/queries/`. The core extraction function `_extract_tags` runs `.scm` queries and returns `Tag` dataclass instances (file, name, line, kind=def/ref).

Supported languages: Python, JavaScript, TypeScript, Vue.

Security: path traversal protection, symlink skipping, file size limits (512 KB), depth limits (30 dirs, 20 AST), output truncation (5000 lines).

Exposed as a LangChain `@tool` (`get_repo_structure`) so the agent can call it during execution. The `show_references` parameter enables cross-file reference annotations in the output.

### `src/repo_graph.py` — Cross-File Reference Graph

`RepoGraph` builds a directed graph from tags produced by `repo_map`: edges go from files that reference a symbol to files that define it. Weights are based on reference count and symbol specificity.

Exposed as a LangChain `@tool` (`get_symbol_graph`) — accepts a symbol name and returns its definitions, references, and related symbols.

### `src/lg_tools.py` — Shell Tool

LangChain tool wrapper for executing shell commands. Handles Windows/Linux path differences.

### `src/gener.py` — LLM Interface

Thin wrapper around the OpenAI-compatible API. Reads `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY` from environment.

### `src/makesrs_prod.py` — SRS Generator

Walks a project directory, reads files (or summarises large ones via LLM), and produces a Markdown SRS document.

- Files < 2000 chars → included verbatim
- Files >= 2000 chars → LLM-summarised (interfaces, dependencies, logic flow)

### `src/prompts.py` — Prompt Templates

| Prompt | Purpose |
|--------|---------|
| `specmaker` | Analyse code → write SRS |
| `header_maker` | Summarise a single file |
| `planner` | Convert SRS → implementation roadmap |
| `check_agent` | QA verification (experimental) |

### `src/main.py` — Pipeline Entry Point

Orchestrates the full pipeline: generate SRS from source project → run agent to build the target project.

---

## Dependency Graph

```
main.py
  ├── makesrs_prod.py → gener.py, prompts.py
  └── lg_agent.py
        ├── repo_map.py (get_repo_structure tool)
        ├── repo_graph.py (get_symbol_graph tool) → repo_map.py
        ├── lg_tools.py (shell_exec tool)
        └── gener.py (LLM calls via ChatOpenAI)
```

---

## Configuration

All config is via `.env` (see `.env.example`):

```env
LLM_MODEL=arcee-ai/trinity-large-preview:free
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your-key-here
```

Any OpenAI-compatible API works (OpenRouter, polza.ai, local servers).

**Note:** if these variables are not set, `lg_agent.py` falls back to hardcoded defaults (`z-ai/glm-4.7` on `api.polza.ai`). Always configure `.env` explicitly.

---

## Running

```bash
# Quick start
just setup
just run "build a landing page" "vue 3, tailwind" ./output

# View repo map
just repomap ./my-project

# Run tests
just test-unit          # unit tests (repomap, parsers, security)
just test-integration   # requires LLM API key (hello_world, add_feature, from_spec)
```
