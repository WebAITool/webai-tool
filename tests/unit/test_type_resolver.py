import os, tempfile
from graph.type_resolver import extract_type_bindings


def _tmp(suffix: str, content: str) -> str:
    f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode="w")
    f.write(content)
    f.close()
    return f.name


def test_python_constructor_binding():
    path = _tmp(".py", "service = UserService()\n")
    try:
        bindings = extract_type_bindings(path, "python")
        assert any(b.var_name == "service" and b.resolved_type == "UserService"
                   for b in bindings)
    finally:
        os.unlink(path)


def test_python_annotation_binding():
    path = _tmp(".py", "def handle(svc: UserService): pass\n")
    try:
        bindings = extract_type_bindings(path, "python")
        assert any(b.var_name == "svc" and b.resolved_type == "UserService"
                   for b in bindings)
    finally:
        os.unlink(path)


def test_unannotated_assignment_no_binding():
    path = _tmp(".py", "service = get_service()\n")
    try:
        bindings = extract_type_bindings(path, "python")
        assert not any(b.var_name == "service" for b in bindings)
    finally:
        os.unlink(path)


def test_ts_new_expression():
    path = _tmp(".ts", "const svc = new UserService();\n")
    try:
        bindings = extract_type_bindings(path, "typescript")
        assert any(b.var_name == "svc" and b.resolved_type == "UserService"
                   for b in bindings)
    finally:
        os.unlink(path)


def test_ts_type_annotation():
    path = _tmp(".ts", "const svc: UserService = createService();\n")
    try:
        bindings = extract_type_bindings(path, "typescript")
        assert any(b.var_name == "svc" and b.resolved_type == "UserService"
                   for b in bindings)
    finally:
        os.unlink(path)


def test_ts_return_type_function():
    """function create(): UserService {} → TypeBinding."""
    code = "function create(): UserService { return new UserService() }\n"
    path = _tmp(".ts", code)
    try:
        bindings = extract_type_bindings(path, "typescript")
        rt = [b for b in bindings if b.source == "return-type"]
        assert len(rt) >= 1
        assert rt[0].var_name == "create"
        assert rt[0].resolved_type == "UserService"
    finally:
        os.unlink(path)


def test_ts_return_type_method():
    """class Foo { create(): UserService {} } → TypeBinding."""
    code = "class Foo {\n  create(): UserService { return new UserService() }\n}\n"
    path = _tmp(".ts", code)
    try:
        bindings = extract_type_bindings(path, "typescript")
        rt = [b for b in bindings if b.source == "return-type"]
        assert len(rt) >= 1
        assert rt[0].var_name == "create"
        assert rt[0].resolved_type == "UserService"
    finally:
        os.unlink(path)
