# Fix logic error in discount calculator

The `calculate_discount()` function in `pricing.py` returns wrong results for some inputs.

## Bug
- `calculate_discount(100, "premium", 5)` returns `85.0` but should return `80.0` (premium = 20% off, loyalty 5% stacks)
- `calculate_discount(50, "basic", 3)` returns `50.0` but should return `47.5` (basic = 5% off, loyalty 3% stacks)

The discount percentages are wrong and the loyalty discount is not being applied correctly.

## Expected behavior
- Membership tiers: `basic` = 5%, `standard` = 10%, `premium` = 20%
- Loyalty bonus: 1% per year of membership (capped at 10%)
- Discounts are additive (stack), not multiplicative
- Minimum price after discount: 0 (can't go negative)
