"""Tests for bugfix-python-logicleak task."""
import pytest
from pricing import calculate_discount


def test_basic_membership():
    assert calculate_discount(100, "basic", 0) == 95.0


def test_standard_membership():
    assert calculate_discount(100, "standard", 0) == 90.0


def test_premium_membership():
    assert calculate_discount(100, "premium", 0) == 80.0


def test_loyalty_bonus():
    # 5% membership + 5% loyalty = 10% off
    assert calculate_discount(100, "basic", 5) == 90.0


def test_premium_with_loyalty():
    # 20% premium + 5% loyalty = 25% off
    assert calculate_discount(100, "premium", 5) == 75.0


def test_loyalty_cap():
    # Loyalty capped at 10%, so 15 years = 10% loyalty only
    assert calculate_discount(100, "basic", 15) == 85.0  # 5% + 10%


def test_zero_price():
    assert calculate_discount(0, "premium", 10) == 0.0


def test_negative_price():
    assert calculate_discount(-50, "basic", 0) == 0.0


def test_unknown_membership():
    # Unknown tier = no membership discount, only loyalty
    assert calculate_discount(100, "unknown", 5) == 95.0
