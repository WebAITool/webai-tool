# WebAI Toolkit — development commands
# usage: just <recipe>    (install just: https://github.com/casey/just)

set dotenv-load
set windows-shell := ["pwsh", "-NoProfile", "-Command"]

# list available recipes
[group: 'help']
default:
    @just --list --list-submodules

# show usage examples
[group: 'help']
[unix]
help:
    @sh scripts/help.sh

# show usage examples
[group: 'help']
[windows]
help:
    @cmd /c scripts\help.bat

# ─── setup ────────────────────────────────────────────────────────────

# install all project dependencies
[group: 'setup']
install:
    @uv sync

# copy .env.example → .env (won't overwrite existing)
[group: 'setup']
[unix]
env:
    @if [ ! -f .env ]; then cp .env.example .env && echo "created .env from .env.example"; else echo ".env already exists"; fi

# copy .env.example → .env (won't overwrite existing)
[group: 'setup']
[windows]
env:
    @if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "created .env from .env.example" } else { Write-Host ".env already exists" }

# full first-time setup
[group: 'setup']
setup: env install

# ─── test ─────────────────────────────────────────────────────────────

# run unit tests (repo-map, parsers, security)
[group: 'test']
test-unit:
    uv run python -m pytest tests/unit/ -v

# run integration tests (requires LLM API key in .env)
[group: 'test']
test-integration:
    uv run python tests/integration/test_hello_world.py
    uv run python tests/integration/test_add_feature.py
    uv run python tests/integration/test_from_spec.py

# run unit tests (default; integration tests need LLM API key)
[group: 'test']
test: test-unit

# ─── run ──────────────────────────────────────────────────────────────

# run the agent
[group: 'run']
run goal spec prjdir=".":
    @uv run python scripts/run_agent.py "{{goal}}" "{{spec}}" "{{prjdir}}"

# show file tree with code annotations
[group: 'run']
show-map dir=".":
    @uv run python scripts/show_map.py "{{dir}}"

# alias for show-map
alias tree := show-map

# show cross-file reference edges
[group: 'run']
show-edges dir=".":
    @uv run python scripts/show_edges.py "{{dir}}"

# show symbol dependency graph
[group: 'run']
show-symbol name depth="1" dir=".":
    @uv run python scripts/show_symbol.py "{{name}}" "{{depth}}" "{{dir}}"

# show blast radius for a symbol
[group: 'run']
show-impact name direction="upstream" depth="3" dir=".":
    @uv run python scripts/show_impact.py "{{name}}" "{{direction}}" "{{depth}}" "{{dir}}"

# search symbols by keyword
[group: 'run']
search query kind="-" limit="10" dir=".":
    @uv run python scripts/search.py "{{query}}" "{{kind}}" "{{limit}}" "{{dir}}"

# show git changes mapped to symbols
[group: 'run']
show-changes scope="unstaged" dir=".":
    @uv run python scripts/show_changes.py "{{scope}}" "{{dir}}"

# ─── lint ─────────────────────────────────────────────────────────────

# check code style with ruff
[group: 'lint']
lint:
    uv run ruff check src/ tests/

# auto-fix lint issues
[group: 'lint']
lint-fix:
    uv run ruff check --fix src/ tests/

# format code with ruff
[group: 'lint']
fmt:
    uv run ruff format src/ tests/

# ─── util ─────────────────────────────────────────────────────────────

# remove python cache files
[group: 'util']
[unix]
clean:
    @find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    @find . -type f -name "*.pyc" -delete 2>/dev/null || true

# remove python cache files
[group: 'util']
[windows]
clean:
    @Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    @Get-ChildItem -Recurse -File -Filter *.pyc | Remove-Item -Force -ErrorAction SilentlyContinue
