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
chunk_size = 500000

for start in range(0, len(candidates), chunk_size):
    end = min(start + chunk_size, len(candidates))
    batch_pairs = candidates[start:end]
    diff = features[batch_pairs[:, 0]] - features[batch_pairs[:, 1]]
    scores[start:end] = np.sqrt(
        np.maximum(0.0, np.sum((diff @ inverse_covariance) * diff, axis=1))
    ).astype(np.float32)

    if start > 0 and start % 500000 == 0:
        print(f"Processed: {start} / {len(candidates)}")

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