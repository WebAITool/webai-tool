;; Identical to typescript-tags.scm — TSX grammar shares the same node types.
;; Kept separate for potential JSX-specific extensions.

;; --- Definitions ---

(class_declaration
  name: (type_identifier) @name.definition.class)

(abstract_class_declaration
  name: (type_identifier) @name.definition.class)

(interface_declaration
  name: (type_identifier) @name.definition.class)

(function_declaration
  name: (identifier) @name.definition.function)

(method_definition
  name: (property_identifier) @name.definition.function)

(lexical_declaration
  (variable_declarator
    name: (identifier) @name.definition.function
    value: (arrow_function)))

;; --- References ---

(call_expression
  function: (identifier) @name.reference.call)

(call_expression
  function: (member_expression
    object: (identifier) @method.receiver
    property: (property_identifier) @name.reference.call))

(import_statement
  (import_clause
    (named_imports
      (import_specifier
        name: (identifier) @name.reference.import))))

;; Default import: import Foo from "bar"
(import_statement
  (import_clause
    (identifier) @name.reference.import))
