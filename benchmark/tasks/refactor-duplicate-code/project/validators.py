"""Duplicate validation logic — needs refactoring."""

import re


def validate_name(value):
    if value is None:
        raise ValueError("name is required")
    if not isinstance(value, str):
        raise TypeError("name must be a string")
    if len(value) < 2:
        raise ValueError("name must be at least 2 characters")
    if len(value) > 100:
        raise ValueError("name must be at most 100 characters")
    return value


def validate_email(value):
    if value is None:
        raise ValueError("email is required")
    if not isinstance(value, str):
        raise TypeError("email must be a string")
    if len(value) < 5:
        raise ValueError("email must be at least 5 characters")
    if len(value) > 200:
        raise ValueError("email must be at most 200 characters")
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', value):
        raise ValueError("email format is invalid")
    return value


def validate_age(value):
    if value is None:
        raise ValueError("age is required")
    if not isinstance(value, int):
        raise TypeError("age must be an integer")
    if value < 0:
        raise ValueError("age must be at least 0")
    if value > 150:
        raise ValueError("age must be at most 150")
    return value


def validate_phone(value):
    if value is None:
        raise ValueError("phone is required")
    if not isinstance(value, str):
        raise TypeError("phone must be a string")
    if len(value) < 7:
        raise ValueError("phone must be at least 7 characters")
    if len(value) > 20:
        raise ValueError("phone must be at most 20 characters")
    if not re.match(r'^\+?[\d\s\-\(\)]+$', value):
        raise ValueError("phone format is invalid")
    return value
