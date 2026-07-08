"""
JobLens — Exploratory Data Analysis & Visualisation
Generates all charts as PNG files into /static/charts/
Run: python eda_visualisation.py <csv_path>
"""

import os, logging
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")          # headless rendering
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from wordcloud import WordCloud

from data_cleaning import load_clean_data
from nlp_pipeline  import rank_skills_tfidf

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join("static", "charts")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Unified dark theme ──────────────────────────────
BG      = "#07080f"
CARD    = "#0e1028"
ACCENT  = "#6c63ff"
ACCENT2 = "#00e5ff"
GREEN   = "#00c896"
ORANGE  = "#ffb347"
RED     = "#ff6b6b"
TEXT    = "#f0f0ff"
MUTED   = "#8b8ba7"
GRID    = "#1a1b2e"

def _style(fig, ax, title="", xlabel="", ylabel=""):
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(CARD)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.xaxis.label.set_color(MUTED)
    ax.yaxis.label.set_color(MUTED)
    ax.title.set_color(TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    ax.grid(color=GRID, linewidth=0.5, linestyle="--", alpha=0.7)
    if title:   ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    if xlabel:  ax.set_xlabel(xlabel, fontsize=10)
    if ylabel:  ax.set_ylabel(ylabel, fontsize=10)

def save(fig, name):
    path = os.path.join(OUTPUT_DIR, f"{name}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    log.info(f"Saved: {path}")
    return path


# ─────────────────────────────────────────
# 1. CATEGORY DISTRIBUTION (bar)
# ─────────────────────────────────────────
def plot_category_distribution(df: pd.DataFrame):
    counts = df["category_label"].value_counts().head(12)
    colors = plt.cm.plasma(np.linspace(0.2, 0.9, len(counts)))

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.barh(counts.index[::-1], counts.values[::-1], color=colors[::-1], height=0.6)
    for bar, val in zip(bars, counts.values[::-1]):
        ax.text(bar.get_width() + 50, bar.get_y() + bar.get_height()/2,
                f"{val:,}", va="center", ha="left", color=MUTED, fontsize=9)
    _style(fig, ax, "Job Postings by Category", "Number of Postings", "")
    ax.grid(axis="y", visible=False)
    return save(fig, "01_category_distribution")


# ─────────────────────────────────────────
# 2. SALARY DISTRIBUTION (histogram)
# ─────────────────────────────────────────
def plot_salary_distribution(df: pd.DataFrame):
    sal = df["salary_mid"].dropna()
    sal = sal[sal.between(10_000, 300_000)]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor(BG)

    # Histogram
    ax1 = axes[0]
    ax1.hist(sal, bins=50, color=ACCENT, alpha=0.8, edgecolor="none")
    ax1.axvline(sal.median(), color=ACCENT2, linestyle="--", linewidth=1.5, label=f"Median: £{sal.median():,.0f}")
    ax1.axvline(sal.mean(),   color=ORANGE,  linestyle="--", linewidth=1.5, label=f"Mean: £{sal.mean():,.0f}")
    ax1.legend(facecolor=CARD, edgecolor=GRID, labelcolor=TEXT, fontsize=9)
    _style(fig, ax1, "Salary Distribution (mid-point)", "Salary (£)", "Count")
    ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"£{x/1000:.0f}K"))

    # Box plot by contract type
    ax2 = axes[1]
    ax2.set_facecolor(CARD)
    tmp = df[["contract_time", "salary_mid"]].dropna()
    tmp = tmp[tmp["salary_mid"].between(10_000, 300_000)]
    groups = [g["salary_mid"].values for _, g in tmp.groupby("contract_time")]
    labels = [k for k, _ in tmp.groupby("contract_time")]
    bp = ax2.boxplot(groups, labels=labels, patch_artist=True, notch=True,
                     medianprops=dict(color=ACCENT2, linewidth=2))
    clrs = [ACCENT, GREEN, ORANGE, RED, MUTED]
    for patch, c in zip(bp["boxes"], clrs):
        patch.set_facecolor(c); patch.set_alpha(0.6)
    _style(fig, ax2, "Salary by Contract Type", "Contract Type", "Salary (£)")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"£{x/1000:.0f}K"))
    ax2.tick_params(axis="x", rotation=15)

    fig.tight_layout(pad=3)
    return save(fig, "02_salary_distribution")


