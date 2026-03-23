@echo off
echo Examples:
echo.
echo   just show-map                             # file tree with code annotations
echo   just show-map src                         # only src/ directory
echo.
echo   just show-edges src                       # cross-file references
echo                                             #   builder.py -^> repo_graph.py via: RepoGraphLite
echo.
echo   just show-symbol _resolve_ref             # what does _resolve_ref call?
echo   just show-symbol _resolve_ref 2           # two levels deep (-^> make_edge -^> Edge)
echo.
echo   just show-impact extract_imports          # who breaks if extract_imports changes?
echo   just show-impact extract_imports upstream 1  # only direct callers
echo   just show-impact build downstream         # what does build() depend on?
echo.
echo   just search resolve                       # find symbols matching "resolve"
echo   just search extract Function              # only functions with "extract"
echo   just search graph - 5                     # top 5 results, any kind
echo.
echo   just show-changes                         # unstaged changes -^> affected symbols
echo   just show-changes staged                  # staged changes only
echo   just show-changes all                     # all uncommitted changes
echo.
echo   just run "build a page" "use vue 3"       # run the agent
echo   just run "add auth" "jwt" ./myapp         # agent works in ./myapp
echo.
echo   just test                                 # unit tests
echo   just lint                                 # ruff check
