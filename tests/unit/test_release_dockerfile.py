from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_docker_dependency_layer_does_not_depend_on_readme_content():
    lines = (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
    uv_sync_index = next(
        index for index, line in enumerate(lines) if "uv sync --frozen" in line
    )
    before_uv_sync = "\n".join(lines[:uv_sync_index])

    assert "COPY pyproject.toml uv.lock ./" in before_uv_sync
    assert "RUN touch ./README.md" in before_uv_sync
    assert "README.md" not in before_uv_sync.replace("RUN touch ./README.md", "")

    readme_copy_index = next(
        index
        for index, line in enumerate(lines)
        if line.strip().startswith("COPY ") and "README.md" in line
    )
    assert readme_copy_index > uv_sync_index


def test_docker_entrypoint_uses_release_cli_with_src_pythonpath():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "ENV PYTHONPATH=/app/src" in dockerfile
    assert 'ENTRYPOINT ["/app/.venv/bin/python", "/app/src/main.py"]' in dockerfile
