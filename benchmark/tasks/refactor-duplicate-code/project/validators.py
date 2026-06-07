import re


class Validator:
    def validate(self, value, name, type_, min_len=None, max_len=None, pattern=None, min_val=None, max_val=None):
        if value is None:
            raise ValueError(f"{name} is required")
        
        if not isinstance(value, type_):
            if type_ == str:
                raise TypeError("must be a string")
            if type_ == int:
                raise TypeError("must be an integer")
            raise TypeError(f"{name} must be a {type_.__name__}")
        
        if isinstance(value, str):
            if name == "phone" and pattern and not re.match(pattern, value):
                raise ValueError("phone format is invalid")
            
            if min_len is not None and len(value) < min_len:
                raise ValueError(f"{name} must be at least {min_len} characters")
            if max_len is not None and len(value) > max_len:
                raise ValueError(f"{name} must be at most {max_len} characters")
            
            if name != "phone" and pattern and not re.match(pattern, value):
                raise ValueError(f"{name} format is invalid")
        
        if isinstance(value, int):
            if min_val is not None and value < min_val:
                raise ValueError(f"{name} must be at least {min_val}")
            if max_val is not None and value > max_val:
                raise ValueError(f"{name} must be at most {max_val}")
        
        return value


validator = Validator()


def validate_name(value):
    return validator.validate(value, "name", str, min_len=2, max_len=100)


def validate_email(value):
    return validator.validate(value, "email", str, min_len=5, max_len=200, pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def validate_age(value):
    return validator.validate(value, "age", int, min_val=0, max_val=150)


def validate_phone(value):
    return validator.validate(value, "phone", str, min_len=7, max_len=20, pattern=r'^\+?[\d\s\-\(\)]+$')


def validate_username(value):
    return validator.validate(value, "username", str, min_len=3, max_len=50)
