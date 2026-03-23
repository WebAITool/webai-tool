#!/bin/sh
cat <<'EOF'
Examples:

  just show-map                             # file tree with code annotations
  just show-map src                         # only src/ directory

  just show-edges src                       # cross-file references
                                            #   builder.py -> repo_graph.py via: RepoGraphLite

  just show-symbol _resolve_ref             # what does _resolve_ref call?
  just show-symbol _resolve_ref 2           # two levels deep (→ make_edge → Edge)

  just show-impact extract_imports          # who breaks if extract_imports changes?
  just show-impact extract_imports upstream 1  # only direct callers
  just show-impact build downstream         # what does build() depend on?

  just search resolve                       # find symbols matching "resolve"
  just search extract Function              # only functions with "extract"
  just search graph - 5                     # top 5 results, any kind

  just show-changes                         # unstaged changes → affected symbols
  just show-changes staged                  # staged changes only
  just show-changes all                     # all uncommitted changes

  just run 'build a page' 'use vue 3'      # run the agent
  just run 'add auth' 'jwt' ./myapp        # agent works in ./myapp

  just test                                 # unit tests
  just lint                                 # ruff check
EOF
