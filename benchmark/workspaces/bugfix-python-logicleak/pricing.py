"""Pricing calculator with logic bugs."""

MEMBERSHIP_DISCOUNTS = {
    "basic": 0.05,
    "standard": 0.10,
    "premium": 0.20,  # BUG: should be 0.20
}


def calculate_discount(price: float, membership: str, loyalty_years: int) -> float:
    """Calculate final price after membership + loyalty discounts."""
    if price <= 0:
        return 0.0

    membership_rate = MEMBERSHIP_DISCOUNTS.get(membership, 0)

    # BUG: loyalty bonus should be 1% per year, capped at 10%
    loyalty_rate = min(loyalty_years, 10) * 0.01  # BUG: 0.005 instead of 0.01

    total_discount = membership_rate + loyalty_rate
    final_price = price * (1 - total_discount)

    return max(final_price, 0.0)
