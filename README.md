# WebAI Tool

WebAI Tool is a spec-driven agent for generating and modifying web projects with a Python backend and a Vue/JavaScript frontend. It can implement requested features from existing project documentation, or analyze a reference project to generate documentation first and then implement changes through an LLM-driven LangGraph workflow.

The current release focuses on a command-line workflow for demonstrations and controlled experiments. The agent can execute generated Python code, run backend checks, inspect frontend output, and optionally commit generated changes inside the target project.

## Capabilities

- Generate or modify a project by implementing features described in project documentation and task specifications.
- Analyze a reference project, generate a specification from it, then implement requested changes in the target project.
- Build a repository map for Python, JavaScript, TypeScript, TSX, and Vue files with tree-sitter queries.
- Run Pyright checks for generated backend code.
- Run frontend verification with Playwright screenshots and LLM vision feedback when frontend files change.
- Optionally create git commits in the generated project when `--enable-commits` is explicitly enabled.

## Security Warning

WebAI Tool works with live project files and can run agent-generated actions. Review generated changes and commands before trusting the result, especially when working with untrusted repositories or task specifications.

Use an isolated environment for untrusted projects.

See the GitHub Wiki page [Security and Isolation](https://github.com/WebAITool/webai-tool/wiki/Security-and-Isolation) for the threat model and mitigation plan.

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/) for local dependency management
- `tree` command available on PATH for reference-project documentation generation
- Node.js and npm for generated frontend projects
- Playwright browsers for frontend verification
- API key for an OpenAI-compatible provider

## Installation

```bash
git clone https://github.com/WebAITool/webai-tool.git
cd webai-tool
uv sync
```

Install Playwright browsers if frontend verification is needed:

```bash
uv run python -m playwright install chromium
```

## Configuration

WebAI Tool uses an OpenAI-compatible chat completions provider. Copy `.env.example` to a local `.env` file in the repository root and add the provider settings. All four variables are required; WebAI Tool does not infer a provider from the API key.

```bash
cp .env.example .env
```

Polza.ai-style example:

```env
API_KEY=your-api-key
LLM_API_BASE_URL=https://api.polza.ai/api/v1
LLM_MODEL=z-ai/glm-5.1
FRONTEND_VISION_MODEL=qwen/qwen3-vl-8b-thinking
```

OpenRouter example:

```env
API_KEY=your-openrouter-key
LLM_API_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/owl-alpha
FRONTEND_VISION_MODEL=qwen/qwen3-vl-8b-instruct
```

