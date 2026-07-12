"""
JobLens — NLP Pipeline
Skill extraction from job descriptions using:
  1. Curated tech/domain keyword matching
  2. spaCy NER + noun-chunk extraction
  3. TF-IDF keyword ranking across corpus
Run standalone: python nlp_pipeline.py <csv_path>
"""

import os, re, logging
from collections import Counter
from typing import List, Dict

import pandas as pd
import numpy as np

log = logging.getLogger(__name__)

# ─────────────────────────────────────────
# MASTER SKILL TAXONOMY
# Covers all major domains in Adzuna data
# ─────────────────────────────────────────
SKILL_TAXONOMY = {
    # Programming Languages
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "R", "Go",
    "Scala", "Kotlin", "Swift", "Ruby", "PHP", "Rust", "MATLAB", "Bash",
    "Shell", "Perl", "Haskell", "Lua",

    # Web / Frontend
    "React", "Vue", "Angular", "Next.js", "HTML", "CSS", "SASS", "Redux",
    "GraphQL", "REST", "Bootstrap", "Tailwind", "jQuery", "Svelte", "Webpack",

    # Backend / Frameworks
    "Node.js", "Django", "Flask", "FastAPI", "Spring Boot", "Express",
    "Rails", "Laravel", "ASP.NET", "Microservices", "gRPC",

    # Data & ML
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
    "TensorFlow", "PyTorch", "Keras", "scikit-learn", "XGBoost",
    "LightGBM", "CatBoost", "Pandas", "NumPy", "SciPy", "OpenCV",
    "HuggingFace", "BERT", "GPT", "Transformers", "spaCy", "NLTK",
    "Reinforcement Learning", "Feature Engineering",

    # Data Engineering
    "SQL", "NoSQL", "PostgreSQL", "MySQL", "MongoDB", "Cassandra",
    "Redis", "Elasticsearch", "Apache Spark", "Kafka", "Airflow",
    "dbt", "Snowflake", "Databricks", "Hadoop", "Hive", "Flink",
    "ETL", "Data Pipeline", "Data Warehouse", "BigQuery", "Redshift",

    # Cloud & DevOps
    "AWS", "Azure", "GCP", "Google Cloud", "Docker", "Kubernetes",
    "Terraform", "Ansible", "Jenkins", "CI/CD", "GitHub Actions",
    "CircleCI", "Helm", "Linux", "Nginx", "Prometheus", "Grafana",

    # Analytics & BI
    "Tableau", "Power BI", "Looker", "Qlik", "Excel", "SPSS",
    "SAS", "Data Analysis", "Statistics", "A/B Testing", "Regression",

    # Soft / Domain Skills
    "Agile", "Scrum", "JIRA", "Confluence", "Communication",
    "Leadership", "Project Management", "Problem Solving",
    "Stakeholder Management", "Strategic Planning",

    # Finance / Domain
    "Financial Modelling", "Risk Analysis", "Compliance",
    "Accounting", "Auditing", "FX", "Derivatives",

    # Healthcare
    "Clinical Research", "HIPAA", "EMR", "Medical Coding",
    "Nursing", "Pharmacology",
}

# Lowercase map for fast matching
_SKILL_LOWER = {s.lower(): s for s in SKILL_TAXONOMY}

# Regex to tokenise description text
_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9.#+\-]{1,25}")


# ─────────────────────────────────────────
# PRIMARY EXTRACTOR
# ─────────────────────────────────────────
def extract_skills(text: str) -> List[str]:
    """
    Extract skills from a single job description string.
    Returns list of canonical skill names (deduplicated, sorted by first appearance).
    """
    if not text or not isinstance(text, str):
        return []

    text_lower = text.lower()
    found = []
    seen  = set()

    # Pass 1 — Direct taxonomy match (single and multi-word)
    for skill_lower, skill_canonical in _SKILL_LOWER.items():
        pattern = r"\b" + re.escape(skill_lower) + r"\b"
        if re.search(pattern, text_lower):
            if skill_canonical not in seen:
                found.append(skill_canonical)
                seen.add(skill_canonical)

    # Pass 2 — spaCy NER if available (noun chunks as candidate skills)
    # Disabled by default: thinc 8.3.13's compiled maxout op is known to
    # segfault against numpy 2.4.6 on real-world text (this is what was
    # crashing `python nlp_pipeline.py` outright, with no catchable
    # Python traceback — a segfault bypasses try/except entirely). This
    # is almost certainly also the cause of the SIGSEGV worker deaths
    # ("Worker was sent code 139") app.py's own comments warn about on
    # Render, since /api/extract-skills and /api/top-skills both call
    # this function on real description text. Pass 1 above (keyword
    # taxonomy matching) is unaffected and is what the app actually
    # relies on. Set JOBLENS_USE_SPACY_NER=1 only in an environment
    # where you've confirmed numpy/thinc/blis are compatible.
    if os.environ.get("JOBLENS_USE_SPACY_NER") == "1":
        try:
            import spacy
            _nlp = _get_spacy_model()
            if _nlp:
                doc = _nlp(text[:3000])   # limit for speed
                for chunk in doc.noun_chunks:
                    chunk_text = chunk.text.strip()
                    if 2 <= len(chunk_text) <= 40 and chunk_text[0].isupper():
                        canonical = _SKILL_LOWER.get(chunk_text.lower())
                        if canonical and canonical not in seen:
                            found.append(canonical)
                            seen.add(canonical)
        except Exception:
            pass  # spaCy not installed or model missing — fall through

    return found


