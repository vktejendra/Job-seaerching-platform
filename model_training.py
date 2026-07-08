"""
JobLens — Model Training
1. Salary Prediction      → GradientBoostingRegressor
2. Job Category Classifier → RandomForest on TF-IDF
Saves trained models to /models directory.
Run standalone to train:  python model_training.py <csv_path>
"""

import os, pickle, logging
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, accuracy_score
from scipy.sparse import hstack

from data_cleaning import load_clean_data

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

# Model artefact paths
SALARY_MODEL_PATH   = os.path.join(MODEL_DIR, "salary_model.pkl")
CATEGORY_MODEL_PATH = os.path.join(MODEL_DIR, "category_model.pkl")
ENCODERS_PATH       = os.path.join(MODEL_DIR, "encoders.pkl")
SKILLS_MODEL_PATH = os.path.join(MODEL_DIR, "skills_extractor.pkl")
TFIDF_PATH = os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl")
LABEL_ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")
GEO_MODEL_PATH = os.path.join(MODEL_DIR, "geo_model.pkl")


# ─────────────────────────────────────────
# SALARY PREDICTION MODEL
# ─────────────────────────────────────────
def train_salary_model(df: pd.DataFrame):
    log.info("Training salary prediction model...")

    # Filter rows with valid salary
    valid = df[df["salary_mid"].notna() & df["title"].notna()].copy()
    log.info(f"Valid salary rows: {len(valid)}")

    # Encode categoricals
    le_cat  = LabelEncoder()
    le_ct   = LabelEncoder()
    le_ctype= LabelEncoder()
    le_loc  = LabelEncoder()

    valid["cat_enc"]    = le_cat.fit_transform(valid["category_label"].fillna("unknown"))
    valid["ct_enc"]     = le_ct.fit_transform(valid["contract_time"].fillna("unknown"))
    valid["ctype_enc"]  = le_ctype.fit_transform(valid["contract_type"].fillna("unknown"))
    valid["loc_code"]   = le_loc.fit_transform(valid["country"].fillna("unknown"))

    # TF-IDF on title (captures role semantics)
    tfidf = TfidfVectorizer(max_features=500, stop_words="english", ngram_range=(1,2))
    title_feats = tfidf.fit_transform(valid["title"].fillna(""))

    # Numeric features
    num_cols = ["cat_enc", "ct_enc", "ctype_enc", "loc_code",
                "desc_length", "salary_is_predicted"]
    num_feats = valid[num_cols].fillna(0).values

    X = hstack([title_feats, num_feats])
    y = valid["salary_mid"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = GradientBoostingRegressor(
        n_estimators=200, max_depth=5, learning_rate=0.08,
        min_samples_split=10, subsample=0.8, random_state=42
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    log.info(f"Salary Model MAE: £{mae:,.0f}")

    # Save
    artefacts = {
        "model": model, "tfidf": tfidf,
        "le_cat": le_cat, "le_ct": le_ct,
        "le_ctype": le_ctype, "le_loc": le_loc,
        "num_cols": num_cols, "mae": mae
    }
    with open(SALARY_MODEL_PATH, "wb") as f:
        pickle.dump(artefacts, f)
    log.info(f"Saved salary model → {SALARY_MODEL_PATH}")
    return artefacts, mae


# ─────────────────────────────────────────
# JOB CATEGORY CLASSIFIER
# ─────────────────────────────────────────
def train_category_classifier(df: pd.DataFrame):
    log.info("Training job category classifier...")

    valid = df[df["category_label"].notna() & df["title"].notna()].copy()
    valid = valid[valid["category_label"] != ""]
    log.info(f"Valid category rows: {len(valid)}")

    le = LabelEncoder()
    y  = le.fit_transform(valid["category_label"])

    with open(LABEL_ENCODER_PATH, "wb") as f:
      pickle.dump(le, f)

    # Combine title + partial description for features
    text = (valid["title"].fillna("") + " " + valid["description"].fillna("").str[:300])

    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=2000, stop_words="english", ngram_range=(1,2))),
        ("clf",   RandomForestClassifier(n_estimators=150, max_depth=20, random_state=42, n_jobs=-1))
    ])

    X_train, X_test, y_train, y_test = train_test_split(text, y, test_size=0.2, random_state=42)
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    log.info(f"Category Classifier Accuracy: {acc:.3f}")

    artefacts = {"pipeline": pipe, "le": le, "accuracy": acc}
    with open(CATEGORY_MODEL_PATH, "wb") as f:
        pickle.dump(artefacts, f)
    log.info(f"Saved category model → {CATEGORY_MODEL_PATH}")
    return artefacts, acc


