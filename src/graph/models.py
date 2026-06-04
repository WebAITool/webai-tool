# src/graph/models.py
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class SymbolNode:
    id: str             # "Function:login:src/auth.py"
    kind: str           # "Function" | "Class" | "Method" | "Interface"
    name: str
    file: str
    line: int
    scope: str          # enclosing class/function name
    is_exported: bool   # JS/TS: export keyword


@dataclass
class Edge:
    source_id: str
    target_id: str
    kind: str           # "CALLS" | "IMPORTS"
    confidence: float   # 0.0–1.0
    reason: str         # "same-file" | "self-access" | "import-resolved" |
                        # "type-resolved" | "scope-match" | "global-unique" | "unique-method"


@dataclass
class ImportTag:
    file: str
    imported_name: str  # "login", "*", "default"
    source_path: str    # "./auth", "auth.service"
    is_relative: bool
    line: int


@dataclass
class TypeBinding:
    file: str
    var_name: str        # "service", "order"
    resolved_type: str   # "UserService"
    scope: str           # enclosing function/method name
    source: str          # "constructor" | "annotation" | "new_expression"


@dataclass
class ReceiverTag:
    file: str
    receiver_name: str   # "service"
    method_name: str     # "validate"
    line: int
    scope: str           # enclosing function/method
