import os, tempfile
from graph.import_resolver import extract_imports, build_suffix_index, resolve_import

def _write_tmp(suffix: str, content: str) -> str:
    f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode="w")
    f.write(content)
    f.close()
    return f.name

def test_python_from_import():
    path = _write_tmp(".py", "from auth import login\n")
    try:
        tags = extract_imports(path, "python")
        names = [t.imported_name for t in tags]
        assert "login" in names
        sources = [t.source_path for t in tags]
        assert any("auth" in s for s in sources)
    finally:
        os.unlink(path)

def test_python_multi_import():
    path = _write_tmp(".py", "from auth import login, logout\n")
    try:
        tags = extract_imports(path, "python")
        names = {t.imported_name for t in tags}
        assert "login" in names
        assert "logout" in names
    finally:
        os.unlink(path)

def test_js_named_import():
    path = _write_tmp(".js", "import { login } from './auth';\n")
    try:
        tags = extract_imports(path, "javascript")
        names = [t.imported_name for t in tags]
        assert "login" in names
    finally:
        os.unlink(path)

def test_js_default_import():
    path = _write_tmp(".js", "import UserService from './services/user';\n")
    try:
        tags = extract_imports(path, "javascript")
        names = [t.imported_name for t in tags]
        assert "UserService" in names
    finally:
        os.unlink(path)

def test_build_suffix_index():
    files = ["src/auth.py", "src/api/auth.py", "lib/utils.py"]
    idx = build_suffix_index(files)
    assert "auth" in idx
    assert "utils" in idx
    assert len(idx["auth"]) == 2

def test_resolve_exact():
    idx = build_suffix_index(["src/auth.py", "src/utils.py"])
    result = resolve_import("auth", "src/api/handler.py", idx)
    assert result == "src/auth.py"

def test_resolve_ambiguous_picks_closest():
    # src/api/auth.py is closer to src/api/handler.py than src/auth.py
    idx = build_suffix_index(["src/auth.py", "src/api/auth.py"])
    result = resolve_import("auth", "src/api/handler.py", idx)
    assert result == "src/api/auth.py"

def test_resolve_stdlib_returns_none():
    idx = build_suffix_index(["src/auth.py"])
    result = resolve_import("os", "src/main.py", idx)
    assert result is None

def test_resolve_unknown_returns_none():
    idx = build_suffix_index(["src/auth.py"])
    result = resolve_import("nonexistent_module", "src/main.py", idx)
    assert result is None
