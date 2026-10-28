"""Streamlit interface for the bank benefit calculator."""

import csv
import io
import json
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import streamlit as st

from calculator import (
    ANNUAL_GBP,
    PERCENT,
    ClientInputs,
    Pricing,
    compare,
)


BASE_DIR = Path(__file__).resolve().parent

ASSUMPTIONS = [
    "All entered balances transfer and remain unchanged for one year.",
    "Quoted bank charges are assumed inclusive of applicable VAT.",
    "Current investment fees must be entered inclusive of VAT.",
    "Current savings interest uses the entered rate on the full balance.",
    (
        "Savings interest is a simple annual estimate before tax; "
        "no intra-year compounding is modelled."
    ),
    "The mandatory annual client fee is deducted once.",
    "Existing provider membership charges are not included in this version.",
    (
        "Investment returns, tax, exit/transfer fees, underlying fund "
        "charges and other unlisted charges are excluded."
    ),
    (
        "This is an illustrative price and interest comparison, "
        "not a recommendation or a guarantee of returns."
    ),
]


def load_pricing() -> Pricing:
    """Load bank pricing from the repository configuration."""
    with (BASE_DIR / "pricing.json").open(encoding="utf-8") as file:
        return Pricing(**json.load(file))


def gbp(value: Decimal) -> str:
    """Format a monetary value with commas and two decimal places."""
    sign = "-" if value < 0 else ""
    return f"{sign}£{abs(value):,.2f}"


def signed_gbp(value: Decimal) -> str:
    """Format a benefit or cost with an explicit positive sign."""
    if value > 0:
        return f"+£{value:,.2f}"
    return gbp(value)


def money_input(label: str, key: str) -> str:
    """
    Display a comma-formatted monetary input.

    Formatting is applied when the user presses Enter or leaves the field.
    The returned string has commas removed for calculator validation.
    """

    def format_value():
        raw = st.session_state[key].strip().replace(",", "")

        try:
            amount = Decimal(raw)
        except InvalidOperation:
            return

        # Leave invalid or negative entries unchanged so that submitting
        # the comparison produces the existing validation error.
        if amount.is_finite() and amount >= 0:
            st.session_state[key] = f"{amount:,.2f}"

    if key not in st.session_state:
        st.session_state[key] = "0.00"

    raw_value = st.text_input(
        label,
        key=key,
        on_change=format_value,
        placeholder="1,000,000.00",
        help=(
            "Enter an amount with or without commas. "
            "Commas are added when you press Enter or leave the field."
        ),
    )

    return raw_value.strip().replace(",", "")


def fee_input(label: str, key: str):
    """Collect an investment fee as a percentage or annual GBP amount."""
    mode_label = st.selectbox(
        f"{label}: input format",
        options=[
            "Annual percentage (%)",
            "Annual amount (£)",
        ],
        key=f"{key}_mode",
    )

    if mode_label == "Annual percentage (%)":
        value = st.number_input(
            f"{label} (%, inc VAT)",
            min_value=0.0,
            value=0.0,
            step=0.01,
            format="%.2f",
            key=f"{key}_percent_value",
            help="Enter 1.00 for a 1% annual fee.",
        )
        return value, PERCENT

    value = money_input(
        f"{label} (£, inc VAT)",
        key=f"{key}_gbp_value",
    )
    return value, ANNUAL_GBP


def comparison_rows(result, bank_name):
    """Build the product-by-product comparison table."""
    # Avoid duplicate column names if the configured bank name happens
    # to match one of the other table headings.
    bank_column = f"{bank_name} — proposed"

    return [
        {
            "Item": "DPM annual fee",
            "Current arrangement": gbp(result.current_dpm_fee),
            bank_column: gbp(result.bank_dpm_fee),
            "Annual benefit / (cost)": signed_gbp(
                result.dpm_saving
            ),
        },
        {
            "Item": "Private Markets annual platform fee",
            "Current arrangement": gbp(
                result.current_private_markets_fee
            ),
            bank_column: gbp(
                result.bank_private_markets_fee
            ),
            "Annual benefit / (cost)": signed_gbp(
                result.private_markets_saving
            ),
        },
        {
            "Item": "Annual savings interest earned",
            "Current arrangement": gbp(
                result.current_savings_interest
            ),
            bank_column: gbp(
                result.bank_savings_interest
            ),
            "Annual benefit / (cost)": signed_gbp(
                result.additional_savings_interest
            ),
        },
        {
            "Item": "Mandatory annual client fee",
            "Current arrangement": "Not included",
            bank_column: gbp(result.annual_client_fee),
            "Annual benefit / (cost)": signed_gbp(
                -result.annual_client_fee
            ),
        },
        {
            "Item": "Net annual cost: included fees less interest",
            "Current arrangement": gbp(
                result.current_net_annual_cost
            ),
            bank_column: gbp(
                result.bank_net_annual_cost
            ),
            "Annual benefit / (cost)": signed_gbp(
                result.net_annual_benefit
            ),
        },
    ]


