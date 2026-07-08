"""
JobLens — Flask Backend API
Endpoints: search, salary prediction, skill extraction, EDA stats, trends
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
import pickle, os, json
from datetime import datetime

# Internal modules
from data_cleaning   import load_clean_data
from model_training  import predict_salary, classify_category
from nlp_pipeline    import extract_skills

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────
# Load & cache dataset on startup
# ─────────────────────────────────────────
DATA_PATH = "adzuna_jobs.csv"   # ← your CSV file name here
df_global = None

def get_df():
    global df_global
    if df_global is None:
        df_global = load_clean_data(DATA_PATH)
    return df_global


# ─────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "rows": len(get_df())})


# ─────────────────────────────────────────
# SEARCH  — location + role + category
# ─────────────────────────────────────────
@app.route("/api/search")
def search():
    df   = get_df()
    loc  = request.args.get("location", "").lower()
    role = request.args.get("role", "").lower()
    cat  = request.args.get("category", "").lower()
    
    mask = pd.Series([True] * len(df), index=df.index)
    if loc:
        mask &= (
            df["location_display"].str.lower().str.contains(loc, na=False) |
            df["location_area"].str.lower().str.contains(loc, na=False)
        )
    if role:
        mask &= (
            df["title"].str.lower().str.contains(role, na=False) |
            df["description"].str.lower().str.contains(role, na=False)
        )
    if cat:
        mask &= df["category_label"].str.lower().str.contains(cat, na=False)
    
    results = df[mask].head(50)

    return jsonify({
        "count": int(len(results)),
        "jobs":  results[[
            "job_id", "title", "company", "location_display",
            "contract_time", "contract_type",
            "salary_min", "salary_max", "salary_is_predicted",
            "category_label", "redirect_url", "created",
            "latitude", "longitude"
        ]].to_dict(orient="records")
    })

# ─────────────────────────────────────────
# SALARY PREDICTION
# ─────────────────────────────────────────
@app.route("/api/predict-salary", methods=["POST"])
def predict_salary_endpoint():
    body     = request.get_json()
    title    = body.get("title", "")
    location = body.get("location", "")
    category = body.get("category", "")
    contract = body.get("contract_time", "full_time")

    try:
        result = predict_salary(title, location, category, contract)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────
# NLP SKILL EXTRACTION
# ─────────────────────────────────────────
@app.route("/api/extract-skills", methods=["POST"])
def extract_skills_endpoint():
    body = request.get_json()
    text = body.get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400
    skills = extract_skills(text)
    return jsonify({"skills": skills})

# ────────────────────────────────────────
# JOB CATEGORY CLASSIFIER
# ─────────────────────────────────────────
@app.route("/api/classify", methods=["POST"])
def classify_endpoint():
    body  = request.get_json()
    title = body.get("title", "")
    desc  = body.get("description", "")
    try:
        result = classify_category(title, desc)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────
# EDA STATS
# ─────────────────────────────────────────
@app.route("/api/eda/stats")
def eda_stats():
    df = get_df()
    return jsonify({
        "total_postings": int(len(df)),
        "unique_companies": int(df["company"].nunique()),
        "unique_categories": int(df["category_label"].nunique()),
        "avg_salary_min": float(df["salary_min"].mean()) if not np.isnan(df["salary_min"].mean()) else 0,
        "avg_salary_max": float(df["salary_max"].mean()) if not np.isnan(df["salary_max"].mean()) else 0,
        "contract_time_dist": df["contract_time"].value_counts().to_dict(),
        "contract_type_dist": df["contract_type"].value_counts().to_dict(),
        "top_categories": df["category_label"].value_counts().head(10).to_dict(),
        "salary_predicted_pct": float(df["salary_is_predicted"].mean() * 100),
    })


# ─────────────────────────────────────────
# DEMAND TRENDS (time-series)
# ─────────────────────────────────────────
# ─────────────────────────────────────────
# DEMAND TRENDS (time-series)
# ─────────────────────────────────────────
@app.route("/api/trends")
def demand_trends():
    df = get_df()
    cat = request.args.get("category", None)

    tmp = df.copy()

    tmp["month"] = pd.to_datetime(
        tmp["created"],
        errors="coerce"
    ).dt.to_period("M").astype(str)

    if cat:
        tmp = tmp[
            tmp["category_label"].str.lower() == cat.lower()
        ]

    trend = tmp.groupby("month").size().reset_index(name="count")

    # Fix NaN / Infinity JSON issues
    trend = trend.replace(
        [np.inf, -np.inf],
        np.nan
    )

    trend = trend.fillna(0)

    return jsonify(
        trend.to_dict(orient="records")
    )
# ─────────────────────────────────────────
# GEO DATA (Heatmap Points)
# ─────────────────────────────────────────
@app.route("/api/geo")
def geo_data():
    df = get_df()

    loc = request.args.get("location", "").lower()
    limit = int(request.args.get("limit", 2000))

    # Keep only rows with coordinates
    tmp = df[
        df["latitude"].notna() &
        df["longitude"].notna()
    ].copy()

    # Optional location filter
    if loc:
        tmp = tmp[
            tmp["location_display"].str.lower().str.contains(loc, na=False) |
            tmp["location_area"].str.lower().str.contains(loc, na=False)
        ]

    # Select required columns
    sample = tmp[[
        "latitude",
        "longitude",
        "salary_max",
        "category_label"
    ]].copy()

    # Remove NaN / Infinity values
    sample = sample.replace([np.inf, -np.inf], np.nan)

    # Remove rows that would break JSON
    sample = sample.dropna(
        subset=["latitude", "longitude", "salary_max"]
    )

    # Apply limit after cleaning
    if len(sample) > limit:
        sample = sample.sample(limit)

    # Debug
    print("Geo rows returned:", len(sample))
    print("NaN salary_max:", sample["salary_max"].isna().sum())

    return jsonify(
        sample.to_dict(orient="records")
    )

# ─────────────────────────────────────────
# TOP SKILLS FROM DATASET
# ─────────────────────────────────────────
@app.route("/api/top-skills")
def top_skills():
    df  = get_df()
    cat = request.args.get("category", None)
    tmp = df.copy()
    if cat:
        tmp = tmp[tmp["category_label"].str.lower() == cat.lower()]
    # Use pre-computed NLP or re-extract
    sample_texts = tmp["description"].dropna().sample(min(500, len(tmp))).tolist()
    all_skills = []
    for t in sample_texts:
        all_skills.extend(extract_skills(t))
    from collections import Counter
    counts = Counter(all_skills).most_common(15)
    return jsonify([{"skill": k, "count": v} for k, v in counts])


# ─────────────────────────────────────────
# HIRING FORECAST
# ─────────────────────────────────────────
@app.route("/api/forecast")
def forecast():
    df = get_df()
    df["month"] = pd.to_datetime(df["created"], errors="coerce").dt.to_period("M").astype(str)
    monthly = df.groupby("month").size().reset_index(name="count").tail(12)

    # Simple linear trend forecast (3 months)
    y = monthly["count"].values
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, 1)
    future = [int(np.polyval(coeffs, len(y) + i)) for i in range(3)]

    return jsonify({
        "historical": monthly.to_dict(orient="records"),
        "forecast_months": 3,
        "forecast_values": future
    })


if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)
