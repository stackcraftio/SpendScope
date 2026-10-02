import io
import re

import pandas as pd


CATEGORY_RULES = [
    ("Income", ["salary", "payroll", "wages", "bonus", "refund"]),
    ("Housing", ["rent", "mortgage", "letting", "landlord"]),
    ("Groceries", ["tesco", "sainsbury", "aldi", "lidl", "waitrose", "morrisons", "asda"]),
    ("Dining", ["restaurant", "cafe", "coffee", "pret", "deliveroo", "just eat", "uber eats"]),
    ("Transport", ["tfl", "uber", "trainline", "rail", "bus", "fuel", "petrol", "shell", "bp "]),
    ("Utilities", ["electric", "gas", "water", "thames water", "octopus", "edf", "british gas"]),
    ("Entertainment", ["netflix", "spotify", "cinema", "disney", "prime video", "apple.com/bill"]),
    ("Shopping", ["amazon", "ikea", "argos", "zara", "h&m", "uniqlo"]),
    ("Health", ["pharmacy", "boots", "dentist", "gym", "puregym"]),
    ("Insurance", ["insurance", "aviva", "admiral"]),
]


def normalize_merchant(description):
    text = str(description).lower()
    text = re.sub(r"\b\d+\b", " ", text)
    text = re.sub(r"[^a-z\s&]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:80]


def categorise_transaction(description, amount):
    text = str(description).lower()
    if amount > 0:
        return "Income"

    for category, keywords in CATEGORY_RULES:
        if category == "Income":
            continue
        if any(keyword in text for keyword in keywords):
            return category

    return "Other"


def clean_transactions(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as exc:
        raise ValueError("Could not read the CSV file.") from exc

    required = {"date", "description", "amount"}
    normalised_columns = {str(c).strip().lower(): c for c in df.columns}

    if not required.issubset(normalised_columns):
        raise ValueError("CSV must contain date, description, and amount columns.")

    df = df.rename(columns={
        normalised_columns["date"]: "date",
        normalised_columns["description"]: "description",
        normalised_columns["amount"]: "amount",
    })[["date", "description", "amount"]]

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["description"] = df["description"].astype(str).str.strip()

    df = df.dropna(subset=["date", "amount"])
    df = df[df["description"].ne("")]

    if df.empty:
        raise ValueError("No valid transactions were found in the CSV.")

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df["category"] = [
        categorise_transaction(description, amount)
        for description, amount in zip(df["description"], df["amount"])
    ]
    df["normalized_merchant"] = df["description"].map(normalize_merchant)

    return df


def detect_recurring(df):
    if df.empty:
        return []

    work = df.copy()
    work = work[work["amount"] < 0]
    work["date"] = pd.to_datetime(work["date"])

    results = []
    for merchant, group in work.groupby("normalized_merchant"):
        group = group.sort_values("date")
        if len(group) < 3 or not merchant:
            continue

        gaps = group["date"].diff().dt.days.dropna()
        median_gap = gaps.median() if not gaps.empty else None
        amounts = group["amount"].abs()
        mean_amount = amounts.mean()
        variation = (amounts.std(ddof=0) / mean_amount) if mean_amount else 999

        cadence = None
        if median_gap is not None and 25 <= median_gap <= 35:
            cadence = "Monthly"
        elif median_gap is not None and 6 <= median_gap <= 8:
            cadence = "Weekly"

        if cadence and variation <= 0.15:
            results.append({
                "merchant": group.iloc[-1]["description"],
                "category": group.iloc[-1]["category"],
                "cadence": cadence,
                "average_amount": round(float(mean_amount), 2),
                "occurrences": int(len(group)),
            })

    return sorted(results, key=lambda item: (-item["occurrences"], item["merchant"].lower()))


def dataframe_to_csv_response_bytes(df):
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue().encode("utf-8")
