@echo off
echo Examples:
echo.
echo   just repo-map                       # file tree of current dir
echo   just repo-map src                   # file tree of src/
echo.
echo   just repo-graph                     # cross-file references
echo   just repo-graph src                 # cross-file references in src/
echo.
echo   just symbol-graph get_map           # what does get_map() call?
echo   just symbol-graph get_map 2         # two levels deep
echo.
echo   just run "build a page" "use vue 3" # run the agent
echo   just run "add auth" "jwt" ./myapp   # agent works in ./myapp
echo.
echo   just test                           # unit tests
echo   just lint                           # ruff check