`openrouter/owl-alpha` is useful for free agent smoke tests, but it is a
text-only OpenRouter model and should not be used for `FRONTEND_VISION_MODEL`.
For frontend screenshot review, choose a model whose OpenRouter metadata lists
`image` in `input_modalities`. `qwen/qwen3-vl-8b-instruct` is a low-cost
Qwen vision-language example for this slot. Check the
[OpenRouter Models](https://openrouter.ai/models) page and the
[OpenRouter multimodal documentation](https://openrouter.ai/docs/guides/overview/multimodal/overview)
before pinning a release configuration.

Configuration variables:

- `API_KEY`: API key from your OpenAI-compatible provider account.
- `LLM_API_BASE_URL`: provider API base URL.
- `LLM_MODEL`: main model used by the agent workflow.
- `FRONTEND_VISION_MODEL`: vision-capable model used for screenshot-based frontend review.

Keep `.env` untracked. The file is ignored by `.gitignore` and excluded from the Docker build context.

## CLI Usage

The main entrypoint is `src/main.py`:

```bash
uv run python src/main.py --prjdir <output-project-dir> (--docpath <doc-file> | --refprjpath <reference-project-dir>) [--enable-commits] [--commit-branch <branch>] [--interactive] <taskspec-file>
```

Arguments:

- `--prjdir`: directory where WebAI Tool creates or modifies the target project.
- `--docpath`: path to an existing project documentation/specification file.
- `--refprjpath`: path to a reference project. WebAI Tool generates documentation from it before implementation.
- `taskspec`: path to the task specification file that describes what the agent should build or change.
- `--enable-commits`: optional. Allows the agent to commit generated changes in the target project.
- `--commit-branch`: branch used for agent commits when commits are enabled. Defaults to `dev`.
- `--interactive`: optional. Prompts for user feedback after the agent confirms completion. Non-interactive is the default and is recommended for Docker and CI runs.

`--docpath` and `--refprjpath` are mutually exclusive.

## Quick CLI Example

Create input files:

```bash
mkdir -p demo-workspace
cat > demo-workspace/project-doc.md <<'EOF'
# Project

Create a small web project with a Python backend and a Vue frontend.
The backend should expose a list of public events.
The frontend should show those events in a simple page.
EOF

cat > demo-workspace/task.txt <<'EOF'
Implement the backend event-list endpoint, the Vue event-list page, and README instructions for running the generated project.
EOF
```

Run WebAI Tool:

```bash
uv run python src/main.py \
  --prjdir demo-workspace \
  --docpath demo-workspace/project-doc.md \
  demo-workspace/task.txt
```

Expected result:

- Generated project files appear in `demo-workspace/`.
- Runtime logs are written under `.logs/`.
- If frontend files are generated, frontend verification may create screenshots in the generated project.

The official release Tutorial Benchmark is defined in the GitHub Wiki and uses a small frontend/backend events betting application scenario.

## Docker Release

During local release validation, build the image from this checkout:

```bash
docker build -t webai-tool:release .
```

When a project release publishes a prebuilt image through Docker Hub, GitHub
Container Registry, or a GitHub release asset, use that published image tag
instead of rebuilding locally.

If Docker build containers cannot reach Debian or Playwright download hosts
through the default bridge network, build with host networking:

```bash
docker build --network=host -t webai-tool:release .
```

Run the release CLI container:

```bash
docker run --rm \
  --env-file .env \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD/demo-workspace:/workspace" \
  webai-tool:release \
  --prjdir /workspace \
  --docpath /workspace/project-doc.md \
  /workspace/task.txt
```

The image reads `API_KEY`, `LLM_API_BASE_URL`, `LLM_MODEL`, and `FRONTEND_VISION_MODEL` from the local `.env` file. `.env` must stay untracked and is excluded from the Docker build context. The image runs as a non-root user. On Linux, pass `--user "$(id -u):$(id -g)"` so files written under the mounted `/workspace` remain writable by the host user.

The default Docker release mode should mount only the target workspace. Do not
mount the Docker socket, SSH agent, cloud credentials, full home directory, or
other broad host paths unless you intentionally leave the default isolation
boundary.

If the container can resolve provider hostnames but cannot open outbound TCP connections, rerun with host networking:

```bash
docker run --rm \
  --network=host \
  --env-file .env \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD/demo-workspace:/workspace" \
  webai-tool:release \
  --prjdir /workspace \
  --docpath /workspace/project-doc.md \
  /workspace/task.txt
```

Host networking is a troubleshooting option for Docker network environments where the default bridge has no outbound provider access.

Interactive feedback is opt-in. Use an interactive terminal only when you intentionally want post-completion feedback prompts:

```bash
docker run --rm -it \
  --env-file .env \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD/demo-workspace:/workspace" \
  webai-tool:release \
  --interactive \
  --prjdir /workspace \
  --docpath /workspace/project-doc.md \
  /workspace/task.txt
```

See the GitHub Wiki page [Deployment](https://github.com/WebAITool/webai-tool/wiki/Deployment) for Docker deployment details.

## Development Checks

Run unit tests:

```bash
uv run python -m pytest tests/unit/ -v
```

Run Ruff:

```bash
uv run ruff check src/
```

## Release Documentation

Release documentation is maintained in the GitHub Wiki:

- [Release Plan](https://github.com/WebAITool/webai-tool/wiki/Release-Plan)
- [Deployment](https://github.com/WebAITool/webai-tool/wiki/Deployment)
- [Security and Isolation](https://github.com/WebAITool/webai-tool/wiki/Security-and-Isolation)
- [Tutorial Benchmark](https://github.com/WebAITool/webai-tool/wiki/Tutorial-Benchmark)
