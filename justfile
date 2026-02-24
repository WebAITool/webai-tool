# WebAI Toolkit — development commands
# usage: just <recipe>    (install just: https://github.com/casey/just)

set dotenv-load
set windows-shell := ["pwsh", "-NoProfile", "-Command"]

# list available recipes
[group: 'help']
default:
    @just --list --list-submodules

# ─── setup ────────────────────────────────────────────────────────────

# install all project dependencies
[group: 'setup']
install:
    uv sync

# copy .env.example → .env (won't overwrite existing)
[group: 'setup']
[unix]
env:
    @if [ ! -f .env ]; then cp .env.example .env && echo "created .env from .env.example"; else echo ".env already exists"; fi

[group: 'setup']
[windows]
env:
    if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "created .env from .env.example" } else { Write-Host ".env already exists" }

# full first-time setup
[group: 'setup']
setup: env install

# ─── test ─────────────────────────────────────────────────────────────

# run unit tests (repomap, parsers, security)
[group: 'test']
test-unit:
    uv run python tests/unit/test_repomap.py

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

# run the agent with a goal and spec
# usage: just run "build a landing page" "use vue 3, tailwind"
[group: 'run']
[unix]
run goal spec prjdir=".":
    AGENT_GOAL="{{goal}}" AGENT_SPEC="{{spec}}" AGENT_PRJDIR="{{prjdir}}" uv run python -c "import sys, os; sys.path.insert(0,'src'); from lg_agent import run_agent; run_agent(os.environ['AGENT_GOAL'], os.environ['AGENT_SPEC'], prjdir=os.environ['AGENT_PRJDIR'])"

[group: 'run']
[windows]
run goal spec prjdir=".":
    $env:AGENT_GOAL="{{goal}}"; $env:AGENT_SPEC="{{spec}}"; $env:AGENT_PRJDIR="{{prjdir}}"; uv run python -c "import sys, os; sys.path.insert(0,'src'); from lg_agent import run_agent; run_agent(os.environ['AGENT_GOAL'], os.environ['AGENT_SPEC'], prjdir=os.environ['AGENT_PRJDIR'])"

# generate repomap for a directory (defaults to current dir)
[group: 'run']
[unix]
repomap dir=".":
    REPOMAP_DIR="{{dir}}" uv run python -c "import sys, os; sys.path.insert(0,'src'); from repomap import get_repo_structure; print(get_repo_structure.invoke({'root_path': os.environ['REPOMAP_DIR']}))"

[group: 'run']
[windows]
repomap dir=".":
    $env:REPOMAP_DIR="{{dir}}"; uv run python -c "import sys, os; sys.path.insert(0,'src'); from repomap import get_repo_structure; print(get_repo_structure.invoke({'root_path': os.environ['REPOMAP_DIR']}))"

# alias for repomap
alias tree := repomap

# ─── lint ─────────────────────────────────────────────────────────────

# check code style with ruff (does not modify files)
[group: 'lint']
lint:
    uvx ruff check src/ tests/

# auto-fix lint issues
[group: 'lint']
lint-fix:
    uvx ruff check --fix src/ tests/

# format code with ruff
[group: 'lint']
fmt:
    uvx ruff format src/ tests/

# ─── util ─────────────────────────────────────────────────────────────

# remove python cache files
[group: 'util']
[unix]
clean:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true

[group: 'util']
[windows]
clean:
    Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -File -Filter *.pyc | Remove-Item -Force -ErrorAction SilentlyContinue
