#!/bin/sh
cat <<'EOF'
Examples:

  just show-map                       # file tree of current dir
  just show-map src                   # file tree of src/

  just show-edges                     # cross-file references
  just show-edges src                 # cross-file references in src/

  just show-symbol get_map            # what does get_map() call?
  just show-symbol get_map 2          # two levels deep

  just show-impact login              # who breaks if login changes?
  just show-impact login downstream   # what does login depend on?
  just show-impact login upstream 2   # upstream, max depth 2

  just search login                   # find symbols matching "login"
  just search validate Method         # search only methods
  just search user - 5                # top 5 results, any kind

  just show-changes                   # unstaged git changes → symbols
  just show-changes staged            # staged changes
  just show-changes all               # all uncommitted changes

  just run 'build a page' 'use vue 3' # run the agent
  just run 'add auth' 'jwt' ./myapp   # agent works in ./myapp

  just test                           # unit tests
  just lint                           # ruff check
EOF