# ─────────────────────────────────────────
# 3. POSTING TREND OVER TIME (line)
# ─────────────────────────────────────────
def plot_demand_trend(df: pd.DataFrame):
    tmp = df.copy()
    tmp["month"] = pd.to_datetime(tmp["created"], errors="coerce").dt.to_period("M")
    monthly = tmp.groupby("month").size().reset_index(name="count")
    monthly["month_str"] = monthly["month"].astype(str)

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.fill_between(monthly["month_str"], monthly["count"],
                    alpha=0.15, color=ACCENT)
    ax.plot(monthly["month_str"], monthly["count"],
            color=ACCENT, linewidth=2.5, marker="o", markersize=4)

    # Rolling average
    monthly["rolling"] = monthly["count"].rolling(3, min_periods=1).mean()
    ax.plot(monthly["month_str"], monthly["rolling"],
            color=ACCENT2, linewidth=1.5, linestyle="--", label="3-mo avg")

    tick_step = max(1, len(monthly) // 12)
    ax.set_xticks(range(0, len(monthly), tick_step))
    ax.set_xticklabels(monthly["month_str"].iloc[::tick_step], rotation=45, ha="right")
    ax.legend(facecolor=CARD, edgecolor=GRID, labelcolor=TEXT)
    _style(fig, ax, "Job Postings Over Time", "Month", "Number of Postings")
    return save(fig, "03_demand_trend")


# ─────────────────────────────────────────
# 4. CONTRACT TYPE DONUT
# ─────────────────────────────────────────
def plot_contract_mix(df: pd.DataFrame):
    ct = df["contract_time"].value_counts()
    ctype = df["contract_type"].value_counts()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor(BG)

    for ax, data, title in zip(axes, [ct, ctype], ["Contract Time", "Contract Type"]):
        ax.set_facecolor(BG)
        wedge_colors = [ACCENT, ACCENT2, GREEN, ORANGE, RED, MUTED]
        wedges, texts, autotexts = ax.pie(
            data.values, labels=data.index,
            colors=wedge_colors[:len(data)],
            autopct="%1.1f%%", startangle=90,
            pctdistance=0.82, wedgeprops=dict(width=0.5, edgecolor=BG, linewidth=2)
        )
        for t in texts + autotexts:
            t.set_color(TEXT); t.set_fontsize(9)
        ax.set_title(title, color=TEXT, fontsize=12, fontweight="bold")

    return save(fig, "04_contract_mix")


# ─────────────────────────────────────────
# 5. TOP SKILLS (horizontal bar)
# ─────────────────────────────────────────
def plot_top_skills(df: pd.DataFrame):
    descriptions = df["description"].dropna().sample(min(1000, len(df))).tolist()
    skills_data  = rank_skills_tfidf(descriptions, top_n=20)
    skills_df    = pd.DataFrame(skills_data)

    if skills_df.empty:
        log.warning("No skills extracted for chart.")
        return None

    fig, ax = plt.subplots(figsize=(12, 7))
    colors = plt.cm.cool(np.linspace(0.3, 0.9, len(skills_df)))
    bars   = ax.barh(skills_df["skill"][::-1], skills_df["mention_count"][::-1],
                     color=colors[::-1], height=0.65)
    for bar, row in zip(bars, skills_df.iloc[::-1].itertuples()):
        ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2,
                f"{row.mention_count:,}", va="center", ha="left", color=MUTED, fontsize=8)

    _style(fig, ax, "Top 20 In-Demand Skills (NLP Extraction)", "Mention Count", "")
    ax.grid(axis="y", visible=False)
    return save(fig, "05_top_skills")


