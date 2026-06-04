"""
Unit tests for repomap.py — tree-sitter based repository map generator.
"""

import os
import sys
import tempfile
import shutil
import contextlib

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from repomap import (
    _parse_with_treesitter,
    _parse_vue,
    _parse_file,
    RepomapGenerator,
    get_repo_structure,
    MAX_FILE_SIZE,
    MAX_AST_DEPTH,
    MAX_DIR_DEPTH,
    MAX_OUTPUT_LINES,
)


class TestParseWithTreesitter:
    """Tests for _parse_with_treesitter across multiple languages."""

    def test_python_classes_and_functions(self):
        with _tmpfile(
            ".py",
            b"""
class Foo:
    def bar(self, x: int) -> str:
        pass

    def baz(self):
        pass

def top_func(a, b):
    return a + b

async def async_func():
    pass
""",
        ) as path:
            items = _parse_with_treesitter(path, "python")
            texts = "\n".join(items)
            assert "class Foo" in texts
            assert "def bar" in texts
            assert "def baz" in texts
            assert "def top_func" in texts
            assert "def async_func" in texts

    def test_javascript_functions_and_classes(self):
        with _tmpfile(
            ".js",
            b"""
class MyClass {
    constructor() {}
    method1(a, b) {}
}

function topFunc(a, b) { return a; }
const arrowFunc = (x) => x + 1;
export async function asyncFunc() {}
""",
        ) as path:
            items = _parse_with_treesitter(path, "javascript")
            texts = "\n".join(items)
            assert "class MyClass" in texts
            assert "def constructor" in texts
            assert "def method1" in texts
            assert "def topFunc" in texts or "function topFunc" in texts
            assert "arrowFunc" in texts
            assert "asyncFunc" in texts

    def test_typescript(self):
        with _tmpfile(
            ".ts",
            b"""
interface IService {
    run(): void;
}

class ServiceImpl {
    run(): void {}
    private helper(): string { return ""; }
}

function createService(): IService { return new ServiceImpl(); }
const factory = () => createService();
""",
        ) as path:
            items = _parse_with_treesitter(path, "typescript")
            texts = "\n".join(items)
            assert "class ServiceImpl" in texts
            assert "def createService" in texts or "createService" in texts

    def test_unknown_language_returns_empty(self):
        with _tmpfile(".xyz", b"some random content here") as path:
            items = _parse_with_treesitter(path, "nonexistent_lang_xyz")
            assert items == []

    def test_empty_file(self):
        with _tmpfile(".py", b"") as path:
            items = _parse_with_treesitter(path, "python")
            assert items == []

    def test_multiline_params_collapsed(self):
        with _tmpfile(
            ".py",
            b"""
def long_func(
    param_a: str,
    param_b: int,
    param_c: float = 0.0,
):
    pass
""",
        ) as path:
            items = _parse_with_treesitter(path, "python")
            # Should be single line
            for item in items:
                assert "\n" not in item


class TestParseVue:
    """Tests for Vue file parsing."""

    def test_vue_sections_detected(self):
        with _tmpfile(
            ".vue",
            b"""<template>
  <div>Hello</div>
</template>
<script>
export default { name: "Test" }
</script>
<style>
.test { color: red; }
</style>
""",
        ) as path:
            items = _parse_vue(path)
            texts = "\n".join(items)
            assert "<template>" in texts
            assert "<script>" in texts
            assert "<style>" in texts

    def test_vue_composition_api_functions(self):
        with _tmpfile(
            ".vue",
            b"""<script setup>
function toggle() { console.log(1) }
const handler = () => {}
</script>
<template><div>hi</div></template>
""",
        ) as path:
            items = _parse_vue(path)
            texts = "\n".join(items)
            assert "toggle" in texts

    def test_vue_script_lang_ts(self):
        with _tmpfile(
            ".vue",
            b"""<script lang="ts" setup>
function greet(name: string): string { return name }
</script>
<template><div>hi</div></template>
""",
        ) as path:
            items = _parse_vue(path)
            texts = "\n".join(items)
            assert "greet" in texts

    def test_vue_options_api_methods(self):
        with _tmpfile(
            ".vue",
            b"""<template><div>Hello</div></template>
<script>
export default {
  methods: {
    logout() { console.log("bye"); },
    handleClick() { return true; }
  }
}
</script>
""",
        ) as path:
            items = _parse_vue(path)
            texts = "\n".join(items)
            assert "def logout()" in texts
            assert "def handleClick()" in texts


class TestParseFile:
    """Tests for the _parse_file dispatcher."""

    def test_py_file(self):
        with _tmpfile(".py", b"def hello(): pass") as path:
            items = _parse_file(path)
            assert any("hello" in i for i in items)

    def test_unknown_extension(self):
        with _tmpfile(".docx", b"binary data") as path:
            items = _parse_file(path)
            assert items == []

    def test_vue_file(self):
        with _tmpfile(".vue", b"<template><div/></template>") as path:
            items = _parse_file(path)
            assert any("template" in i for i in items)


