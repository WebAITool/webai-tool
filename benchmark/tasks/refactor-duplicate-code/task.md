# Refactor duplicate validation logic

The file `validators.py` contains heavily duplicated validation code for different field types.
Each validator repeats the same pattern: check if value is None, check type, check constraints, raise ValueError.

## Current problems
- `validate_name`, `validate_email`, `validate_age`, `validate_phone` all follow the same pattern
- Adding a new validator means copy-pasting ~15 lines
- Bug fixes need to be applied in 4 places

## Requirements

1. **Extract a base `Validator` class** with common logic:
   - `required` check (raise ValueError if None and required)
   - `type` check (raise TypeError if wrong type)
   - `constraints` check (call a method that subclasses override)

2. **Implement specific validators** as subclasses:
   - `StringValidator` (min_length, max_length, pattern)
   - `IntValidator` (min_value, max_value)
   - `EmailValidator` (inherits StringValidator, adds email pattern)

3. **Keep the same public API**: `validate_name()`, `validate_email()`, `validate_age()`, `validate_phone()` must still work exactly as before (same error messages, same behavior).

4. **Add `validate_username()`** using the new framework as proof it works.

5. All existing behavior must be preserved — this is a refactor, not a behavior change.
