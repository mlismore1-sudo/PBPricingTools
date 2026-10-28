"""Streamlit interface for the bank benefit calculator."""

import csv
import io
import json
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
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
    "Savings interest is a simple annual estimate before tax; no "
    "intra-year compounding is modelled.",
    "The mandatory annual client fee is deducted once.",
    "Existing provider membership charges are not included in this version.",
    "Investment returns, tax, exit/transfer fees, underlying fund charges "
    "and other unlisted charges are excluded.",
    "This is an illustrative price and interest comparison, not a "
    "recommendation or a guarantee of returns.",
]


def load_pricing() -> Pricing:
    with (BASE_DIR / "pricing.json").open(encoding="utf-8") as file:
        return Pricing(**json.load(file))


def gbp(value: Decimal) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}£{abs(value):,.2f}"


def signed_gbp(value: Decimal) -> str:
    if value > 0:
        return f"+£{value:,.2f}"
    return gbp(value)


def fee_input(label: str, key: str):
    mode_label = st.selectbox(
        f"{label}: input format",
        options=["Annual percentage (%)", "Annual amount (£)"],
        key=f"{key}_mode",
    )

    mode = (
        PERCENT
        if mode_label == "Annual percentage (%)"
        else ANNUAL_GBP
    )

    value = st.number_input(
        f"{label} ({'%' if mode == PERCENT else '£'}, inc VAT)",
        min_value=0.0,
        value=0.0,
        step=0.01 if mode == PERCENT else 100.0,
        format="%.2f",
        key=f"{key}_value",
        help="Enter 1.00 for a 1% annual fee, or select annual £ amount.",
    )

    return value, mode


def comparison_rows(result, bank_name):
    return [
        {
            "Item": "DPM annual fee",
            "Current arrangement": gbp(result.current_dpm_fee),
            bank_name: gbp(result.bank_dpm_fee),
            "Annual benefit / (cost)": signed_gbp(result.dpm_saving),
        },
        {
            "Item": "Private Markets annual platform fee",
            "Current arrangement": gbp(result.current_private_markets_fee),
            bank_name: gbp(result.bank_private_markets_fee),
            "Annual benefit / (cost)": signed_gbp(
                result.private_markets_saving
            ),
        },
        {
            "Item": "Annual savings interest earned",
            "Current arrangement": gbp(result.current_savings_interest),
            bank_name: gbp(result.bank_savings_interest),
            "Annual benefit / (cost)": signed_gbp(
                result.additional_savings_interest
            ),
        },
        {
            "Item": "Mandatory annual client fee",
            "Current arrangement": "Not included",
            bank_name: gbp(result.annual_client_fee),
            "Annual benefit / (cost)": signed_gbp(
                -result.annual_client_fee
            ),
        },
        {
            "Item": "Net annual cost: included fees less interest",
            "Current arrangement": gbp(result.current_net_annual_cost),
            bank_name: gbp(result.bank_net_annual_cost),
            "Annual benefit / (cost)": signed_gbp(
                result.net_annual_benefit
            ),
        },
    ]


def export_csv(snapshot) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Bank switching comparison"])
    writer.writerow(["Generated at (UTC)", snapshot["generated_at"]])
    writer.writerow([])

    for title, data in (
        ("Submitted inputs", asdict(snapshot["client"])),
        ("Bank pricing", asdict(snapshot["pricing"])),
        ("Annual results", asdict(snapshot["result"])),
    ):
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
    f"Compare your current annual charges and savings interest "
    f"with {pricing.bank_name}."
)
st.caption(
    "Enter the balances proposed for transfer. "
    "Use zero for any product not included."
)

with st.expander("Our pricing and calculation assumptions"):
    st.write(f"Mandatory annual client fee: {gbp(pricing.annual_client_fee)}")
    st.write(f"DPM: {pricing.dpm_rate_percent}% per year")
    st.write(
        f"Private Markets platform fee: "
        f"{pricing.private_markets_rate_percent}% per year"
    )
    st.write(
        f"Savings: {pricing.savings_lower_tier_rate_percent}% on the "
        f"first {gbp(pricing.savings_threshold)}, then "
        f"{pricing.savings_upper_tier_rate_percent}% on the excess."
    )
    for assumption in ASSUMPTIONS:
        st.write(f"- {assumption}")

with st.form("comparison_form"):
    st.header("Section 1 — Discretionary Portfolio Management")

    dpm_aum = st.number_input(
        "How much AUM does the client have in DPM? (£)",
        min_value=0.0,
        value=0.0,
        step=10000.0,
        format="%.2f",
    )
    dpm_fee, dpm_mode = fee_input(
        "What is the current annual DPM fee?",
        "dpm",
    )

    st.header("Section 2 — Private Markets")

    pm_aum = st.number_input(
        "How much AUM does the client have in Private Markets? (£)",
        min_value=0.0,
        value=0.0,
        step=10000.0,
        format="%.2f",
    )
    pm_fee, pm_mode = fee_input(
        "What is the current annual platform fee?",
        "private_markets",
    )

    st.header("Section 3 — Savings")

    savings_balance = st.number_input(
        "What amount is the client holding in savings? (£)",
        min_value=0.0,
        value=0.0,
        step=10000.0,
        format="%.2f",
    )
    savings_rate = st.number_input(
        "What is their current annual savings rate? (%)",
        min_value=0.0,
        value=0.0,
        step=0.05,
        format="%.2f",
        help="Enter 3.50 for 3.5%.",
    )

    submitted = st.form_submit_button(
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

        st.session_state["comparison"] = {
            "client": client,
            "pricing": pricing,
            "result": compare(client, pricing),
            "generated_at": datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ),
        }
    except ValueError as exc:
        # Do not leave an old comparison visible after invalid submission.
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
        "After editing the form, click Calculate annual benefit again."
    )

    if result.net_annual_benefit > 0:
        st.success(
            f"Estimated net annual benefit: "
            f"{gbp(result.net_annual_benefit)}"
        )
    elif result.net_annual_benefit < 0:
        st.error(
            f"Estimated additional annual cost: "
            f"{gbp(abs(result.net_annual_benefit))}"
        )
    else:
        st.info("The proposed move breaks even on the included annual items.")

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

    st.table(comparison_rows(result, submitted_pricing.bank_name))

    st.write(
        f"Product benefit before client fee: "
        f"{signed_gbp(result.gross_annual_benefit)}"
    )
    st.write(
        f"Less mandatory annual client fee: "
        f"{gbp(result.annual_client_fee)}"
    )
    st.write(
        f"Net annual benefit / (cost): "
        f"{signed_gbp(result.net_annual_benefit)}"
    )

    st.caption(
        "Positive benefit values favour switching; negative values favour "
        "the current arrangement. Savings interest is income, whereas "
        "investment fees and the client fee are costs. A negative net "
        "annual cost means included interest exceeds included fees."
    )

    with st.expander("Submitted inputs used in this comparison"):
        st.json({
            key: str(value)
            for key, value in asdict(snapshot["client"]).items()
        })

    st.download_button(
        label="Download comparison as CSV",
        data=export_csv(snapshot),
        file_name="bank_switching_comparison.csv",
        mime="text/csv",
    )

st.divider()
st.caption(
    "No client names or account numbers are required. This application "
    "does not implement a database or deliberately write submitted "
    "financial values to disk. Review hosting access, logging and data "
    "handling before entering real client information."
)
