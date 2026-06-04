;; from auth import login  (single name)
(import_from_statement
  module_name: (_) @import.source
  name: (dotted_name (identifier) @import.name))

;; from auth import login as lg  (aliased)
(import_from_statement
  module_name: (_) @import.source
  name: (aliased_import
    name: (dotted_name (identifier) @import.name)))
