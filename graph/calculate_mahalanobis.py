import numpy as np
import pandas as pd
import os

CANDIDATE_FILE = "data/graphs/wmnc/wmnc_candidates.npz"
FEATURE_FILE = "data/processed/scaled/train_scaled.csv"
OUTPUT_FILE = "data/graphs/wmnc/mahalanobis_scores.npz"

print("Loading candidate pairs...")
candidates = np.load(CANDIDATE_FILE)["pairs"]

print("Candidate pairs:", len(candidates))

print("Loading scaled training features...")
features = pd.read_csv(FEATURE_FILE).values.astype(np.float32)

print("Feature shape:", features.shape)

print("Calculating covariance matrix...")

covariance = np.cov(features, rowvar=False)

print("Covariance shape:", covariance.shape)

print("Calculating inverse covariance matrix...")

inverse_covariance = np.linalg.pinv(covariance)

print("Inverse covariance calculated.")

scores = np.zeros(len(candidates), dtype=np.float32)

for index, (a, b) in enumerate(candidates):

    x = features[int(a)]
    y = features[int(b)]

    difference = x - y

    distance = np.sqrt(
        difference @ inverse_covariance @ difference
    )

    scores[index] = distance

    if index % 500000 == 0 and index > 0:
        print(
            "Processed:",
            index,
            "/",
            len(candidates)
        )

np.savez_compressed(
    OUTPUT_FILE,
    pairs=candidates,
    distances=scores
)

print("\n========== MAHALANOBIS SUMMARY ==========")
print("Pairs:", len(candidates))
print("Minimum:", scores.min())
print("Maximum:", scores.max())
print("Mean:", scores.mean())
print("Median:", np.median(scores))
print("NaN:", np.isnan(scores).sum())
print("Inf:", np.isinf(scores).sum())

print("\nSaved:")
print(OUTPUT_FILE)