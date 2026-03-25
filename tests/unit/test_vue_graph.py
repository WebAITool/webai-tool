# tests/unit/test_vue_graph.py
"""Tests for Vue SFC graph support."""
import os
import tempfile

from vue_utils import extract_vue_script, extract_vue_template_refs


VUE_BASIC = b"""\
<template>
  <div>Hello</div>
</template>

<script>
export default {
  methods: {
    logout() { console.log('bye') }
  }
}
</script>
"""

VUE_TS = b"""\
<template>
  <div>Hello</div>
</template>

<script lang="ts">
import { ref } from 'vue'
export default {
  setup() { return {} }
}
</script>
"""

VUE_SETUP = b"""\
<template>
  <div>{{ count }}</div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
const count = ref(0)
function increment() { count.value++ }
</script>
"""

VUE_NO_SCRIPT = b"""\
<template>
  <div>Static</div>
</template>
"""

VUE_TEMPLATE_REFS = b"""\
<template>
  <div>
    <Header />
    <UserCard :name="user" />
    <button @click="logout">Logout</button>
    <input @input="handleInput" />
  </div>
</template>

<script>
export default {
  methods: {
    logout() {},
    handleInput() {}
  }
}
</script>
"""


def test_extract_vue_script_basic():
    result = extract_vue_script(source=VUE_BASIC)
    assert result is not None
    script_bytes, lang, offset = result
    assert lang == "javascript"
    assert b"logout" in script_bytes
    assert offset > 0  # script block is not at line 0


def test_extract_vue_script_typescript():
    result = extract_vue_script(source=VUE_TS)
    assert result is not None
    _, lang, _ = result
    assert lang == "typescript"


def test_extract_vue_script_setup():
    result = extract_vue_script(source=VUE_SETUP)
    assert result is not None
    script_bytes, lang, offset = result
    assert lang == "typescript"
    assert b"increment" in script_bytes


def test_extract_vue_script_no_script():
    result = extract_vue_script(source=VUE_NO_SCRIPT)
    assert result is None


def test_extract_vue_template_refs_components():
    refs = extract_vue_template_refs(source=VUE_TEMPLATE_REFS)
    names = [name for name, _ in refs]
    assert "Header" in names
    assert "UserCard" in names
    # Lowercase tags (div, button, input) should NOT be included
    assert "div" not in names
    assert "button" not in names


def test_extract_vue_template_refs_events():
    refs = extract_vue_template_refs(source=VUE_TEMPLATE_REFS)
    names = [name for name, _ in refs]
    assert "logout" in names
    assert "handleInput" in names


# --- Task 2: _extract_tags_and_receivers for .vue ---

from repo_map import _extract_tags_and_receivers, _EXT_TO_LANG


def test_vue_in_ext_to_lang():
    assert ".vue" in _EXT_TO_LANG
    assert _EXT_TO_LANG[".vue"] == "vue"


def test_vue_tags_and_receivers():
    """_extract_tags_and_receivers returns tags from Vue <script> block."""
    with tempfile.NamedTemporaryFile(suffix=".vue", delete=False, mode="wb") as f:
        f.write(VUE_BASIC)
        tmp = f.name
    try:
        tags, receivers = _extract_tags_and_receivers(tmp, "vue")
        names = [t.name for t in tags if t.kind == "def"]
        assert "logout" in names
    finally:
        os.unlink(tmp)


def test_vue_tags_line_offset():
    """Tags from <script> have correct line numbers (offset by script position)."""
    with tempfile.NamedTemporaryFile(suffix=".vue", delete=False, mode="wb") as f:
        f.write(VUE_BASIC)
        tmp = f.name
    try:
        tags, _ = _extract_tags_and_receivers(tmp, "vue")
        logout_tags = [t for t in tags if t.name == "logout" and t.kind == "def"]
        assert len(logout_tags) == 1
        # logout is defined around line 7 in VUE_BASIC (inside <script> block)
        assert logout_tags[0].line >= 6
    finally:
        os.unlink(tmp)


def test_vue_template_refs_in_tags():
    """Template component/event refs appear as ref tags."""
    with tempfile.NamedTemporaryFile(suffix=".vue", delete=False, mode="wb") as f:
        f.write(VUE_TEMPLATE_REFS)
        tmp = f.name
    try:
        tags, _ = _extract_tags_and_receivers(tmp, "vue")
        ref_names = [t.name for t in tags if t.kind == "ref"]
        assert "Header" in ref_names
        assert "logout" in ref_names
    finally:
        os.unlink(tmp)


# --- Task 4: builder.py handles .vue ---

from graph.builder import build


def test_vue_graph_has_nodes(tmp_path):
    """build() on a dir with .vue files produces SymbolNodes."""
    vue_file = tmp_path / "App.vue"
    vue_file.write_bytes(VUE_BASIC)
    graph = build(str(tmp_path))
    names = [n.name for n in graph.nodes.values()]
    assert "logout" in names


def test_vue_graph_cross_file_edges(tmp_path):
    """Edges between .vue and .js files work."""
    vue_content = b"""\
<template><div></div></template>
<script>
import { helper } from './utils'
export default {
  methods: {
    run() { helper() }
  }
}
</script>
"""
    js_content = b"""\
export function helper() { return 1 }
"""
    (tmp_path / "App.vue").write_bytes(vue_content)
    (tmp_path / "utils.js").write_bytes(js_content)
    graph = build(str(tmp_path))
    # helper should exist as a node
    assert any(n.name == "helper" for n in graph.nodes.values())
    # There should be edges
    assert len(graph.edges) > 0


# --- Task 5: .vue import resolution ---

from graph.import_resolver import build_suffix_index, resolve_import


def test_vue_import_resolution():
    """import X from './Header.vue' resolves to the .vue file."""
    files = ["src/components/Header.vue", "src/App.vue"]
    index = build_suffix_index(files)
    result = resolve_import("./components/Header.vue", "src/App.vue", index)
    assert result == "src/components/Header.vue"


def test_vue_import_resolution_ambiguous():
    """import X from './Header.vue' resolves to .vue not .js when both exist."""
    files = ["src/components/Header.vue", "src/components/Header.js", "src/App.vue"]
    index = build_suffix_index(files)
    result = resolve_import("./components/Header.vue", "src/App.vue", index)
    assert result == "src/components/Header.vue"
