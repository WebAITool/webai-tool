"""
Unit tests for repo_map.py — tree-sitter based repository map generator.
"""

import os
import sys
import tempfile
import shutil
import contextlib

from repomap import (
    _parse_vue,
    _parse_file,
    _extract_tags,
    RepomapGenerator,
    get_repo_structure,
    MAX_FILE_SIZE,
    MAX_DIR_DEPTH,
    MAX_OUTPUT_LINES,
)


class TestParseWithTreesitter:
    """Tests for tag extraction across multiple languages."""

    def test_python_classes_and_functions(self):
        code = b"""
class Foo:
    def bar(self, x: int) -> str:
        pass
    def baz(self):
        pass

def top_func(a, b):
    return a + b

async def async_func():
    pass
"""
        tags = _extract_tags_from_source(code, "python")
        defs = [t.name for t in tags if t.kind == "def"]
        assert "Foo" in defs
        assert "bar" in defs
        assert "baz" in defs
        assert "top_func" in defs
        assert "async_func" in defs

    def test_javascript_functions_and_classes(self):
        code = b"""
class MyClass {
    constructor() {}
    method1(a, b) {}
}
function topFunc(a, b) { return a; }
const arrowFunc = (x) => x + 1;
"""
        tags = _extract_tags_from_source(code, "javascript")
        defs = [t.name for t in tags if t.kind == "def"]
        assert "MyClass" in defs
        assert "constructor" in defs
        assert "method1" in defs
        assert "topFunc" in defs
        assert "arrowFunc" in defs

    def test_typescript(self):
        code = b"""
class ServiceImpl {
    run(): void {}
}
function createService() { return new ServiceImpl(); }
const factory = () => createService();
"""
        tags = _extract_tags_from_source(code, "typescript")
        defs = [t.name for t in tags if t.kind == "def"]
        assert "ServiceImpl" in defs
        assert "createService" in defs
        assert "factory" in defs

    def test_unknown_language_returns_empty(self):
        with _tmpfile(".xyz", b"some random content here") as path:
            tags = _extract_tags(path, "nonexistent_lang_xyz")
            assert tags == []

    def test_empty_file(self):
        tags = _extract_tags_from_source(b"", "python")
        assert tags == []


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
            tags = _parse_vue(path)
            names = [t.name for t in tags]
            assert "<template>" in names
            assert "<script>" in names
            assert "<style>" in names

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
            tags = _parse_vue(path)
            names = [t.name for t in tags]
            assert "toggle" in names

    def test_vue_script_lang_ts(self):
        with _tmpfile(
            ".vue",
            b"""<script lang="ts" setup>
function greet(name: string): string { return name }
</script>
<template><div>hi</div></template>
""",
        ) as path:
            tags = _parse_vue(path)
            names = [t.name for t in tags]
            assert "greet" in names

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
            tags = _parse_vue(path)
            names = [t.name for t in tags]
            assert "logout" in names
            assert "handleClick" in names


class TestParseFile:
    """Tests for the _parse_file dispatcher."""

    def test_py_file(self):
        with _tmpfile(".py", b"def hello(): pass") as path:
            tags = _parse_file(path)
            names = [t.name for t in tags]
            assert "hello" in names

    def test_unknown_extension(self):
        with _tmpfile(".docx", b"binary data") as path:
            tags = _parse_file(path)
            assert tags == []

    def test_vue_file(self):
        with _tmpfile(".vue", b"<template><div/></template>") as path:
            tags = _parse_file(path)
            names = [t.name for t in tags]
            assert any("template" in n for n in names)


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
            assert "App" in result
            assert "run" in result
            assert "utils.py" in result
            assert "helper" in result
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
            tags = _extract_tags(path, "python")
            assert tags == []

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


class TestScmQueries:
    """Tests for .scm tag query extraction."""

    def test_python_definitions(self):
        code = b'''
class UserService:
    def get_user(self, user_id):
        pass

    def delete_user(self, user_id):
        pass

def helper():
    pass

async def async_helper():
    pass
'''
        tags = _extract_tags_from_source(code, "python")
        defs = [t for t in tags if t.kind == "def"]
        names = [t.name for t in defs]
        assert "UserService" in names
        assert "get_user" in names
        assert "delete_user" in names
        assert "helper" in names
        assert "async_helper" in names

    def test_python_definition_scope(self):
        """Method defined inside class has scope = class name, not self."""
        code = b'''
class MyClass:
    def method(self):
        pass

def top_level():
    pass
'''
        tags = _extract_tags_from_source(code, "python")
        defs = [t for t in tags if t.kind == "def"]
        method_def = [t for t in defs if t.name == "method"]
        assert len(method_def) == 1
        assert method_def[0].scope == "MyClass"
        class_def = [t for t in defs if t.name == "MyClass"]
        assert len(class_def) == 1
        assert class_def[0].scope == ""
        top_def = [t for t in defs if t.name == "top_level"]
        assert len(top_def) == 1
        assert top_def[0].scope == ""

    def test_javascript_definitions(self):
        code = b'''
class MyService {
    process(data) {
        return data;
    }
}

function helper() {}

const handler = (req, res) => { res.send("ok"); };
'''
        tags = _extract_tags_from_source(code, "javascript")
        defs = [t.name for t in tags if t.kind == "def"]
        assert "MyService" in defs
        assert "process" in defs
        assert "helper" in defs
        assert "handler" in defs

    def test_typescript_definitions(self):
        code = b'''
interface UserRepo {
    find(id: string): User;
}

class UserService implements UserRepo {
    find(id: string): User {
        return db.get(id);
    }
}

function createService(): UserService {
    return new UserService();
}

const factory = (config: Config) => new UserService();
'''
        tags = _extract_tags_from_source(code, "typescript")
        defs = [t.name for t in tags if t.kind == "def"]
        assert "UserRepo" in defs
        assert "UserService" in defs
        assert "find" in defs
        assert "createService" in defs
        assert "factory" in defs

    def test_tsx_definitions(self):
        code = b'''
function App() {
    return <div>Hello</div>;
}

const Button = ({ label }) => <button>{label}</button>;
'''
        tags = _extract_tags_from_source(code, "tsx")
        defs = [t.name for t in tags if t.kind == "def"]
        assert "App" in defs
        assert "Button" in defs