class TestRepomapGenerator:
    """Tests for the full RepomapGenerator output."""

    def test_generates_tree(self):
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "subdir"))
            with open(os.path.join(tmpdir, "main.py"), "w") as f:
                f.write("class App:\n    def run(self): pass\n")
            with open(os.path.join(tmpdir, "subdir", "utils.py"), "w") as f:
                f.write("def helper(): pass\n")

            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)

            assert "subdir/" in result
            assert "main.py" in result
            assert "class App" in result
            assert "def run" in result
            assert "utils.py" in result
            assert "def helper" in result
        finally:
            shutil.rmtree(tmpdir)

    def test_ignores_pycache(self):
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "__pycache__"))
            with open(os.path.join(tmpdir, "__pycache__", "cached.pyc"), "w") as f:
                f.write("junk")
            with open(os.path.join(tmpdir, "app.py"), "w") as f:
                f.write("def main(): pass\n")

            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)

            assert "__pycache__" not in result
            assert "app.py" in result
        finally:
            shutil.rmtree(tmpdir)

    def test_invalid_dir(self):
        gen = RepomapGenerator()
        result = gen.get_map("/nonexistent/path/12345")
        assert "Error" in result

    def test_empty_project(self):
        tmpdir = tempfile.mkdtemp()
        try:
            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)
            assert result == "(empty project)"
        finally:
            shutil.rmtree(tmpdir)


