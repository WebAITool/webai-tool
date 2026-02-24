# Loop Detection: Design & Observed Behavior

## Problem

An autonomous agent that writes and executes code needs a mechanism to detect when it is stuck. Without one, it burns through iterations (and API credits) repeating the same actions.

### Why thought-based detection failed

The original implementation compared consecutive plans (thoughts) using `SequenceMatcher` with a 0.95 threshold. This produced **false positives**: when the agent focuses on a sub-problem, plans naturally converge in wording even though `code_action` is trying different things. In integration tests the agent completed its task but was killed because plans looked similar.

## Current Design (action-based)

All detection logic lives in `state_check()` in `src/lg_agent.py`. It only runs when the decision is `code_action` — if `think` already said `[GOAL_ACHIEVED]` or `max_steps` was hit, those take priority.

### Three checks, in order

| # | Check | Condition | What it means |
|---|-------|-----------|---------------|
| 1 | Consecutive failures | Last 2 actions contain `"code was not executed"` | Code agent cannot produce valid code at all |
| 2 | Stale filesystem | `tree` unchanged for 3+ iterations | Code runs but modifies nothing |
| 3 | Repeated code | Code blocks from last 2 actions have `similarity() > 0.85` | Agent submitting the same approach again |

Only the first matching check fires per iteration. Each produces a specific wakeup message injected into the next `think` call.

### Escalation

1. **First detection** → set `wakeup`, route to `think` (give the agent one chance to reframe).
2. **Second consecutive detection** (wakeup already set) → route to `review` (reviewer reads actual project files). If YES → clean exit. If NO → back to `think` with specific reviewer feedback, `max_steps` as the ultimate backstop.

### Helper: `_extract_code_from_action()`

Parses successful action strings by splitting on `"executed code:\n"` / `"\nresult:\n"`. Returns `None` for failure actions (containing `"code was not executed"`). This is what feeds into the similarity check.

### State fields

```python
prev_tree: str       # tree snapshot from previous iteration
stale_count: int     # consecutive iterations with unchanged tree
```

Both are updated every iteration regardless of decision, so the counters stay accurate even when loop detection itself is skipped.

## Historical: The Verification Loop (solved by `review` node)

Before the `review` node was introduced, integration tests showed a consistent pattern:

```
Iter 1: think (plan work) → code_action (creates/modifies files)     ← actual work
Iter 2: think (plan verify) → code_action (reads files to check)     ← verification
Iter 3: think (plan verify) → code_action (reads files again)        ← repeated verification
        ↑ repeated code detected (similarity > 0.85), wakeup injected
Iter 4: think (with wakeup) → [GOAL_ACHIEVED] or escalation          ← exit
```

The agent would complete its task in 1 iteration, then waste 2-3 iterations on self-verification before loop detection caught it. The root cause: `think` planned verification as a regular step, and the old `try_to_end` node didn't actually read files — it just asked the LLM "did you finish?" with no evidence.

### Resolution

The `review` node replaced `try_to_end`. It reads actual project files and presents them to the LLM as a reviewer. `think` is instructed not to plan verification — just work and say `[GOAL_ACHIEVED]`. The reviewer handles the rest.

This eliminates the verification loop structurally: verification happens exactly once, at the end, with real file evidence.

### Expected flow after the change

```
Iter 1: think (plan work) → code_action (creates/modifies files)     ← actual work
Iter 2: think ([GOAL_ACHIEVED]) → review (reads files) → END          ← clean exit
```

In practice, the reviewer may reject the result (e.g. a bug in generated code). The feedback loop is:

```
think ([GOAL_ACHIEVED]) → review (VERDICT: NO, feedback) → think (with feedback) → code_action (fix) → ...
```

### Reviewer loop limit (`review_count`)

If the reviewer says NO three times in a row, the agent accepts the result and stops — to prevent an infinite reviewer↔coder loop. This is tracked by `review_count` in `AgentState`, incremented on each `VERDICT: NO` and checked at the start of `review()`.

### REPL ephemerality and file creation

A common failure mode: the code agent generates **in-memory** application code (e.g. `from fastapi import FastAPI; app = FastAPI()`) instead of **file-writing** code (`with open("app.py", "w") as f: f.write(content)`). The REPL executes the code without errors, but no files are created on disk.

This is addressed by the `code_action` prompt which explains that the REPL is ephemeral and includes an explicit example of writing files to disk via `open()`/`write()`. The generated code is also logged to stdout for diagnostics.

## Diagnostic logging

`state_check` prints code similarity and the first 120 characters of both code blocks on every iteration where two successful actions exist:

```
CODE SIMILARITY: 0.930
  prev code: "# Verify the current content of frontend/src/components/Header.vue\ntry:\n    with open('frontend/src/co"...
  curr code: '# Verify the current content of frontend/src/components/Header.vue to ensure the logout button and f'...
LOOP: repeated code (similarity > 0.85)
```

This runs even below threshold, making it easy to tune the 0.85 cutoff or diagnose false positives.
