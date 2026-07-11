"""
JobLens — Flask Backend API
Endpoints: search, salary prediction, skill extraction, EDA stats, trends
"""

from flask import Flask, jsonify, request, send_from_directory
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
# Serve the frontend (index.html, dashboard.html, dashboard.js, auth.js,
# style.css, etc.) — this app previously only defined /api/* routes, so
# opening the site's root URL had nothing to match and returned a 404.
# All these files are expected to sit in the same folder as this app.py.
# ─────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route("/")
def serve_index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/<path:filename>")
def serve_static_files(filename):
    file_path = os.path.join(BASE_DIR, filename)
    if os.path.isfile(file_path):
        return send_from_directory(BASE_DIR, filename)
    return jsonify({"error": "Not found"}), 404

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


def _clean_nans(record: dict) -> dict:
    """Replace NaN/inf float values with None so jsonify produces valid JSON.
    Pandas can't hold None inside a float64 column (it silently reverts to
    NaN), so this must run on plain Python dicts *after* to_dict(), not on
    the DataFrame itself."""
    for k, v in record.items():
        if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
            record[k] = None
    return record


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
    loc      = request.args.get("location", "").lower()
    role     = request.args.get("role", "").lower()
    cat      = request.args.get("category", "").lower()
    contract = request.args.get("contract_time", "").lower()
    limit    = int(request.args.get("limit", 50))

    mask = pd.Series([True] * len(df), index=df.index)
    if loc:
        mask &= (
            df["location_display"].str.lower().str.contains(loc, na=False) |
            df["location_area"].str.lower().str.contains(loc, na=False)
        )
    if role:
        mask &= (
            df["title"].str.lower().str.contains(role, na=False) |
            df["company"].str.lower().str.contains(role, na=False) |
            df["description"].str.lower().str.contains(role, na=False)
        )
    if cat:
        mask &= df["category_label"].str.lower().str.contains(cat, na=False)
    if contract:
        mask &= df["contract_time"].str.lower() == contract

    results = df[mask].head(limit)

    jobs_df = results[[
        "job_id", "title", "company", "location_display",
        "contract_time", "contract_type",
        "salary_min", "salary_max", "salary_is_predicted",
        "category_label", "redirect_url", "created",
        "latitude", "longitude"
    ]].copy()

    jobs = jobs_df.to_dict(orient="records")
    jobs = [_clean_nans(job) for job in jobs]

    return jsonify({
        "count": int(len(results)),
        "jobs":  jobs
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
        raw = predict_salary(title, location, category, contract)
        # model_training.predict_salary() returns
        # predicted_salary_min/mid/max, but the dashboard reads
        # salary_min/mid/max — remap here so the frontend actually
        # receives the numbers instead of undefined -> NaN.
        result = {
            "title": raw.get("title"),
            "location": raw.get("location"),
            "category": raw.get("category"),
            "salary_min": raw.get("predicted_salary_min"),
            "salary_mid": raw.get("predicted_salary_mid"),
            "salary_max": raw.get("predicted_salary_max"),
            "currency": raw.get("currency"),
            "model_mae": raw.get("model_mae"),
        }
        # predict_salary() can still legitimately produce NaN in edge
        # cases (e.g. degenerate model output), so keep the NaN-scrubber
        # every other endpoint uses.
        result = _clean_nans(result)
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
        raw = classify_category(title, desc)
        # model_training.classify_category() returns "predicted_category",
        # but the dashboard reads data.category -- remap so the predicted
        # label actually shows up instead of undefined.
        result = {
            "category": raw.get("predicted_category"),
            "top3": raw.get("top3"),
            "accuracy": raw.get("accuracy"),
        }
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
# GEO SUMMARY (chart-based breakdown by country/city)
# ─────────────────────────────────────────
@app.route("/api/geo-summary")
def geo_summary():
    df = get_df()

    by_country = df[df["country"] != "Unknown"]["country"].value_counts().head(10)
    by_city = df[df["location_display"] != ""]["location_display"].value_counts().head(12)

    return jsonify({
        "by_country": [{"country": k, "count": int(v)} for k, v in by_country.items()],
        "by_city": [{"city": k, "count": int(v)} for k, v in by_city.items()]
    })


# ─────────────────────────────────────────
# GEO — COUNTRY INTAKE (for the map's colour-graded country bubbles)
# ─────────────────────────────────────────
_COUNTRY_META = {
    "US": {"name": "United States", "lat": 39.8, "lon": -98.6},
    "UK": {"name": "United Kingdom", "lat": 54.0, "lon": -2.5},
}

def _parse_country(area) -> str:
    """location_area is stored as a *stringified* Python list, e.g.
    "['US', 'Virginia', 'Fairfax County', 'Herndon']" — this pulls out
    just the first element (the country) instead of treating the whole
    string as one opaque value."""
    if not area or str(area) in ("nan", ""):
        return "Unknown"
    s = str(area).strip()
    try:
        if s.startswith("["):
            import ast
            parts = ast.literal_eval(s)
            return str(parts[0]).strip() if parts else "Unknown"
    except Exception:
        pass
    return s.split("›")[0].strip() if s else "Unknown"


@app.route("/api/geo-country-intake")
def geo_country_intake():
    df = get_df()
    counts = df["location_area"].apply(_parse_country).value_counts()

    results = []
    for code, count in counts.items():
        meta = _COUNTRY_META.get(code)
        if not meta:
            continue  # skip anything without known coordinates
        results.append({
            "code": code,
            "country": meta["name"],
            "lat": meta["lat"],
            "lon": meta["lon"],
            "count": int(count)
        })

    results.sort(key=lambda x: x["count"], reverse=True)
    return jsonify(results)


@app.route("/api/geo-city-intake")
def geo_city_intake():
    """Sample of real cities (not the whole dataset) for the map: top 30
    US cities + top 15 UK cities by posting count, with their average
    lat/lon."""
    df = get_df().copy()
    df["_country"] = df["location_area"].apply(_parse_country)

    valid = df[
        df["latitude"].notna() & df["longitude"].notna() &
        (df["location_display"] != "") &
        df["_country"].isin(["US", "UK"])
    ]

    grouped = (
        valid.groupby(["location_display", "_country"])
        .agg(count=("job_id", "size"), lat=("latitude", "mean"), lon=("longitude", "mean"))
        .reset_index()
    )

    us_cities = grouped[grouped["_country"] == "US"].sort_values("count", ascending=False).head(30)
    uk_cities = grouped[grouped["_country"] == "UK"].sort_values("count", ascending=False).head(15)
    combined = pd.concat([us_cities, uk_cities])

    results = [
        {
            "city": row["location_display"],
            "country": _COUNTRY_META[row["_country"]]["name"],
            "code": row["_country"],
            "lat": round(float(row["lat"]), 4),
            "lon": round(float(row["lon"]), 4),
            "count": int(row["count"])
        }
        for _, row in combined.iterrows()
    ]
    results.sort(key=lambda x: x["count"], reverse=True)
    return jsonify(results)


# ─────────────────────────────────────────
# GEO DATA (Heatmap Points)
# ─────────────────────────────────────────
@app.route("/api/geo")
def geo_data():
    df = get_df()

    loc = request.args.get("location", "").lower()
    limit = int(request.args.get("limit", 2000))

    tmp = df[
        df["latitude"].notna() &
        df["longitude"].notna()
    ].copy()

    if loc:
        tmp = tmp[
            tmp["location_display"].str.lower().str.contains(loc, na=False) |
            tmp["location_area"].str.lower().str.contains(loc, na=False)
        ]

    sample = tmp[
        ["latitude", "longitude"]
    ].copy()

    sample = sample.replace([np.inf, -np.inf], np.nan)

    sample = sample.dropna(
        subset=["latitude", "longitude"]
    )

    sample["latitude"] = sample["latitude"].round(2)
    sample["longitude"] = sample["longitude"].round(2)

    heatmap = (
        sample.groupby(["latitude", "longitude"])
        .size()
        .reset_index(name="job_count")
    )

    if len(heatmap) > limit:
        heatmap = heatmap.sample(limit, random_state=42)

    print("Heatmap Points:", len(heatmap))

    return jsonify(
        heatmap.to_dict(orient="records")
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
# TOP HIRING COMPANIES
# ─────────────────────────────────────────
@app.route("/api/top-companies")
def top_companies():
    df = get_df()
    cat = request.args.get("category", None)
    limit = int(request.args.get("limit", 10))

    tmp = df.copy()
    if cat:
        tmp = tmp[tmp["category_label"].str.lower() == cat.lower()]

    counts = (
        tmp[tmp["company"] != ""]["company"]
        .value_counts()
        .head(limit)
    )

    return jsonify([{"company": k, "count": int(v)} for k, v in counts.items()])


# ─────────────────────────────────────────
# AVERAGE SALARY BY CATEGORY
# ─────────────────────────────────────────
@app.route("/api/salary-by-category")
def salary_by_category():
    df = get_df()
    limit = int(request.args.get("limit", 10))

    tmp = df[df["salary_mid"].notna() & (df["category_label"] != "")]

    top_cats = tmp["category_label"].value_counts().head(limit).index
    avg_salary = (
        tmp[tmp["category_label"].isin(top_cats)]
        .groupby("category_label")["salary_mid"]
        .mean()
        .reindex(top_cats)
    )

    return jsonify([
        {"category": k, "avg_salary": float(v)} for k, v in avg_salary.items()
    ])


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