# ─────────────────────────────────────────
# 6. SALARY BY CATEGORY (violin)
# ─────────────────────────────────────────
def plot_salary_by_category(df: pd.DataFrame):
    tmp = df[["category_label", "salary_mid"]].dropna()
    tmp = tmp[tmp["salary_mid"].between(10_000, 250_000)]
    top_cats = tmp["category_label"].value_counts().head(8).index
    tmp = tmp[tmp["category_label"].isin(top_cats)]

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.set_facecolor(CARD)
    fig.patch.set_facecolor(BG)

    palette = {c: plt.cm.plasma(i / len(top_cats)) for i, c in enumerate(top_cats)}
    sns.violinplot(data=tmp, x="category_label", y="salary_mid",
                   palette=palette, inner="box", ax=ax, linewidth=0.8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"£{x/1000:.0f}K"))
    ax.tick_params(axis="x", rotation=30)
    _style(fig, ax, "Salary Distribution by Category", "Category", "Salary (£)")
    return save(fig, "06_salary_by_category")


# ─────────────────────────────────────────
# 7. GEO SCATTER MAP
# ─────────────────────────────────────────
def plot_geo_scatter(df: pd.DataFrame):
    geo = df[["latitude", "longitude", "salary_mid"]].dropna()
    geo = geo[geo["latitude"].between(-80, 80)]

    fig, ax = plt.subplots(figsize=(16, 8))
    ax.set_facecolor("#020310")
    fig.patch.set_facecolor("#020310")

    scatter = ax.scatter(
        geo["longitude"], geo["latitude"],
        c=geo["salary_mid"].clip(10_000, 200_000),
        cmap="plasma", s=4, alpha=0.35,
        vmin=15_000, vmax=120_000
    )
    cbar = fig.colorbar(scatter, ax=ax, fraction=0.02, pad=0.02)
    cbar.set_label("Salary (£)", color=MUTED)
    cbar.ax.yaxis.set_tick_params(color=MUTED)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=MUTED)
    cbar.ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"£{x/1000:.0f}K"))

    ax.set_xlim(-180, 180); ax.set_ylim(-80, 80)
    ax.set_title("Global Job Postings — Geo Salary Heatmap", color=TEXT, fontsize=13, fontweight="bold")
    ax.set_xlabel("Longitude", color=MUTED); ax.set_ylabel("Latitude", color=MUTED)
    ax.tick_params(colors=MUTED)
    ax.grid(color="#1a1b2e", linewidth=0.3)
    return save(fig, "07_geo_heatmap")


