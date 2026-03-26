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

