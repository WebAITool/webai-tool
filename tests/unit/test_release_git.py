from dev_env import git as git_module


def _reset_git_module(monkeypatch):
    monkeypatch.setattr(git_module, "_is_initialized", False)


def test_commit_stages_deleted_files(tmp_path, monkeypatch):
    _reset_git_module(monkeypatch)
    git_module.init_git(tmp_path, "dev")

    tracked_file = tmp_path / "tracked.txt"
    tracked_file.write_text("content\n", encoding="utf-8")
    git_module.commit(["tracked.txt"], "add tracked file")

    tracked_file.unlink()
    dirty_files = git_module.get_dirty_files()

    assert "tracked.txt" in dirty_files

    git_module.commit(dirty_files, "delete tracked file")

    assert not git_module._REPO.is_dirty(untracked_files=True)


def test_generated_gitignore_excludes_env_profiles(tmp_path, monkeypatch):
    _reset_git_module(monkeypatch)
    git_module.init_git(tmp_path, "dev")

    (tmp_path / ".envrc").write_text("API_KEY=secret\n", encoding="utf-8")
    (tmp_path / ".env-prod").write_text("API_KEY=secret\n", encoding="utf-8")
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    (nested_dir / ".envfoo").write_text("API_KEY=secret\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("API_KEY=placeholder\n", encoding="utf-8")

    dirty_files = git_module.get_dirty_files()

    assert ".envrc" not in dirty_files
    assert ".env-prod" not in dirty_files
    assert "nested/.envfoo" not in dirty_files
    assert ".env.example" in dirty_files


def test_existing_gitignore_gets_env_profile_rules(tmp_path, monkeypatch):
    _reset_git_module(monkeypatch)
    (tmp_path / ".gitignore").write_text(
        "custom.log\n!**/.env.example\n",
        encoding="utf-8",
    )

    git_module.init_git(tmp_path, "dev")

    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    env_block = (
        "# WebAITool sensitive env files\n"
        "**/.env*\n"
        "!**/.env.example\n"
        "**/.env.example/**\n"
    )
    assert env_block in gitignore
    assert gitignore.rfind("**/.env*") < gitignore.rfind("!**/.env.example")
    assert gitignore.rfind("!**/.env.example") < gitignore.rfind("**/.env.example/**")


def test_dirty_files_and_commit_filter_sensitive_env_paths(tmp_path, monkeypatch):
    _reset_git_module(monkeypatch)
    (tmp_path / ".gitignore").write_text("custom.log\n", encoding="utf-8")
    git_module.init_git(tmp_path, "dev")

    (tmp_path / ".gitignore").write_text("custom.log\n", encoding="utf-8")
    (tmp_path / ".envrc").write_text("API_KEY=secret\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("API_KEY=placeholder\n", encoding="utf-8")
    (tmp_path / "RESULT.txt").write_text("OK\n", encoding="utf-8")

    dirty_files = git_module.get_dirty_files()

    assert ".envrc" not in dirty_files
    assert ".env.example" in dirty_files
    assert "RESULT.txt" in dirty_files

    before_commit = git_module._REPO.head.commit.hexsha
    git_module.commit([".envrc"], "skip sensitive file")
    assert git_module._REPO.head.commit.hexsha == before_commit


def test_commit_does_not_include_pre_staged_sensitive_env_file(tmp_path, monkeypatch):
    _reset_git_module(monkeypatch)
    (tmp_path / ".gitignore").write_text("custom.log\n", encoding="utf-8")
    git_module.init_git(tmp_path, "dev")

    (tmp_path / ".gitignore").write_text("custom.log\n", encoding="utf-8")
    (tmp_path / ".env.polza").write_text("API_KEY=secret\n", encoding="utf-8")
    (tmp_path / "RESULT.txt").write_text("OK\n", encoding="utf-8")
    git_module._REPO.git.add("-f", ".env.polza")

    git_module.commit(["RESULT.txt"], "add result")

    committed_files = git_module._REPO.git.show(
        "--pretty=",
        "--name-only",
        "HEAD",
    ).splitlines()
    assert "RESULT.txt" in committed_files
    assert ".env.polza" not in committed_files


def test_commit_does_not_include_hidden_staged_files(tmp_path, monkeypatch):
    _reset_git_module(monkeypatch)
    git_module.init_git(tmp_path, "dev")

    (tmp_path / "STAGED.txt").write_text("hidden\n", encoding="utf-8")
    (tmp_path / "RESULT.txt").write_text("OK\n", encoding="utf-8")
    git_module._REPO.git.add("STAGED.txt")

    git_module.commit(["RESULT.txt"], "add result")

    committed_files = git_module._REPO.git.show(
        "--pretty=",
        "--name-only",
        "HEAD",
    ).splitlines()
    assert "RESULT.txt" in committed_files
    assert "STAGED.txt" not in committed_files


def test_env_example_directory_children_are_sensitive(tmp_path, monkeypatch):
    _reset_git_module(monkeypatch)
    git_module.init_git(tmp_path, "dev")

    env_example_dir = tmp_path / ".env.example"
    env_example_dir.mkdir()
    (env_example_dir / "secret.txt").write_text("API_KEY=secret\n", encoding="utf-8")
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    (nested_dir / ".env.example").write_text(
        "API_KEY=placeholder\n",
        encoding="utf-8",
    )

    dirty_files = git_module.get_dirty_files()

    assert "nested/.env.example" in dirty_files
    assert ".env.example/secret.txt" not in dirty_files