# ─────────────────────────────────────────
# 8. HIRING FORECAST (linear + trend)
# ─────────────────────────────────────────
def plot_hiring_forecast(df: pd.DataFrame):
    tmp = df.copy()
    tmp["month"] = pd.to_datetime(tmp["created"], errors="coerce").dt.to_period("M")
    monthly = tmp.groupby("month").size().reset_index(name="count").tail(18)
    monthly["month_str"] = monthly["month"].astype(str)

    y = monthly["count"].values
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, 1)

    future_x  = np.arange(len(y), len(y) + 4)
    future_y  = np.polyval(coeffs, future_x).astype(int)
    trend_y   = np.polyval(coeffs, x)

    all_labels = list(monthly["month_str"]) + [f"Forecast+{i+1}" for i in range(4)]
    all_y_actual = list(y) + [None]*4
    all_y_forecast = [None]*(len(y)-1) + [int(y[-1])] + list(future_y)

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(range(len(y)), y, color=ACCENT, linewidth=2.5, marker="o", markersize=4, label="Actual")
    ax.plot(range(len(y)), trend_y, color=MUTED, linewidth=1, linestyle=":", label="Trend")
    ax.plot(range(len(y)-1, len(y)+4), all_y_forecast[len(y)-1:],
            color=ACCENT2, linewidth=2, linestyle="--", marker="s", markersize=6, label="Forecast")
    ax.fill_between(range(len(y)-1, len(y)+4),
                    [v * 0.92 for v in all_y_forecast[len(y)-1:]],
                    [v * 1.08 for v in all_y_forecast[len(y)-1:]],
                    alpha=0.15, color=ACCENT2)
    ax.axvline(len(y)-1, color=ORANGE, linewidth=1, linestyle="--", alpha=0.7)

    tick_step = max(1, len(all_labels) // 10)
    ax.set_xticks(range(0, len(all_labels), tick_step))
    ax.set_xticklabels(all_labels[::tick_step], rotation=40, ha="right")
    ax.legend(facecolor=CARD, edgecolor=GRID, labelcolor=TEXT)
    _style(fig, ax, "Hiring Demand Forecast (Linear Trend)", "Month", "Postings")
    return save(fig, "08_hiring_forecast")


# ─────────────────────────────────────────
# 9. SKILL WORDCLOUD
# ─────────────────────────────────────────
def plot_skill_wordcloud(df: pd.DataFrame):
    from nlp_pipeline import extract_skills
    from collections import Counter

    sample = df["description"].dropna().sample(min(800, len(df))).tolist()
    all_skills: Counter = Counter()
    for text in sample:
        for skill in extract_skills(text):
            all_skills[skill] += 1

    if not all_skills:
        log.warning("No skills for wordcloud")
        return None

    wc = WordCloud(
        width=1200, height=600,
        background_color="#07080f",
        colormap="plasma",
        max_words=100,
        font_path=None,
        prefer_horizontal=0.8
    ).generate_from_frequencies(all_skills)

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_title("In-Demand Skill Cloud (NLP Extraction)", color=TEXT, fontsize=13, fontweight="bold", pad=12)
    return save(fig, "09_skill_wordcloud")


# ─────────────────────────────────────────
# 10. SALARY: PREDICTED vs ACTUAL (scatter)
# ─────────────────────────────────────────
def plot_predicted_vs_actual(df: pd.DataFrame):
    tmp = df[["salary_mid", "salary_is_predicted"]].dropna()
    tmp = tmp[tmp["salary_mid"].between(10_000, 250_000)]

    predicted = tmp[tmp["salary_is_predicted"] == 1]["salary_mid"]
    stated    = tmp[tmp["salary_is_predicted"] == 0]["salary_mid"]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor(BG)

    for ax, data, color, label in [
        (axes[0], stated,    ACCENT,  "Employer-Stated"),
        (axes[1], predicted, ACCENT2, "Model-Predicted")
    ]:
        ax.set_facecolor(CARD)
        ax.hist(data, bins=40, color=color, alpha=0.8, edgecolor="none")
        ax.axvline(data.median(), color=ORANGE, linestyle="--", linewidth=1.5,
                   label=f"Median: £{data.median():,.0f}")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}K"))
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"£{x/1000:.0f}K"))
        ax.legend(facecolor=CARD, edgecolor=GRID, labelcolor=TEXT, fontsize=9)
        _style(fig, ax, f"Salary Distribution — {label}", "Salary", "Count")

    fig.tight_layout(pad=3)
    return save(fig, "10_predicted_vs_actual_salary")


# ─────────────────────────────────────────
# RUN ALL CHARTS
# ─────────────────────────────────────────
def run_all(df: pd.DataFrame):
    log.info("Generating all EDA charts...")
    saved = []
    fns = [
        plot_category_distribution,
        plot_salary_distribution,
        plot_demand_trend,
        plot_contract_mix,
        plot_top_skills,
        plot_salary_by_category,
        plot_geo_scatter,
        plot_hiring_forecast,
        plot_skill_wordcloud,
        plot_predicted_vs_actual,
    ]
    for fn in fns:
        try:
            path = fn(df)
            if path:
                saved.append(path)
        except Exception as e:
            log.error(f"{fn.__name__} failed: {e}")
    log.info(f"Done. {len(saved)}/{len(fns)} charts saved to {OUTPUT_DIR}/")
    return saved


if __name__ == "__main__":
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "adzuna_jobs.csv"
    df = load_clean_data(csv_path)
    paths = run_all(df)
    print("\nCharts generated:")
    for p in paths:
        print(f"  ✓ {p}")
