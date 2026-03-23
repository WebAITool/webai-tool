@echo off
echo Examples:
echo.
echo   just show-map                       # file tree of current dir
echo   just show-map src                   # file tree of src/
echo.
echo   just show-edges                     # cross-file references
echo   just show-edges src                 # cross-file references in src/
echo.
echo   just show-symbol get_map            # what does get_map() call?
echo   just show-symbol get_map 2          # two levels deep
echo.
echo   just show-impact login              # who breaks if login changes?
echo   just show-impact login downstream   # what does login depend on?
echo   just show-impact login upstream 2   # upstream, max depth 2
echo.
echo   just search login                   # find symbols matching "login"
echo   just search validate Method         # search only methods
echo   just search user - 5               # top 5 results, any kind
echo.
echo   just show-changes                   # unstaged git changes -^> symbols
echo   just show-changes staged            # staged changes
echo   just show-changes all               # all uncommitted changes
echo.
echo   just run "build a page" "use vue 3" # run the agent
echo   just run "add auth" "jwt" ./myapp   # agent works in ./myapp
echo.
echo   just test                           # unit tests
echo   just lint                           # ruff check
