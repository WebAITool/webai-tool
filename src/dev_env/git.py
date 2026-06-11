import logging
from pathlib import Path
import git


class InvalidStateException(Exception):
    pass


_REPO: git.Repo
_AGENT_ACTOR = git.Actor('WebAITool', 'webai@example.com')
_DEV_BRANCH: git.Head
_INDEX: git.IndexFile
_is_initialized = False
_GITIGNORE = """
# WebAITool gitignore
**/node_modules
**/dist
**/.vite
**/.cache
**/.eslintcache

**/.env*
!**/.env.example
**/.env.example/**
**/.DS_Store
**/.Thumbs.db
**/.idea
**/.vscode

**/.venv
**/__pycache__/
**/*.pyc

**/logs
**/*.log
**/npm-debug.log*
**/yarn-debug.log*
**/yarn-error.log*
# end
"""


def is_sensitive_env_path(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    for index, part in enumerate(parts):
        if not part.startswith(".env"):
            continue
        if part == ".env.example" and index == len(parts) - 1:
            continue
        return True
    return False


def _unstage_sensitive_env_paths() -> None:
    try:
        staged = _REPO.git.diff("--cached", "--name-only").splitlines()
    except git.GitCommandError:
        return
    sensitive = [path for path in staged if is_sensitive_env_path(path)]
    if sensitive:
        try:
            _REPO.git.reset("HEAD", "--", *sensitive)
        except git.GitCommandError:
            _REPO.index.remove(sensitive, cached=True, r=True)


def _unstage_paths_not_in(allowed_paths: set[str]) -> None:
    try:
        staged = _REPO.git.diff("--cached", "--name-only").splitlines()
    except git.GitCommandError:
        return
    extra = [path for path in staged if path not in allowed_paths]
    if extra:
        _REPO.git.reset("HEAD", "--", *extra)


def _ensure_gitignore_rules(gitignore: Path) -> None:
    if not gitignore.exists():
        gitignore.write_text(_GITIGNORE, encoding="utf-8")
        return

    content = gitignore.read_text(encoding="utf-8")
    block = (
        "# WebAITool sensitive env files\n"
        "**/.env*\n"
        "!**/.env.example\n"
        "**/.env.example/**\n"
    )
    if block not in content:
        with gitignore.open("a", encoding="utf-8") as file:
            if content and not content.endswith("\n"):
                file.write("\n")
            if content:
                file.write("\n")
            file.write(block)


def init_git(prjdir: Path, commit_branch: str) -> None:
    global _is_initialized
    if _is_initialized:
        raise InvalidStateException()

    global _REPO, _AGENT_ACTOR, _DEV_BRANCH, _INDEX
    if (prjdir / '.git').exists():
        _REPO = git.Repo(str(prjdir))
    else:
        _REPO = git.Repo.init(str(prjdir))

    _INDEX = _REPO.index

    gitignore = (prjdir / '.gitignore')
    _ensure_gitignore_rules(gitignore)

    if commit_branch in _REPO.branches:
        _DEV_BRANCH = _REPO.branches[commit_branch]
    else:
        has_commits = True
        try:
            next(_REPO.iter_commits())
        except (StopIteration, ValueError):
            has_commits = False
        if not has_commits:
            _INDEX.add([str(gitignore)])
            _INDEX.commit('init', author=_AGENT_ACTOR, committer=_AGENT_ACTOR)
        _DEV_BRANCH = _REPO.create_head(commit_branch)

    _DEV_BRANCH.checkout()
    _is_initialized = True

#   def create_branch( branch_name: str) -> None:
#       if _REPO.active_branch != _DEV_BRANCH:
#           raise InvalidStateException("Current branch isn't dev")

#       _REPO.create_head(branch_name).checkout()

#   def switch_branch_to_dev( -> None:
#       _DEV_BRANCH.checkout()


def get_dirty_files() -> list[str]:
    if not _is_initialized:
        raise InvalidStateException()

    _unstage_sensitive_env_paths()

    res = []
    for diff in _REPO.index.diff(None):
        if diff.deleted_file:
            if not is_sensitive_env_path(diff.a_path):
                res.append(diff.a_path)
        elif diff.renamed_file:
            if diff.a_path is not None and diff.b_path is not None:
                if not (
                    is_sensitive_env_path(diff.a_path)
                    or is_sensitive_env_path(diff.b_path)
                ):
                    res.append(diff.a_path + ' -> ' + diff.b_path)
        else:
            if not is_sensitive_env_path(diff.b_path):
                res.append(diff.b_path)

    res += [path for path in _REPO.untracked_files if not is_sensitive_env_path(path)]

    logging.debug('git.get_dirty_files() -> ' + str(res))
    return res


def commit(files: list[str], message: str) -> None:
    """
    Commits files with message

    Raises:
        FileNotFoundError if files contains invalid path
    """
    if not _is_initialized:
        raise InvalidStateException()

    _unstage_sensitive_env_paths()

    paths = []
    for file in files:
        if " -> " in file:
            old_path, new_path = file.split(" -> ", 1)
            if not (is_sensitive_env_path(old_path) or is_sensitive_env_path(new_path)):
                paths.extend([old_path, new_path])
        else:
            if not is_sensitive_env_path(file):
                paths.append(file)

    if not paths:
        logging.debug("git.commit skipped: no non-sensitive files to commit")
        return

    try:
        if paths:
            _REPO.git.add("-A", "--", *paths)
            _unstage_sensitive_env_paths()
            _unstage_paths_not_in(set(paths))
    except (OSError, git.GitCommandError) as e:
        raise FileNotFoundError(e.args)
    _REPO.index.commit(message, author=_AGENT_ACTOR, committer=_AGENT_ACTOR)

    logging.debug(f'git.commit(files={str(files)}, message="{message}"')
