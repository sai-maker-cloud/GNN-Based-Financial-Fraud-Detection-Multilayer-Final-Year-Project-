import os
import sys
import random

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report
)
import joblib

from models.url_detector.feature_extractor import extract_features_vector, FEATURE_NAMES

# Seed for reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT_DIR, "data", "raw", "phishing_urls.csv")
CHECKPOINT_DIR = os.path.join(ROOT_DIR, "results", "checkpoints")
CHECKPOINT_PATH = os.path.join(CHECKPOINT_DIR, "url_phishing_model.joblib")

# Curated list of verified legitimate domains across banking, government, global tech, and e-commerce
LEGITIMATE_DOMAINS = [
    # Indian Banks & UPI Ecosystem
    "onlinesbi.sbi", "sbi.co.in", "hdfcbank.com", "icicibank.com", "axisbank.com",
    "kotak.com", "pnbindia.in", "bankofbaroda.in", "canarabank.com", "unionbankofindia.co.in",
    "paytm.com", "phonepe.com", "bhimupi.org.in", "npci.org.in", "rbi.org.in", "cred.club",
    "razorpay.com", "cashfree.com", "billdesk.io", "ccavenue.com",
    
    # Government & Utility Services
    "uidai.gov.in", "incometax.gov.in", "parivahan.gov.in", "epfindia.gov.in",
    "irctc.co.in", "mahadiscom.in", "bescom.karnataka.gov.in", "tnebnet.org",
    "passportindia.gov.in", "digilocker.gov.in", "india.gov.in",
    
    # E-Commerce & Everyday Services
    "amazon.in", "amazon.com", "flipkart.com", "myntra.com", "ajio.com",
    "swiggy.com", "zomato.com", "makemytrip.com", "bookmyshow.com", "bigbasket.com",
    "blinkit.com", "zeptonow.com", "tatacliq.com", "jiomart.com",
    
    # Global Tech, Education & Media
    "google.com", "youtube.com", "microsoft.com", "github.com", "apple.com",
    "wikipedia.org", "linkedin.com", "stackoverflow.com", "twitter.com", "reddit.com",
    "netflix.com", "spotify.com", "medium.com", "cloudflare.com", "adobe.com",
    "zoom.us", "dropbox.com", "salesforce.com", "slack.com", "whatsapp.com",
    "coursera.org", "edx.org", "khanacademy.org", "mit.edu", "stanford.edu",
    "nature.com", "ieee.org", "acm.org", "springer.com", "researchgate.net",
    "bbc.com", "cnn.com", "reuters.com", "thehindu.com", "indiatimes.com"
]

COMMON_SUBDOMAINS = ["www", "portal", "secure", "online", "api", "auth", "m", "app", "pay", "help", "support"]
COMMON_PATHS = [
    "", "/", "/login", "/home", "/about", "/contact", "/terms", "/privacy",
    "/services/banking", "/dashboard", "/account/overview", "/products/view",
    "/checkout/payment", "/faq", "/support/help-center", "/news/article/2026",
    "/download/app", "/user/profile", "/bill/pay", "/search?q=statement"
]


def generate_legitimate_urls(target_count: int = 35000) -> list:
    """Generates a diverse, realistic corpus of verified legitimate URLs with standard paths and parameters."""
    print(f"Generating {target_count:,} realistic legitimate URLs from trusted domains...")
    urls = []
    schemes = ["https://", "https://", "https://", "http://"]  # 75% https, 25% http
    
    for _ in range(target_count):
        scheme = random.choice(schemes)
        domain = random.choice(LEGITIMATE_DOMAINS)
        
        # Optionally add a subdomain
        if random.random() < 0.4:
            sub = random.choice(COMMON_SUBDOMAINS)
            full_host = f"{sub}.{domain}"
        else:
            full_host = domain
            
        path = random.choice(COMMON_PATHS)
        if random.random() < 0.2 and path and not path.endswith("?"):
            path += f"?id={random.randint(100, 99999)}&lang=en"
            
        urls.append(f"{scheme}{full_host}{path}")
        
    return urls


