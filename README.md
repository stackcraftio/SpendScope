# SpendScope — Personal Finance Analytics Dashboard

SpendScope is a portfolio-ready Flask app that imports bank-style transaction CSVs, cleans and categorises them, stores them in SQLite, and produces an interactive personal-finance dashboard.

> **Privacy note:** this repository contains synthetic sample data only. Do not commit real bank statements.

## Features

- CSV transaction upload
- pandas-based cleaning and validation
- automatic rule-based categorisation
- SQLite persistence
- income, spending, and net balance KPIs
- monthly income vs spending chart
- spending-by-category chart
- monthly spending trend chart
- search and filter transactions
- likely recurring-payment detection
- simple monthly category budgets and alerts
- cleaned-data CSV export
- responsive Bootstrap UI
- unit tests
- GitHub Actions CI

## CSV format

SpendScope accepts a CSV containing these columns:

```text
date,description,amount
```

Amounts use this convention:

- positive = money in / income
- negative = money out / spending

Example:

```csv
date,description,amount
2026-01-02,ACME PAYROLL,2450.00
2026-01-03,RENT PAYMENT,-950.00
2026-01-05,TESCO STORES,-54.22
```

A synthetic file is included at:

```text
sample_data/sample_transactions.csv
```

## Run on macOS

Open Terminal and `cd` into this project folder.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Run the tests

```bash
source .venv/bin/activate
pytest
```

## Try the sample data

1. Start the app.
2. Open `http://127.0.0.1:5000`.
3. Use **Upload CSV**.
4. Select `sample_data/sample_transactions.csv`.

## GitHub Desktop / Add Local Repository

After unzipping the project:

1. Open GitHub Desktop.
2. Choose **File → Add Local Repository**.
3. Select the `SpendScope` folder.
4. If prompted, create a Git repository there.
5. Commit the files.
6. Publish the repository.

Or from Terminal:

```bash
git init
git add .
git commit -m "Initial SpendScope dashboard"
```

## Project structure

```text
SpendScope/
├── app.py
├── requirements.txt
├── spendscope/
│   ├── __init__.py
│   ├── db.py
│   ├── services.py
│   ├── routes.py
│   ├── templates/
│   └── static/
├── sample_data/
├── tests/
└── .github/workflows/ci.yml
```

## Categorisation

The categoriser is intentionally simple and transparent. It uses keyword rules such as:

- Tesco, Sainsbury's, Aldi → Groceries
- Netflix, Spotify → Entertainment
- Uber, TFL, Trainline → Transport
- Rent, mortgage → Housing
- Salary, payroll → Income

Unknown debit transactions are assigned `Other`.

## Recurring-payment detection

SpendScope groups outgoing transactions by a normalised merchant description and flags groups that:

- appear at least three times, and
- have a median gap of roughly 25–35 days or 6–8 days, and
- have reasonably consistent transaction amounts.

This is heuristic detection, not banking-grade subscription identification.

## Budget alerts

Budget limits are stored per category. If current-month spending in a category reaches:

- 80% of the limit: warning
- 100% or more: over-budget alert

You can edit the budget values from the dashboard.

## Notes

This project is designed as a local portfolio/demo application. It has no real bank API integration and no authentication layer.