# ─────────────────────────────────────────
# CORPUS-LEVEL: TF-IDF SKILL RANKING
# ─────────────────────────────────────────
def rank_skills_tfidf(texts: List[str], top_n: int = 20) -> List[Dict]:
    """
    Rank skills by TF-IDF score across a corpus of descriptions.
    Returns [{skill, tfidf_score, mention_count}]
    """
    from sklearn.feature_extraction.text import TfidfVectorizer

    if not texts:
        return []

    vocab = list(SKILL_TAXONOMY)
    vocab_lower = [v.lower() for v in vocab]

    tfidf = TfidfVectorizer(
        vocabulary=vocab_lower,
        stop_words="english",
        ngram_range=(1, 2),
        dtype=np.float32
    )
    matrix = tfidf.fit_transform(
        [t.lower() if isinstance(t, str) else "" for t in texts]
    )

    # Mean TF-IDF score per skill
    mean_scores  = np.asarray(matrix.mean(axis=0)).flatten()
    doc_freq     = np.asarray((matrix > 0).sum(axis=0)).flatten()

    # Map back to canonical names
    feature_names = tfidf.get_feature_names_out()
    results = []
    for i, feat in enumerate(feature_names):
        canonical = _SKILL_LOWER.get(feat)
        if canonical and mean_scores[i] > 0:
            results.append({
                "skill": canonical,
                "tfidf_score": round(float(mean_scores[i]), 6),
                "mention_count": int(doc_freq[i])
            })

    results.sort(key=lambda x: x["tfidf_score"], reverse=True)
    return results[:top_n]


# ─────────────────────────────────────────
# SKILL CO-OCCURRENCE (for graph analysis)
# ─────────────────────────────────────────
def skill_cooccurrence(descriptions: List[str], top_n: int = 15) -> List[Dict]:
    """
    Find which skills appear together most frequently.
    Returns list of {skill_a, skill_b, count}.
    """
    from itertools import combinations

    pair_counts: Counter = Counter()
    for text in descriptions:
        skills = extract_skills(text)
        if len(skills) >= 2:
            for a, b in combinations(sorted(set(skills)), 2):
                pair_counts[(a, b)] += 1

    return [
        {"skill_a": a, "skill_b": b, "count": c}
        for (a, b), c in pair_counts.most_common(top_n)
    ]


# ─────────────────────────────────────────
# DATASET-LEVEL SKILL ANALYSIS
# ─────────────────────────────────────────
def analyse_dataset_skills(df: pd.DataFrame, category: str = None) -> Dict:
    """
    Full skill analysis on the cleaned DataFrame.
    Optionally filter by category_label.
    """
    if category:
        df = df[df["category_label"].str.lower() == category.lower()]

    descriptions = df["description"].dropna().tolist()
    log.info(f"Analysing skills in {len(descriptions)} descriptions")

    # TF-IDF ranking
    tfidf_ranked = rank_skills_tfidf(descriptions, top_n=20)

    # Frequency count
    all_skills: Counter = Counter()
    for text in descriptions:
        for skill in extract_skills(text):
            all_skills[skill] += 1

    top_skills = [{"skill": s, "count": c} for s, c in all_skills.most_common(20)]

    # Co-occurrence (sample for speed)
    sample = descriptions[:500]
    cooccur = skill_cooccurrence(sample, top_n=10)

    return {
        "total_descriptions": len(descriptions),
        "top_skills_by_frequency": top_skills,
        "top_skills_by_tfidf": tfidf_ranked,
        "skill_cooccurrence": cooccur,
    }


# ─────────────────────────────────────────
# spaCy MODEL CACHE
# ─────────────────────────────────────────
_nlp_model = None
_nlp_tried = False

def _get_spacy_model():
    global _nlp_model, _nlp_tried
    if _nlp_tried:
        return _nlp_model
    _nlp_tried = True
    try:
        import spacy
        _nlp_model = spacy.load("en_core_web_sm")
        log.info("spaCy model loaded: en_core_web_sm")
    except Exception as e:
        log.warning(f"spaCy model not available ({e}). Using keyword matching only.")
        _nlp_model = None
    return _nlp_model


# ─────────────────────────────────────────
# STANDALONE ENTRY POINT
# ─────────────────────────────────────────
if __name__ == "__main__":
    import sys, json
    from data_cleaning import load_clean_data

    csv_path = sys.argv[1] if len(sys.argv) > 1 else "adzuna_jobs.csv"
    df = load_clean_data(csv_path)

    print("\n=== JobLens NLP — Skill Analysis ===")
    results = analyse_dataset_skills(df)

    print(f"\nTotal descriptions analysed: {results['total_descriptions']}")
    print("\nTop 20 skills by frequency:")
    for item in results["top_skills_by_frequency"]:
        bar = "█" * (item["count"] // 50)
        print(f"  {item['skill']:<30} {item['count']:>5}  {bar}")

    print("\nTop 10 skill co-occurrences:")
    for pair in results["skill_cooccurrence"]:
        print(f"  {pair['skill_a']} + {pair['skill_b']} → {pair['count']} jobs")

    # Quick single-description test
    sample_desc = df["description"].dropna().iloc[0]
    extracted = extract_skills(sample_desc)
    print(f"\nSample extraction from first posting:\n  {extracted}")