def load_phishing_urls(target_count: int = 35000) -> list:
    """Loads a representative sample of verified phishing URLs from data/raw/phishing_urls.csv."""
    print(f"Loading real-world phishing URLs from {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH, usecols=["url"], nrows=target_count * 2)
    urls = df["url"].dropna().unique().tolist()
    if len(urls) > target_count:
        urls = random.sample(urls, target_count)
    print(f"Successfully loaded {len(urls):,} authentic phishing URLs.")
    return urls


def main():
    print("=" * 70)
    print("      TRAINING URL PHISHING & QUISHING CLASSIFIER")
    print("=" * 70)
    
    # 1. Dataset Construction
    target_per_class = 35000
    phishing_urls = load_phishing_urls(target_count=target_per_class)
    legit_urls = generate_legitimate_urls(target_count=len(phishing_urls))
    
    all_urls = phishing_urls + legit_urls
    all_labels = [1] * len(phishing_urls) + [0] * len(legit_urls)
    
    print(f"\nTotal Dataset Size: {len(all_urls):,} URLs ({len(phishing_urls):,} Phishing + {len(legit_urls):,} Legitimate)")
    
    # 2. Feature Extraction
    print(f"Extracting {len(FEATURE_NAMES)} lexical & entropy features per URL...")
    X = np.zeros((len(all_urls), len(FEATURE_NAMES)), dtype=np.float32)
    y = np.array(all_labels, dtype=np.int64)
    
    for i, u in enumerate(all_urls):
        X[i] = extract_features_vector(u)
        if (i + 1) % 15000 == 0 or (i + 1) == len(all_urls):
            print(f"  Processed {i + 1:,} / {len(all_urls):,} URLs ({(i + 1) / len(all_urls) * 100:.1f}%)")
            
    # 3. Train / Test Split (80% Train, 20% Unseen Test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_SEED, stratify=y
    )
    print(f"\nTrain set: {len(X_train):,} samples | Test set: {len(X_test):,} unseen samples")
    
    # 4. Model Training
    print("\nTraining Random Forest Ensemble (100 trees, max_depth=15)...")
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        class_weight="balanced",
        n_jobs=-1,
        random_state=RANDOM_SEED
    )
    clf.fit(X_train, y_train)
    print("Model training completed successfully!")
    
    # 5. Evaluation on Unseen Test Data
    print("\nEvaluating on 20% Unseen Test Set...")
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred)
    
    print("\n" + "=" * 55)
    print("        URL PHISHING MODEL EVALUATION REPORT")
    print("=" * 55)
    print(f"Overall Accuracy:  {acc * 100:.2f}% ({acc:.4f})")
    print(f"Phishing Precision:{prec * 100:.2f}% ({prec:.4f})")
    print(f"Phishing Recall:   {rec * 100:.2f}% ({rec:.4f})")
    print(f"F1-Score:          {f1 * 100:.2f}% ({f1:.4f})")
    print(f"ROC-AUC:           {auc * 100:.2f}% ({auc:.4f})")
    print("\nConfusion Matrix:")
    print(f"  True Legitimate:  {cm[0][0]:,} | False Phishing: {cm[0][1]:,}")
    print(f"  False Legitimate: {cm[1][0]:,} | True Phishing:  {cm[1][1]:,}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Legitimate", "Phishing"]))
    
    # Top Feature Importances
    importances = clf.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    print("Top Feature Importances:")
    for rank, idx in enumerate(sorted_idx[:8], 1):
        print(f"  {rank}. {FEATURE_NAMES[idx]:<24} {importances[idx] * 100:.2f}%")
        
    # 6. Save Checkpoint
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    pipeline_artifact = {
        "model": clf,
        "feature_names": FEATURE_NAMES,
        "metrics": {
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1": float(f1),
            "roc_auc": float(auc)
        }
    }
    joblib.dump(pipeline_artifact, CHECKPOINT_PATH, compress=3)
    file_size_mb = os.path.getsize(CHECKPOINT_PATH) / (1024 * 1024)
    print(f"\n[OK] Model successfully serialized to: {CHECKPOINT_PATH}")
    print(f"     Artifact size: {file_size_mb:.2f} MB")
    print("=" * 70)


if __name__ == "__main__":
    main()