class TestSecurity:
    """Tests for path traversal, symlinks, and file size limits."""

    def test_symlinks_skipped(self):
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "real.py"), "w") as f:
                f.write("def real(): pass\n")
            link_path = os.path.join(tmpdir, "link_to_real.py")
            try:
                os.symlink(os.path.join(tmpdir, "real.py"), link_path)
            except (OSError, NotImplementedError):
                print("  SKIP  (symlinks not supported on this OS)")
                return

            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)

            assert "real.py" in result
            assert "link_to_real.py" not in result
        finally:
            shutil.rmtree(tmpdir)

    def test_symlink_dir_skipped(self):
        tmpdir = tempfile.mkdtemp()
        try:
            real_dir = os.path.join(tmpdir, "realdir")
            os.makedirs(real_dir)
            with open(os.path.join(real_dir, "mod.py"), "w") as f:
                f.write("def foo(): pass\n")
            link_dir = os.path.join(tmpdir, "linkeddir")
            try:
                os.symlink(real_dir, link_dir)
            except (OSError, NotImplementedError):
                print("  SKIP  (symlinks not supported on this OS)")
                return

            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)

            assert "realdir/" in result
            assert "linkeddir" not in result
        finally:
            shutil.rmtree(tmpdir)

    def test_large_file_skipped(self):
        with _tmpfile(".py", b"x = 1\n" * (MAX_FILE_SIZE // 4)) as path:
            items = _parse_with_treesitter(path, "python")
            assert items == []

    def test_permission_error_skipped(self):
        if sys.platform == "win32":
            print("  SKIP  (Unix permissions don't apply on Windows)")
            return
        tmpdir = tempfile.mkdtemp()
        try:
            restricted = os.path.join(tmpdir, "noaccess")
            os.makedirs(restricted)
            with open(os.path.join(restricted, "secret.py"), "w") as f:
                f.write("def secret(): pass\n")
            with open(os.path.join(tmpdir, "public.py"), "w") as f:
                f.write("def public(): pass\n")
            os.chmod(restricted, 0o000)

            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)

            assert "public.py" in result
            assert "secret.py" not in result
        finally:
            os.chmod(os.path.join(tmpdir, "noaccess"), 0o755)
            shutil.rmtree(tmpdir)

    def test_path_traversal_blocked(self):
        # Use system temp dir — guaranteed to be outside project cwd
        outside_path = tempfile.gettempdir()
        result = get_repo_structure.invoke({"root_path": outside_path})
        assert "outside" in result


class TestBoundariesAndLimits:
    """Tests for boundary conditions that catch specific mutations."""

    def test_file_at_exact_max_size_is_parsed(self):
        """Catches mutation: changing > to >= in MAX_FILE_SIZE check."""
        with _tmpfile(".py", b"") as path:
            # Overwrite with exactly MAX_FILE_SIZE bytes
            with open(path, "wb") as f:
                content = b"def boundary(): pass\n"
                f.write(content + b" " * (MAX_FILE_SIZE - len(content)))
            assert os.path.getsize(path) == MAX_FILE_SIZE
            items = _parse_with_treesitter(path, "python")
            assert any("boundary" in i for i in items)

    def test_file_over_max_size_is_skipped(self):
        """Catches mutation: removing the MAX_FILE_SIZE check entirely."""
        with _tmpfile(".py", b"") as path:
            with open(path, "wb") as f:
                f.write(b"def toobig(): pass\n" + b" " * MAX_FILE_SIZE)
            assert os.path.getsize(path) > MAX_FILE_SIZE
            items = _parse_with_treesitter(path, "python")
            assert items == []

    def test_ast_depth_limit(self):
        """Catches mutation: removing MAX_AST_DEPTH check."""
        # Build 25 levels of nested classes (exceeds MAX_AST_DEPTH=20)
        lines = []
        for i in range(25):
            lines.append("    " * i + f"class C{i}:")
        lines.append("    " * 25 + "def deepfunc(): pass")
        code = "\n".join(lines).encode()
        with _tmpfile(".py", code) as path:
            items = _parse_with_treesitter(path, "python")
            # Should find exactly MAX_AST_DEPTH classes (0..19), not all 25
            class_items = [i for i in items if "class C" in i]
            assert len(class_items) == MAX_AST_DEPTH

    def test_output_truncation(self):
        """Catches mutation: removing MAX_OUTPUT_LINES truncation."""
        tmpdir = tempfile.mkdtemp()
        try:
            # Create enough files to exceed MAX_OUTPUT_LINES
            # Each file generates ~2 lines (filename + 1 definition)
            n_files = MAX_OUTPUT_LINES // 2 + 100
            for i in range(n_files):
                with open(os.path.join(tmpdir, f"f{i:05d}.py"), "w") as f:
                    f.write(f"def func_{i}(): pass\n")
            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)
            result_lines = result.split("\n")
            assert len(result_lines) <= MAX_OUTPUT_LINES + 1  # +1 for truncation msg
            assert "truncated" in result_lines[-1]
        finally:
            shutil.rmtree(tmpdir)

    def test_dir_depth_limit(self):
        """Catches mutation: removing MAX_DIR_DEPTH check."""
        tmpdir = tempfile.mkdtemp()
        try:
            # Create nesting deeper than MAX_DIR_DEPTH
            depth = MAX_DIR_DEPTH + 5
            current = tmpdir
            for i in range(depth):
                current = os.path.join(current, f"d{i}")
                os.makedirs(current)
            with open(os.path.join(current, "deep.py"), "w") as f:
                f.write("def deep(): pass\n")

            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)
            # The deepest file should NOT appear (cut off at MAX_DIR_DEPTH)
            assert "deep.py" not in result
        finally:
            shutil.rmtree(tmpdir)

    def test_get_repo_structure_with_cwd(self):
        """Catches mutation: removing 'resolved != cwd' in traversal check."""
        cwd = os.getcwd()
        result = get_repo_structure.invoke({"root_path": cwd})
        assert "Error" not in result

    def test_path_traversal_sep_sensitivity(self):
        """Catches mutation: changing os.sep to hardcoded '/' in traversal check."""
        # Construct a path that shares a prefix with cwd but is outside it.
        # E.g., if cwd is /home/user/project, test /home/user/project-evil
        cwd = os.path.realpath(os.getcwd())
        evil_path = cwd + "-evil"
        result = get_repo_structure.invoke({"root_path": evil_path})
        assert "outside" in result or "Error" in result

    def test_get_repo_structure_default_cwd(self):
        """Test the most common invocation: root_path=None (defaults to cwd)."""
        result = get_repo_structure.invoke({})
        assert "Error" not in result

    def test_env_file_excluded(self):
        """Sensitive .env files should not appear in repomap output."""
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, ".env"), "w") as f:
                f.write("SECRET_KEY=abc123\n")
            with open(os.path.join(tmpdir, ".env.local"), "w") as f:
                f.write("DB_PASSWORD=secret\n")
            with open(os.path.join(tmpdir, "app.py"), "w") as f:
                f.write("def main(): pass\n")

            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)

            assert ".env" not in result
            assert "app.py" in result
        finally:
            shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _tmpfile(ext: str, content: bytes):
    """Create a temporary file with the given extension and content."""
    fd, path = tempfile.mkstemp(suffix=ext)
    try:
        os.write(fd, content)
    finally:
        os.close(fd)
    try:
        yield path
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    passed = 0
    failed = 0
    errors = []

    for cls in [
        TestParseWithTreesitter,
        TestParseVue,
        TestParseFile,
        TestRepomapGenerator,
        TestSecurity,
        TestBoundariesAndLimits,
    ]:
        instance = cls()
        for name in sorted(dir(instance)):
            if not name.startswith("test_"):
                continue
            method = getattr(instance, name)
            try:
                method()
                passed += 1
                print(f"  PASS  {cls.__name__}.{name}")
            except Exception as e:
                failed += 1
                errors.append((f"{cls.__name__}.{name}", e))
                print(f"  FAIL  {cls.__name__}.{name}: {e}")

    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed")
    if errors:
        print("\nFailures:")
        for name, err in errors:
            print(f"  - {name}: {err}")
    sys.exit(1 if failed else 0)
