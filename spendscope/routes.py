import io
import sqlite3
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from flask import (
    Blueprint,
    Response,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from .db import get_db
from .services import clean_transactions, detect_recurring


bp = Blueprint("main", __name__)


def _load_transactions():
    db = get_db()
    return pd.read_sql_query(
        """
        SELECT id, date, description, amount, category, normalized_merchant
        FROM transactions
        ORDER BY date DESC, id DESC
        """,
        db,
    )


def _filtered_transactions(df):
    if df.empty:
        return df

    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    month = request.args.get("month", "").strip()

    out = df.copy()

    if query:
        mask = out["description"].str.contains(query, case=False, na=False)
        out = out[mask]

    if category:
        out = out[out["category"] == category]

    if month:
        out = out[out["date"].str.startswith(month)]

    return out


def _chart_json(df):
    if df.empty:
        return {
            "income_spending": go.Figure().to_json(),
            "categories": go.Figure().to_json(),
            "trend": go.Figure().to_json(),
        }

    work = df.copy()
    work["date"] = pd.to_datetime(work["date"])
    work["month"] = work["date"].dt.to_period("M").astype(str)
    work["income"] = work["amount"].clip(lower=0)
    work["spending"] = (-work["amount"].clip(upper=0))

    monthly = (
        work.groupby("month", as_index=False)[["income", "spending"]]
        .sum()
        .sort_values("month")
    )

    fig_income_spending = go.Figure()
    fig_income_spending.add_bar(
        x=monthly["month"],
        y=monthly["income"],
        name="Income",
    )
    fig_income_spending.add_bar(
        x=monthly["month"],
        y=monthly["spending"],
        name="Spending",
    )
    fig_income_spending.update_layout(
        barmode="group",
        title="Monthly Income vs Spending",
        margin=dict(l=30, r=20, t=55, b=35),
        legend=dict(orientation="h"),
    )

    spending_df = work[work["amount"] < 0].copy()
    by_category = (
        spending_df.assign(spending=-spending_df["amount"])
        .groupby("category", as_index=False)["spending"]
        .sum()
        .sort_values("spending", ascending=False)
    )

    fig_categories = px.pie(
        by_category,
        names="category",
        values="spending",
        hole=0.5,
        title="Spending by Category",
    )
    fig_categories.update_layout(margin=dict(l=20, r=20, t=55, b=20))

    fig_trend = px.line(
        monthly,
        x="month",
        y="spending",
        markers=True,
        title="Monthly Spending Trend",
    )
    fig_trend.update_layout(
        xaxis_title="Month",
        yaxis_title="Spending",
        margin=dict(l=30, r=20, t=55, b=35),
    )

    return {
        "income_spending": fig_income_spending.to_json(),
        "categories": fig_categories.to_json(),
        "trend": fig_trend.to_json(),
    }


def _budget_status(df):
    db = get_db()
    budgets = pd.read_sql_query(
        "SELECT category, monthly_limit FROM budgets ORDER BY category",
        db,
    )

    if budgets.empty:
        return []

    current_month = date.today().strftime("%Y-%m")
    month_df = df[df["date"].str.startswith(current_month)] if not df.empty else df

    spending = {}
    if not month_df.empty:
        debit_df = month_df[month_df["amount"] < 0].copy()
        if not debit_df.empty:
            debit_df["spent"] = -debit_df["amount"]
            spending = debit_df.groupby("category")["spent"].sum().to_dict()

    statuses = []
    for _, row in budgets.iterrows():
        category = row["category"]
        limit = float(row["monthly_limit"])
        spent = float(spending.get(category, 0))
        pct = (spent / limit * 100) if limit else 0

        if limit and spent >= limit:
            level = "danger"
            label = "Over budget"
        elif limit and pct >= 80:
            level = "warning"
            label = "Near limit"
        else:
            level = "success"
            label = "On track"

        statuses.append({
            "category": category,
            "limit": limit,
            "spent": spent,
            "pct": min(pct, 100),
            "raw_pct": pct,
            "level": level,
            "label": label,
        })

    return statuses


@bp.route("/")
def dashboard():
    df = _load_transactions()
    filtered = _filtered_transactions(df)

    income = float(df.loc[df["amount"] > 0, "amount"].sum()) if not df.empty else 0
    spending = float(-df.loc[df["amount"] < 0, "amount"].sum()) if not df.empty else 0
    balance = income - spending

    categories = sorted(df["category"].dropna().unique().tolist()) if not df.empty else []
    recurring = detect_recurring(df)
    charts = _chart_json(df)
    budgets = _budget_status(df)

    return render_template(
        "dashboard.html",
        income=income,
        spending=spending,
        balance=balance,
        transaction_count=len(df),
        transactions=filtered.to_dict("records"),
        categories=categories,
        recurring=recurring,
        budgets=budgets,
        charts=charts,
        query=request.args.get("q", ""),
        selected_category=request.args.get("category", ""),
        selected_month=request.args.get("month", ""),
    )


@bp.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Choose a CSV file first.", "danger")
            return redirect(url_for("main.upload"))

        if not file.filename.lower().endswith(".csv"):
            flash("Please upload a .csv file.", "danger")
            return redirect(url_for("main.upload"))

        try:
            df = clean_transactions(file)
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("main.upload"))

        db = get_db()
        rows = [
            (
                row.date,
                row.description,
                float(row.amount),
                row.category,
                row.normalized_merchant,
            )
            for row in df.itertuples(index=False)
        ]
        db.executemany(
            """
            INSERT INTO transactions
            (date, description, amount, category, normalized_merchant)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        db.commit()

        flash(f"Imported {len(rows)} transactions.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("upload.html")


@bp.route("/budgets", methods=["POST"])
def update_budgets():
    db = get_db()

    for key, value in request.form.items():
        if not key.startswith("budget_"):
            continue

        category = key.replace("budget_", "", 1)
        try:
            limit = max(float(value), 0)
        except ValueError:
            continue

        db.execute(
            """
            INSERT INTO budgets(category, monthly_limit)
            VALUES (?, ?)
            ON CONFLICT(category)
            DO UPDATE SET monthly_limit = excluded.monthly_limit
            """,
            (category, limit),
        )

    db.commit()
    flash("Budget limits updated.", "success")
    return redirect(url_for("main.dashboard"))


@bp.route("/export")
def export():
    df = _load_transactions()
    if not df.empty:
        df = df.drop(columns=["normalized_merchant"], errors="ignore")

    csv_text = df.to_csv(index=False)

    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=spendscope_cleaned.csv"},
    )


@bp.route("/reset", methods=["POST"])
def reset():
    db = get_db()
    db.execute("DELETE FROM transactions")
    db.commit()
    flash("All imported transactions were deleted.", "success")
    return redirect(url_for("main.dashboard"))