def export_csv(snapshot) -> str:
    """Export submitted inputs, pricing, results and assumptions."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Bank switching comparison"])
    writer.writerow([
        "Generated at (UTC)",
        snapshot["generated_at"],
    ])
    writer.writerow([])

    sections = (
        ("Submitted inputs", asdict(snapshot["client"])),
        ("Bank pricing", asdict(snapshot["pricing"])),
        ("Annual results", asdict(snapshot["result"])),
    )

    for title, data in sections:
        writer.writerow([title])
        writer.writerow(["Field", "Value"])

        for key, value in data.items():
            writer.writerow([key, str(value)])

        writer.writerow([])

    writer.writerow(["Assumptions"])

    for assumption in ASSUMPTIONS:
        writer.writerow([assumption])

    return output.getvalue()


st.set_page_config(
    page_title="Bank Switching Benefit Calculator",
    page_icon="£",
    layout="wide",
)

try:
    pricing = load_pricing()
except (OSError, ValueError, TypeError) as exc:
    st.error(f"Unable to load bank pricing: {exc}")
    st.stop()


st.title("Bank Switching Benefit Calculator")

st.write(
    "Compare your current annual charges and savings interest "
    f"with {pricing.bank_name}."
)

st.caption(
    "Enter the balances proposed for transfer. "
    "Use zero for any product not included. "
    "Monetary amounts are formatted with commas when you leave a field."
)


with st.expander("Our pricing and calculation assumptions"):
    st.write(
        "Mandatory annual client fee: "
        f"{gbp(pricing.annual_client_fee)}"
    )

    st.write(
        f"DPM: {pricing.dpm_rate_percent}% per year"
    )

    st.write(
        "Private Markets platform fee: "
        f"{pricing.private_markets_rate_percent}% per year"
    )

    st.write(
        f"Savings: {pricing.savings_lower_tier_rate_percent}% "
        f"on the first {gbp(pricing.savings_threshold)}, then "
        f"{pricing.savings_upper_tier_rate_percent}% "
        "on the excess."
    )

    for assumption in ASSUMPTIONS:
        st.write(f"- {assumption}")


# Inputs are outside a Streamlit form so that individual monetary
# fields can apply formatting callbacks when their values change.
with st.container():
    st.header(
        "Section 1 — Discretionary Portfolio Management"
    )

    dpm_aum = money_input(
        "How much AUM does the client have in DPM? (£)",
        key="dpm_aum_input",
    )

    dpm_fee, dpm_mode = fee_input(
        "What is the current annual DPM fee?",
        key="dpm",
    )

    st.divider()

    st.header("Section 2 — Private Markets")

    pm_aum = money_input(
        "How much AUM does the client have in Private Markets? (£)",
        key="pm_aum_input",
    )

    pm_fee, pm_mode = fee_input(
        "What is the current annual platform fee?",
        key="private_markets",
    )

    st.divider()

    st.header("Section 3 — Savings")

    savings_balance = money_input(
        "What amount is the client holding in savings? (£)",
        key="savings_balance_input",
    )

    savings_rate = st.number_input(
        "What is their current annual savings rate? (%)",
        min_value=0.0,
        value=0.0,
        step=0.05,
        format="%.2f",
        key="current_savings_rate_input",
        help="Enter 3.50 for 3.5%.",
    )

    submitted = st.button(
        "Calculate annual benefit",
        type="primary",
    )


if submitted:
    try:
        client = ClientInputs(
            dpm_aum=dpm_aum,
            dpm_current_fee=dpm_fee,
            dpm_fee_mode=dpm_mode,
            private_markets_aum=pm_aum,
            private_markets_current_fee=pm_fee,
            private_markets_fee_mode=pm_mode,
            savings_balance=savings_balance,
            current_savings_rate_percent=savings_rate,
        )

        result = compare(client, pricing)

        st.session_state["comparison"] = {
            "client": client,
            "pricing": pricing,
            "result": result,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(timespec="seconds"),
        }

    except ValueError as exc:
        # Remove an old result after an invalid submission.
        st.session_state.pop("comparison", None)
        st.error(str(exc))


snapshot = st.session_state.get("comparison")

if snapshot is not None:
    result = snapshot["result"]
    submitted_pricing = snapshot["pricing"]

    st.divider()
    st.header("Annual comparison")

    st.caption(
        "Results reflect the last submitted inputs. "
        "After editing the fields, click Calculate annual benefit again."
    )

    if result.net_annual_benefit > 0:
        st.success(
            "Estimated net annual benefit: "
            f"{gbp(result.net_annual_benefit)}"
        )

    elif result.net_annual_benefit < 0:
        st.error(
            "Estimated additional annual cost: "
            f"{gbp(abs(result.net_annual_benefit))}"
        )

    else:
        st.info(
            "The proposed move breaks even on the included annual items."
        )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "DPM annual fee saving / (increase)",
        signed_gbp(result.dpm_saving),
    )

    col2.metric(
        "Private Markets fee saving / (increase)",
        signed_gbp(result.private_markets_saving),
    )

    col3.metric(
        "Additional annual savings interest / (reduction)",
        signed_gbp(result.additional_savings_interest),
    )

    st.table(
        comparison_rows(
            result,
            submitted_pricing.bank_name,
        )
    )

    st.subheader("Total annual impact")

    st.write(
        "Product benefit before client fee: "
        f"{signed_gbp(result.gross_annual_benefit)}"
    )

    st.write(
        "Less mandatory annual client fee: "
        f"{gbp(result.annual_client_fee)}"
    )

    st.write(
        "Net annual benefit / (cost): "
        f"{signed_gbp(result.net_annual_benefit)}"
    )

    st.caption(
        "Positive benefit values favour switching; negative values "
        "favour the current arrangement. Savings interest is income, "
        "whereas investment fees and the client fee are costs. "
        "A negative net annual cost means included interest exceeds "
        "included fees."
    )

    with st.expander(
        "Submitted inputs used in this comparison"
    ):
        submitted_client = snapshot["client"]

        submitted_inputs = [
            {
                "Input": "DPM AUM",
                "Submitted value": gbp(
                    submitted_client.dpm_aum
                ),
            },
            {
                "Input": "Current annual DPM fee",
                "Submitted value": (
                    f"{submitted_client.dpm_current_fee:,.2f}%"
                    if submitted_client.dpm_fee_mode == PERCENT
                    else gbp(
                        submitted_client.dpm_current_fee
                    )
                ),
            },
            {
                "Input": "Private Markets AUM",
                "Submitted value": gbp(
                    submitted_client.private_markets_aum
                ),
            },
            {
                "Input": "Current annual platform fee",
                "Submitted value": (
                    f"{submitted_client.private_markets_current_fee:,.2f}%"
                    if (
                        submitted_client.private_markets_fee_mode
                        == PERCENT
                    )
                    else gbp(
                        submitted_client.private_markets_current_fee
                    )
                ),
            },
            {
                "Input": "Savings balance",
                "Submitted value": gbp(
                    submitted_client.savings_balance
                ),
            },
            {
                "Input": "Current annual savings rate",
                "Submitted value": (
                    f"{submitted_client.current_savings_rate_percent:,.2f}%"
                ),
            },
        ]

        st.table(submitted_inputs)

    st.download_button(
        label="Download comparison as CSV",
        data=export_csv(snapshot),
        file_name="bank_switching_comparison.csv",
        mime="text/csv",
    )


st.divider()

st.caption(
    "No client names or account numbers are required. "
    "This application does not implement a database or deliberately "
    "write submitted financial values to disk. "
    "Review hosting access, logging and data handling before entering "
    "real client information."
)
