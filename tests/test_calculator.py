import unittest
from decimal import Decimal

from calculator import (
    ANNUAL_GBP,
    PERCENT,
    ClientInputs,
    Pricing,
    compare,
    money,
    savings_interest,
)


D = Decimal


def default_pricing():
    return Pricing(
        bank_name="Our Bank",
        annual_client_fee="1800",
        dpm_rate_percent="0.35",
        private_markets_rate_percent="0.35",
        savings_threshold="200000",
        savings_lower_tier_rate_percent="4",
        savings_upper_tier_rate_percent="3.5",
    )


def client_inputs(**overrides):
    values = {
        "dpm_aum": "0",
        "dpm_current_fee": "0",
        "dpm_fee_mode": PERCENT,
        "private_markets_aum": "0",
        "private_markets_current_fee": "0",
        "private_markets_fee_mode": PERCENT,
        "savings_balance": "0",
        "current_savings_rate_percent": "0",
    }
    values.update(overrides)
    return ClientInputs(**values)


class CalculatorTests(unittest.TestCase):
    def setUp(self):
        self.pricing = default_pricing()

    def test_savings_below_threshold(self):
        self.assertEqual(
            savings_interest("100000", self.pricing),
            D("4000.00"),
        )

    def test_savings_at_threshold(self):
        self.assertEqual(
            savings_interest("200000", self.pricing),
            D("8000.00"),
        )

    def test_savings_above_threshold(self):
        # £200k at 4% plus £100k at 3.5%.
        self.assertEqual(
            savings_interest("300000", self.pricing),
            D("11500.00"),
        )

    def test_zero_balances_still_include_client_fee(self):
        result = compare(client_inputs(), self.pricing)
        self.assertEqual(result.gross_annual_benefit, D("0.00"))
        self.assertEqual(result.net_annual_benefit, D("-1800.00"))

    def test_full_worked_example(self):
        result = compare(
            client_inputs(
                dpm_aum="500000",
                dpm_current_fee="1",
                private_markets_aum="250000",
                private_markets_current_fee="0.75",
                savings_balance="300000",
                current_savings_rate_percent="3",
            ),
            self.pricing,
        )

        self.assertEqual(result.current_dpm_fee, D("5000.00"))
        self.assertEqual(result.bank_dpm_fee, D("1750.00"))
        self.assertEqual(result.dpm_saving, D("3250.00"))

        self.assertEqual(result.current_private_markets_fee, D("1875.00"))
        self.assertEqual(result.bank_private_markets_fee, D("875.00"))
        self.assertEqual(result.private_markets_saving, D("1000.00"))

        self.assertEqual(result.current_savings_interest, D("9000.00"))
        self.assertEqual(result.bank_savings_interest, D("11500.00"))
        self.assertEqual(result.additional_savings_interest, D("2500.00"))

        self.assertEqual(result.gross_annual_benefit, D("6750.00"))
        self.assertEqual(result.net_annual_benefit, D("4950.00"))

        self.assertEqual(
            result.current_net_annual_cost - result.bank_net_annual_cost,
            result.net_annual_benefit,
        )

    def test_annual_pound_fee_matches_percentage_fee(self):
        percent_result = compare(
            client_inputs(
                dpm_aum="500000",
                dpm_current_fee="1",
            ),
            self.pricing,
        )
        pounds_result = compare(
            client_inputs(
                dpm_aum="500000",
                dpm_current_fee="5000",
                dpm_fee_mode=ANNUAL_GBP,
            ),
            self.pricing,
        )
        self.assertEqual(percent_result, pounds_result)

    def test_lower_current_fees_produce_negative_saving(self):
        result = compare(
            client_inputs(
                dpm_aum="100000",
                dpm_current_fee="0.20",
            ),
            self.pricing,
        )
        self.assertEqual(result.dpm_saving, D("-150.00"))
        self.assertEqual(result.net_annual_benefit, D("-1950.00"))

    def test_higher_current_interest_is_not_a_benefit(self):
        result = compare(
            client_inputs(
                savings_balance="100000",
                current_savings_rate_percent="5",
            ),
            self.pricing,
        )
        self.assertEqual(result.additional_savings_interest, D("-1000.00"))
        self.assertEqual(result.net_annual_benefit, D("-2800.00"))

    def test_break_even(self):
        result = compare(
            client_inputs(
                savings_balance="100000",
                current_savings_rate_percent="2.2",
            ),
            self.pricing,
        )
        self.assertEqual(result.net_annual_benefit, D("0.00"))

    def test_invalid_numeric_inputs_are_rejected(self):
        for value in ("-1", "NaN", "Infinity", "not-a-number"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    client_inputs(savings_balance=value)

    def test_fee_against_zero_aum_is_rejected(self):
        with self.assertRaises(ValueError):
            client_inputs(
                dpm_aum="0",
                dpm_current_fee="500",
                dpm_fee_mode=ANNUAL_GBP,
            )

    def test_unsupported_fee_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            client_inputs(dpm_fee_mode="monthly")

    def test_half_penny_rounds_up(self):
        self.assertEqual(money(D("1.005")), D("1.01"))


if __name__ == "__main__":
    unittest.main()
