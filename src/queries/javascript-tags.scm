;; --- Definitions ---

(class_declaration
  name: (identifier) @name.definition.class)

(function_declaration
  name: (identifier) @name.definition.function)

(method_definition
  name: (property_identifier) @name.definition.function)

;; Arrow functions assigned to const/let/var
(lexical_declaration
  (variable_declarator
    name: (identifier) @name.definition.function
    value: (arrow_function)))