class TestRepoMapWithReferences:
    def test_no_references_by_default(self):
        import tempfile, shutil
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "auth.py"), "w") as f:
                f.write("def login(user):\n    pass\n")
            with open(os.path.join(tmpdir, "views.py"), "w") as f:
                f.write("from auth import login\ndef dashboard():\n    login(user)\n")
            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)
            assert "->" not in result
        finally:
            shutil.rmtree(tmpdir)


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
            tags = _extract_tags(path, "python")
            assert any(t.name == "boundary" for t in tags)

    def test_file_over_max_size_is_skipped(self):
        """Catches mutation: removing the MAX_FILE_SIZE check entirely."""
        with _tmpfile(".py", b"") as path:
            with open(path, "wb") as f:
                f.write(b"def toobig(): pass\n" + b" " * MAX_FILE_SIZE)
            assert os.path.getsize(path) > MAX_FILE_SIZE
            tags = _extract_tags(path, "python")
            assert tags == []

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


class TestRepomapOutput:
    """Tests for the full repomap output — what the agent actually sees."""

    def test_python_class_with_methods(self):
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "service.py"), "w") as f:
                f.write(
                    "class UserService:\n"
                    "    def create(self, name):\n"
                    "        pass\n"
                    "    def delete(self, uid):\n"
                    "        pass\n"
                    "\n"
                    "def helper():\n"
                    "    pass\n"
                )
            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)
            assert "UserService (class)" in result
            assert "create (method)" in result
            assert "delete (method)" in result
            assert "helper (function)" in result
        finally:
            shutil.rmtree(tmpdir)

    def test_nested_functions_not_labeled_method(self):
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "app.py"), "w") as f:
                f.write(
                    "def setup():\n"
                    "    def inner():\n"
                    "        pass\n"
                )
            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)
            assert "setup (function)" in result
            assert "inner (function)" in result
            assert "method" not in result
        finally:
            shutil.rmtree(tmpdir)

    def test_javascript_arrow_functions(self):
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "handler.js"), "w") as f:
                f.write(
                    "function process() {}\n"
                    "const handler = (req) => {};\n"
                )
            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)
            assert "process (function)" in result
            assert "handler (function)" in result
        finally:
            shutil.rmtree(tmpdir)

    def test_typescript_interface_and_class(self):
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "models.ts"), "w") as f:
                f.write(
                    "interface UserRepo {\n"
                    "    find(id: string): User;\n"
                    "}\n"
                    "class UserService {\n"
                    "    find(id: string) { return null; }\n"
                    "}\n"
                )
            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)
            assert "UserRepo (class)" in result  # interface shown as class
            assert "UserService (class)" in result
            assert "find (method)" in result
        finally:
            shutil.rmtree(tmpdir)

    def test_vue_sfc_output(self):
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "App.vue"), "w") as f:
                f.write(
                    "<template>\n"
                    "  <div>Hello</div>\n"
                    "</template>\n"
                    "<script>\n"
                    "export default {\n"
                    "  methods: {\n"
                    "    logout() { console.log('bye') }\n"
                    "  }\n"
                    "}\n"
                    "</script>\n"
                    "<style scoped>\n"
                    ".app { color: red }\n"
                    "</style>\n"
                )
            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)
            assert "<template>" in result
            assert "<script>" in result
            assert "<style>" in result
            assert "logout" in result
        finally:
            shutil.rmtree(tmpdir)

    def test_directory_structure(self):
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "src"))
            with open(os.path.join(tmpdir, "src", "main.py"), "w") as f:
                f.write("def main():\n    pass\n")
            with open(os.path.join(tmpdir, "README.md"), "w") as f:
                f.write("# Hello\n")
            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)
            assert "src/" in result
            assert "main.py" in result
            assert "main (function)" in result
        finally:
            shutil.rmtree(tmpdir)

    def test_same_name_class_and_function(self):
        """Function nested in function named same as a class should NOT be method."""
        tmpdir = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmpdir, "weird.py"), "w") as f:
                f.write(
                    "class Foo:\n"
                    "    def bar(self):\n"
                    "        pass\n"
                    "\n"
                    "def Foo():\n"
                    "    def inner():\n"
                    "        pass\n"
                )
            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)
            # bar inside class Foo → method
            assert "bar (method)" in result
            # inner inside function Foo → function, NOT method
            assert "inner (function)" in result
        finally:
            shutil.rmtree(tmpdir)

    def test_empty_project(self):
        tmpdir = tempfile.mkdtemp()
        try:
            gen = RepomapGenerator()
            result = gen.get_map(tmpdir)
            assert result == "(empty project)"
        finally:
            shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _extract_tags_from_source(code: bytes, lang: str) -> list:
    """Helper: write code to temp file and extract tags."""
    ext = {"python": ".py", "javascript": ".js", "typescript": ".ts", "tsx": ".tsx"}[lang]
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(code)
        f.flush()
        tags = _extract_tags(f.name, lang)
    os.unlink(f.name)
    return tags


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
        TestScmQueries,
        TestRepoMapWithReferences,
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
