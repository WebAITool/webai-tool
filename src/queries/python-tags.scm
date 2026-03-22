;; --- Definitions ---

;; Classes
(class_definition
  name: (identifier) @name.definition.class)

;; Functions (top-level and methods)
(function_definition
  name: (identifier) @name.definition.function)

;; --- References ---

;; Function/method calls: foo(), obj.method()
(call
  function: (identifier) @name.reference.call)

;; obj.method() — capture both receiver and method name
(call
  function: (attribute
    object: (identifier) @method.receiver
    attribute: (identifier) @name.reference.call))

;; Imports: import foo / from foo import bar
(import_statement
  name: (dotted_name (identifier) @name.reference.import))

(import_from_statement
  module_name: (dotted_name (identifier) @name.reference.import))

(import_from_statement
  name: (dotted_name (identifier) @name.reference.import))
