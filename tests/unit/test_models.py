from graph.models import SymbolNode, Edge, ImportTag, TypeBinding, ReceiverTag
from repo_map import Tag

def test_symbol_node_id():
    n = SymbolNode(id="Function:login:src/auth.py", kind="Function",
                   name="login", file="src/auth.py", line=10,
                   scope="", is_exported=False)
    assert n.id == "Function:login:src/auth.py"

def test_edge_fields():
    e = Edge(source_id="A", target_id="B", kind="CALLS",
             confidence=0.95, reason="import-resolved")
    assert e.kind == "CALLS"

def test_import_tag():
    t = ImportTag(file="views.py", imported_name="login",
                  source_path="./auth", is_relative=True, line=1)
    assert t.imported_name == "login"

def test_type_binding():
    b = TypeBinding(file="views.py", var_name="svc",
                    resolved_type="UserService", scope="handle", source="constructor")
    assert b.resolved_type == "UserService"

def test_receiver_tag():
    r = ReceiverTag(file="views.py", receiver_name="svc",
                    method_name="validate", line=5, scope="handle")
    assert r.receiver_name == "svc"

def test_tag_has_node_type():
    t = Tag(file="f.py", name="Foo", line=1, kind="def")
    assert t.node_type == ""      # default
    assert t.capture_name == ""   # default
    t2 = Tag(file="f.py", name="IFoo", line=1, kind="def",
             node_type="interface_declaration",
             capture_name="name.definition.class")
    assert t2.node_type == "interface_declaration"
    assert t2.capture_name == "name.definition.class"
