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
