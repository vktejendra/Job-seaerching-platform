# 🛰️ JobLens — Global Job Market Intelligence Platform
### B.Tech Final Year Project | Data Science + Full Stack

> AI-powered job market analysis platform built on 17,350 Adzuna global job postings.  
> Covers: Data Cleaning · EDA · Salary Prediction · NLP Skill Extraction · Geo Heatmaps · Hiring Forecasting · Job Classification.

---

## 📁 Project Structure

```
JobLens/
│
├── index.html              ← Login / Register page (frontend entry)
├── dashboard.html          ← Main dashboard with charts & search
├── style.css               ← Global dark theme styles
├── auth.js                 ← Auth logic (login/register/session)
├── dashboard.js            ← Charts, search, autocomplete, geo map
│
├── app.py                  ← Flask REST API (backend)
├── data_cleaning.py        ← Data pipeline (cleaning, feature eng.)
├── model_training.py       ← Salary predictor + Category classifier
├── nlp_pipeline.py         ← Skill extraction (TF-IDF + spaCy)
├── eda_visualisation.py    ← 10 EDA charts → static/charts/*.png
│
├── requirements.txt        ← Python packages
├── adzuna_jobs.csv         ← ← YOUR DATASET (place here)
│
└── static/
    └── charts/             ← Auto-generated EDA chart PNGs
```

---

## ⚙️ Setup in VS Code

### Step 1 — Clone / open project
Open the `JobLens/` folder in VS Code.

### Step 2 — Create virtual environment
```bash
python -m venv venv
```

Activate it:
- **Windows:**  `venv\Scripts\activate`
- **Mac/Linux:** `source venv/bin/activate`

### Step 3 — Install Python packages
```bash
pip install -r requirements.txt
```

### Step 4 — Download spaCy English model
```bash
python -m spacy download en_core_web_sm
```

### Step 5 — Place your dataset
Copy your Adzuna CSV file into the project root and name it:
```
adzuna_jobs.csv
```

---

## 🚀 Running the Project

### A) Open frontend (no server needed)
Just open `index.html` in your browser (double-click or use Live Server extension in VS Code).

For Live Server:
1. Install **Live Server** extension in VS Code
2. Right-click `index.html` → **Open with Live Server**
3. Login or Register → auto-redirects to `dashboard.html`

---

### B) Train ML models (run once)
```bash
python model_training.py adzuna_jobs.csv
```
Outputs:
- `models/salary_model.pkl`
- `models/category_model.pkl`

---

### C) Generate all EDA charts (run once)
```bash
python eda_visualisation.py adzuna_jobs.csv
```
Outputs 10 charts to `static/charts/`:
- `01_category_distribution.png`
- `02_salary_distribution.png`
- `03_demand_trend.png`
- `04_contract_mix.png`
- `05_top_skills.png`
- `06_salary_by_category.png`
- `07_geo_heatmap.png`
- `08_hiring_forecast.png`
- `09_skill_wordcloud.png`
- `10_predicted_vs_actual_salary.png`

---

### D) Start Flask backend API
```bash
python app.py
```
API runs at: `http://127.0.0.1:5000`

---

### E) Test NLP pipeline standalone
```bash
python nlp_pipeline.py adzuna_jobs.csv
```

### F) Test data cleaning standalone
```bash
python data_cleaning.py adzuna_jobs.csv
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Server + dataset status |
| GET | `/api/search?location=Sydney&role=Developer` | Search jobs |
| POST | `/api/predict-salary` | Predict salary from role/location |
| POST | `/api/extract-skills` | Extract skills from text |
| POST | `/api/classify` | Classify job into category |
| GET | `/api/eda/stats` | Global EDA statistics |
| GET | `/api/trends?category=IT+Jobs` | Time-series trend data |
| GET | `/api/geo?location=London&limit=1000` | Geo coordinates for heatmap |
| GET | `/api/top-skills?category=IT+Jobs` | Top skills by NLP |
| GET | `/api/forecast` | Hiring forecast (3-month) |

### Example: Salary Prediction (POST body)
```json
{
  "title": "Data Scientist",
  "location": "Sydney",
  "category": "IT Jobs",
  "contract_time": "full_time"
}
```

### Example: Skill Extraction (POST body)
```json
{
  "text": "We need a Python developer with TensorFlow and AWS experience..."
}
```

---

## 🧠 ML Models

| Model | Algorithm | Target | Metric |
|-------|-----------|--------|--------|
| Salary Predictor | GradientBoostingRegressor | salary_mid | MAE (£) |
| Category Classifier | RandomForest + TF-IDF | category_label | Accuracy |

Features used for salary: `title (TF-IDF)`, `category`, `contract_time`, `contract_type`, `country`, `desc_length`

---

## 📊 Data Science Components

| Module | Techniques |
|--------|-----------|
| `data_cleaning.py` | Null handling, outlier clipping, dedup, type casting, feature engineering |
| `model_training.py` | TF-IDF vectorisation, GBM regression, RF classification, train/test split |
| `nlp_pipeline.py` | Keyword taxonomy matching, spaCy NER, TF-IDF corpus ranking, co-occurrence |
| `eda_visualisation.py` | Histograms, violin plots, heatmaps, trend lines, forecasting, wordcloud |

---

## 🖥️ Frontend Features

- **Login / Register** — localStorage-based session, password strength meter
- **Smart Search** — Autocomplete for location, role, and category
- **Location Detection** — Browser geolocation + reverse geocoding
- **AI Insight Panel** — Dynamic analysis text for each search
- **5 Chart Types** — Category bar, salary distribution, trend line, contract donut, skills bar
- **Leaflet Geo Map** — Real heatmap with lat/lon from dataset
- **Job Cards** — Title, company, salary range, contract type, skill tags
- **Sidebar Navigation** — 8 sections including classify, forecast, geo

---

## 📦 Package Summary

```
flask, flask-cors          → REST API
pandas, numpy              → Data processing
scikit-learn, scipy        → ML models
spacy                      → NLP
matplotlib, seaborn        → EDA charts
wordcloud                  → Skill wordcloud
xgboost                    → Optional stronger model
gunicorn                   → Production deployment
```

---

## 👨‍🎓 Project Sections Covered

1. ✅ Data Cleaning & Preprocessing
2. ✅ Exploratory Data Analysis (EDA)
3. ✅ Salary Prediction Model (GBM)
4. ✅ Job Category Classification (RF)
5. ✅ Skill Extraction using NLP (spaCy + TF-IDF)
6. ✅ Job Demand Trend Analysis (time-series)
7. ✅ Geographic Heatmaps (Leaflet + lat/lon)
8. ✅ Hiring Forecasting (linear trend + confidence band)

---
*JobLens — Built with ❤️ for B.Tech Final Year Project*