# ─────────────────────────────────────────
# INFERENCE FUNCTIONS (called by Flask API)
# ─────────────────────────────────────────
_salary_art  = None
_category_art = None

def _load_salary_model():
    global _salary_art
    if _salary_art is None:
        if not os.path.exists(SALARY_MODEL_PATH):
            raise FileNotFoundError("Salary model not trained. Run: python model_training.py <csv>")
        with open(SALARY_MODEL_PATH, "rb") as f:
            _salary_art = pickle.load(f)
    return _salary_art

def _load_category_model():
    global _category_art
    if _category_art is None:
        if not os.path.exists(CATEGORY_MODEL_PATH):
            raise FileNotFoundError("Category model not trained. Run: python model_training.py <csv>")
        with open(CATEGORY_MODEL_PATH, "rb") as f:
            _category_art = pickle.load(f)
    return _category_art


def predict_salary(title: str, location: str, category: str, contract_time: str) -> dict:
    art   = _load_salary_model()
    tfidf = art["tfidf"]
    model = art["model"]

    # Encode input (use transform; unseen labels → 0)
    def safe_encode(le, val):
        classes = list(le.classes_)
        return classes.index(val) if val in classes else 0

    cat_enc   = safe_encode(art["le_cat"],   category)
    ct_enc    = safe_encode(art["le_ct"],    contract_time)
    ctype_enc = 0  # contract_type not available in live input
    loc_enc   = safe_encode(art["le_loc"],   location)

    title_feat = tfidf.transform([title])
    num_feat   = np.array([[cat_enc, ct_enc, ctype_enc, loc_enc, 0, 0]])

    X = hstack([title_feat, num_feat])
    pred_mid = float(model.predict(X)[0])
    pred_min = pred_mid * 0.85
    pred_max = pred_mid * 1.15

    return {
        "title": title, "location": location, "category": category,
        "predicted_salary_min": round(pred_min, 2),
        "predicted_salary_mid": round(pred_mid, 2),
        "predicted_salary_max": round(pred_max, 2),
        "currency": "GBP",
        "model_mae": art.get("mae", "N/A")
    }

def train_geo_model(df):
    log.info("Creating Geo Model...")

    geo_data = {}

    if "country" in df.columns:
        geo_data = df["country"].value_counts().to_dict()

    with open(GEO_MODEL_PATH, "wb") as f:
        pickle.dump(geo_data, f)

    log.info("Saved geo_model.pkl")

def classify_category(title: str, description: str) -> dict:
    art  = _load_category_model()
    pipe = art["pipeline"]
    le   = art["le"]

    text  = title + " " + description[:300]
    pred  = pipe.predict([text])[0]
    probs = pipe.predict_proba([text])[0]
    top3_idx   = probs.argsort()[::-1][:3]
    top3       = [(le.classes_[i], round(float(probs[i]), 4)) for i in top3_idx]

    return {
        "predicted_category": le.inverse_transform([pred])[0],
        "top3": [{"category": c, "probability": p} for c, p in top3],
        "accuracy": art.get("accuracy", "N/A")
    }

def train_skills_extractor(df):
    log.info("Training Skills Extractor...")

    tfidf = TfidfVectorizer(
        max_features=1000,
        stop_words="english",
        ngram_range=(1,2)
    )

    text = df["description"].fillna("")
    tfidf.fit(text)

    with open(SKILLS_MODEL_PATH, "wb") as f:
        pickle.dump(tfidf, f)

    with open(TFIDF_PATH, "wb") as f:
        pickle.dump(tfidf, f)

    log.info("Saved skills_extractor.pkl")
    log.info("Saved tfidf_vectorizer.pkl")

# ─────────────────────────────────────────
# STANDALONE TRAINING ENTRY POINT
# ─────────────────────────────────────────
if __name__ == "__main__":
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "adzuna_jobs.csv"

    log.info("=== JobLens Model Training Pipeline ===")
    df = load_clean_data(csv_path)

    _, salary_mae = train_salary_model(df)
    _, cat_acc = train_category_classifier(df)

    train_skills_extractor(df)
    train_geo_model(df)

    print("\n╔══════════════════════════════════╗")
    print("║  TRAINING COMPLETE               ║")
    print(f"║  Salary MAE    : £{salary_mae:>8,.0f}       ║")
    print(f"║  Category Acc  : {cat_acc:.3f}               ║")
    print("╚══════════════════════════════════╝")