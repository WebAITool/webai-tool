import re


class Validator:
    def __init__(self, name, required=True, type_=None):
        self.name = name
        self.required = required
        self.type_ = type_

    def validate(self, value):
        if self.required and value is None:
            raise ValueError(f"{self.name} is required")
        if self.type_ is not None and not isinstance(value, self.type_):
            if self.type_ == str:
                raise TypeError("must be a string")
            elif self.type_ == int:
                raise TypeError("must be an integer")
            else:
                raise TypeError(f"{self.name} must be a {self.type_.__name__}")
        self.check_constraints(value)
        return value

    def check_constraints(self, value):
        pass


class StringValidator(Validator):
    def __init__(self, name, min_length=None, max_length=None, pattern=None):
        super().__init__(name, required=True, type_=str)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern

    def check_constraints(self, value):
        if self.pattern is not None and not re.match(self.pattern, value):
            raise ValueError(f"{self.name} format is invalid")
        if self.min_length is not None and len(value) < self.min_length:
            raise ValueError(f"{self.name} must be at least {self.min_length} characters")
        if self.max_length is not None and len(value) > self.max_length:
            raise ValueError(f"{self.name} must be at most {self.max_length} characters")


class IntValidator(Validator):
    def __init__(self, name, min_value=None, max_value=None):
        super().__init__(name, required=True, type_=int)
        self.min_value = min_value
        self.max_value = max_value

    def check_constraints(self, value):
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"{self.name} must be at least {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"{self.name} must be at most {self.max_value}")


class EmailValidator(StringValidator):
    def __init__(self, name="email"):
        super().__init__(name, min_length=5, max_length=200,
                         pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


# Pre-configured validators for the public API
_name_validator = StringValidator("name", min_length=2, max_length=100)
_email_validator = EmailValidator()
_age_validator = IntValidator("age", min_value=0, max_value=150)
_phone_validator = StringValidator("phone", min_length=7, max_length=20,
                                   pattern=r'^\+?[\d\s\-\(\)]+$')
_username_validator = StringValidator("username", min_length=3, max_length=50)


def validate_name(value):
    return _name_validator.validate(value)


def validate_email(value):
    return _email_validator.validate(value)


def validate_age(value):
    return _age_validator.validate(value)


def validate_phone(value):
    return _phone_validator.validate(value)


def validate_username(value):
    return _username_validator.validate(value)
