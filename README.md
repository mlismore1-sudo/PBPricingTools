# Bank Switching Benefit Calculator

A Streamlit application comparing a prospective client's current annual
investment fees and savings interest with the proposed bank's pricing.

## Features

- Three-section client questionnaire.
- DPM and Private Markets fees entered as annual percentages or annual
  GBP amounts.
- Tiered savings interest.
- Mandatory annual client fee deducted once.
- Positive and negative switching outcomes.
- Downloadable CSV comparison, including inputs and assumptions.
- Decimal-based calculations.
- Automated calculation tests and GitHub Actions.

## Requirements

- Python 3.11 recommended.
- Dependencies listed in requirements.txt.

## Run locally

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

Or on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies and start the app:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Run tests

From the repository root:

```bash
python -m unittest discover -s tests -v
```

## Configure pricing

Edit pricing.json.

All percentage values use percentage units:

- "0.35" means 0.35%.
- "4.00" means 4%.

Default pricing:

- Annual client fee: GBP 1,800.
- DPM: 0.35% annually.
- Private Markets: 0.35% annually.
- Savings: 4% on the first GBP 200,000.
- Savings: 3.5% on the balance above GBP 200,000.

Quoted bank charges are assumed inclusive of applicable VAT.
Confirm this interpretation before using the comparison with clients.

## Calculation

DPM saving =
current annual DPM fee - proposed annual DPM fee

Private Markets saving =
current annual platform fee - proposed annual platform fee

Additional savings interest =
proposed annual savings interest - current annual savings interest

Net annual benefit =
DPM saving + Private Markets saving
+ additional savings interest - annual client fee

A negative net annual benefit means an additional annual cost.

Each annual charge or interest amount is rounded to the nearest penny
using ROUND_HALF_UP before differences are calculated.

## Worked example

Inputs:

- DPM AUM: GBP 500,000.
- Current DPM fee: 1.00%.
- Private Markets AUM: GBP 250,000.
- Current platform fee: 0.75%.
- Savings: GBP 300,000.
- Current savings rate: 3.00%.

Results:

- DPM saving: GBP 3,250.
- Private Markets saving: GBP 1,000.
- Additional savings interest: GBP 2,500.
- Product benefit before client fee: GBP 6,750.
- Annual client fee: GBP 1,800.
- Net annual benefit: GBP 4,950.

## Deployment configuration

For a Streamlit deployment, use:

- Repository: this GitHub repository.
- Branch: your deployment branch, normally main.
- Entrypoint: app.py.
- Python: 3.11 where available.

The deployment environment must install requirements.txt.

After validating your environment, consider pinning the exact tested
Streamlit version in requirements.txt.

## Scope and limitations

- All entered balances are assumed to transfer.
- Enter zero for products outside the proposed move.
- Balances and rates remain unchanged for a full year.
- Savings interest is a simple annual estimate before tax.
- No intra-year compounding is modelled.
- Current savings interest applies the entered rate to the entire balance.
- The annual client fee is charged once, including savings-only cases.
- Existing provider membership fees are not modelled separately.
- Investment returns, exit fees, transfer fees, underlying fund charges,
  tax and unlisted charges are excluded.
- This is a pricing illustration, not a recommendation.

## Data handling

The application does not require client identifiers and does not
implement a database or deliberately persist submitted figures to disk.

The latest comparison is held in Streamlit session state. Users can
explicitly download a CSV containing the submitted financial figures.

This application does not implement authentication. Review access
controls, hosting arrangements, logs, exports and your organisation's
data-handling requirements before using real client information.

## Production review

Before client-facing use:

1. Confirm the VAT treatment of all quoted bank charges.
2. Confirm savings rate conventions and applicable product conditions.
3. Confirm which charges the comparison must include.
4. Validate results against approved bank examples.
5. Arrange appropriate access control and compliance review.
