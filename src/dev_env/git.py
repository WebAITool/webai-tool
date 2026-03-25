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

**/.env
**/.env.*
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
    if not gitignore.exists():
        with gitignore.open("+a") as file:
            file.write(_GITIGNORE)

    if commit_branch in _REPO.branches:
        _DEV_BRANCH = _REPO.branches[commit_branch]
    else:
        has_commits = True
        try:
            next(_REPO.iter_commits())
        except StopIteration:
            has_commits = False
        if not has_commits:
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

    res = []
    for diff in _INDEX.diff():
        if diff.deleted_file:
            res.append(diff.a_path)
        elif diff.renamed_file:
            if diff.a_path is not None and diff.b_path is not None:
                res.append(diff.a_path + ' -> ' + diff.b_path)
        else:
            res.append(diff.b_path)

    res += _REPO.untracked_files

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

    try:
        _INDEX.add(files)
    except OSError as e:
        raise FileNotFoundError(e.args)
    _INDEX.commit(message, author=_AGENT_ACTOR, committer=_AGENT_ACTOR)

    logging.debug(f'git.commit(files={str(files)}, message="{message}"')
