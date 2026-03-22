;; Capture the source string from any import statement
(import_statement source: (string) @import.source)

;; import { login } from './auth'  (named import)
(import_specifier name: (identifier) @import.name)

;; import UserService from './services/user'  (default import)
(import_statement (import_clause (identifier) @import.name))
