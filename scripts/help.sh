#!/bin/sh
cat <<'EOF'
Examples:

  just repo-map                       # file tree of current dir
  just repo-map src                   # file tree of src/

  just repo-graph                     # cross-file references
  just repo-graph src                 # cross-file references in src/

  just symbol-graph get_map           # what does get_map() call?
  just symbol-graph get_map 2         # two levels deep

  just run 'build a page' 'use vue 3' # run the agent
  just run 'add auth' 'jwt' ./myapp   # agent works in ./myapp

  just test                           # unit tests
  just lint                           # ruff check
EOF
