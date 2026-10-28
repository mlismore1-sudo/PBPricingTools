"""Annual bank-switching comparison engine."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Union


Number = Union[str, int, float, Decimal]

ZERO = Decimal("0")
PENNY = Decimal("0.01")
HUNDRED = Decimal("100")

PERCENT = "percent"
ANNUAL_GBP = "annual_gbp"


def decimal_value(value: Number, label: str = "Value") -> Decimal:
    """Convert a numeric input to a finite, non-negative Decimal."""
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{label} must be a valid number.") from exc

    if not result.is_finite() or result < ZERO:
        raise ValueError(f"{label} must be finite and non-negative.")

    return result


def money(value: Decimal) -> Decimal:
    return value.quantize(PENNY, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Pricing:
    bank_name: str
    annual_client_fee: Decimal
    dpm_rate_percent: Decimal
    private_markets_rate_percent: Decimal
    savings_threshold: Decimal
    savings_lower_tier_rate_percent: Decimal
    savings_upper_tier_rate_percent: Decimal

    def __post_init__(self):
        for field_name in (
            "annual_client_fee",
            "dpm_rate_percent",
            "private_markets_rate_percent",
            "savings_threshold",
            "savings_lower_tier_rate_percent",
            "savings_upper_tier_rate_percent",
        ):
            object.__setattr__(
                self,
                field_name,
                decimal_value(getattr(self, field_name), field_name),
            )

        if not isinstance(self.bank_name, str) or not self.bank_name.strip():
            raise ValueError("A bank name is required.")


@dataclass(frozen=True)
class ClientInputs:
    dpm_aum: Decimal
    dpm_current_fee: Decimal
    dpm_fee_mode: str

    private_markets_aum: Decimal
    private_markets_current_fee: Decimal
    private_markets_fee_mode: str

    savings_balance: Decimal
    current_savings_rate_percent: Decimal

    def __post_init__(self):
        for field_name in (
            "dpm_aum",
            "dpm_current_fee",
            "private_markets_aum",
            "private_markets_current_fee",
            "savings_balance",
            "current_savings_rate_percent",
        ):
            object.__setattr__(
                self,
                field_name,
                decimal_value(getattr(self, field_name), field_name),
            )

        for field_name in ("dpm_fee_mode", "private_markets_fee_mode"):
            if getattr(self, field_name) not in (PERCENT, ANNUAL_GBP):
                raise ValueError(f"Unsupported fee mode: {field_name}.")

        # Prevent a misleading saving from a fee entered against no assets.
        if self.dpm_aum == ZERO and self.dpm_current_fee != ZERO:
            raise ValueError(
                "DPM AUM is zero: enter zero for its current fee."
            )

        if (
            self.private_markets_aum == ZERO
            and self.private_markets_current_fee != ZERO
        ):
            raise ValueError(
                "Private Markets AUM is zero: enter zero for its current fee."
            )


@dataclass(frozen=True)
class Comparison:
    current_dpm_fee: Decimal
    bank_dpm_fee: Decimal
    dpm_saving: Decimal

    current_private_markets_fee: Decimal
    bank_private_markets_fee: Decimal
    private_markets_saving: Decimal

    current_savings_interest: Decimal
    bank_savings_interest: Decimal
    additional_savings_interest: Decimal

    annual_client_fee: Decimal
    gross_annual_benefit: Decimal
    net_annual_benefit: Decimal

    current_net_annual_cost: Decimal
    bank_net_annual_cost: Decimal


def annual_charge(
    balance: Decimal,
    quoted_fee: Decimal,
    mode: str,
) -> Decimal:
    if mode == PERCENT:
        return money(balance * quoted_fee / HUNDRED)

    if mode == ANNUAL_GBP:
        return money(quoted_fee)

    raise ValueError("Unsupported fee mode.")


def savings_interest(balance: Number, pricing: Pricing) -> Decimal:
    """Calculate tiered annual interest; round the total once."""
    balance = decimal_value(balance, "Savings balance")
    first_tier = min(balance, pricing.savings_threshold)
    second_tier = max(balance - pricing.savings_threshold, ZERO)

    return money(
        first_tier * pricing.savings_lower_tier_rate_percent / HUNDRED
        + second_tier * pricing.savings_upper_tier_rate_percent / HUNDRED
    )


def compare(client: ClientInputs, pricing: Pricing) -> Comparison:
    current_dpm = annual_charge(
        client.dpm_aum,
        client.dpm_current_fee,
        client.dpm_fee_mode,
    )
    bank_dpm = annual_charge(
        client.dpm_aum,
        pricing.dpm_rate_percent,
        PERCENT,
    )

    current_pm = annual_charge(
        client.private_markets_aum,
        client.private_markets_current_fee,
        client.private_markets_fee_mode,
    )
    bank_pm = annual_charge(
        client.private_markets_aum,
        pricing.private_markets_rate_percent,
        PERCENT,
    )

    current_interest = money(
        client.savings_balance
        * client.current_savings_rate_percent
        / HUNDRED
    )
    bank_interest = savings_interest(client.savings_balance, pricing)

    dpm_saving = current_dpm - bank_dpm
    pm_saving = current_pm - bank_pm
    extra_interest = bank_interest - current_interest

    annual_client_fee = money(pricing.annual_client_fee)
    gross = dpm_saving + pm_saving + extra_interest
    net = gross - annual_client_fee

    # Negative net cost means interest exceeds the included charges.
    current_net_cost = current_dpm + current_pm - current_interest
    bank_net_cost = (
        bank_dpm + bank_pm + annual_client_fee - bank_interest
    )

    return Comparison(
        current_dpm_fee=current_dpm,
        bank_dpm_fee=bank_dpm,
        dpm_saving=dpm_saving,
        current_private_markets_fee=current_pm,
        bank_private_markets_fee=bank_pm,
        private_markets_saving=pm_saving,
        current_savings_interest=current_interest,
        bank_savings_interest=bank_interest,
        additional_savings_interest=extra_interest,
        annual_client_fee=annual_client_fee,
        gross_annual_benefit=gross,
        net_annual_benefit=net,
        current_net_annual_cost=current_net_cost,
        bank_net_annual_cost=bank_net_cost,
    )
