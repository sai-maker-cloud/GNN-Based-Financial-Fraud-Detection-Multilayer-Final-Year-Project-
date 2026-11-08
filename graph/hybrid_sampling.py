import numpy as np
import os

WMNC_FILE = "data/graphs/wmnc/wmnc_scores.npz"
MAHAL_FILE = "data/graphs/wmnc/mahalanobis_scores.npz"

OUTPUT_FILE = "data/graphs/sampled/hybrid_edges.npz"

TOP_K = 10
RANDOM_K = 5
SEED = 42

np.random.seed(SEED)

print("Loading WMNC scores...")
wmnc_data = np.load(WMNC_FILE)

pairs = wmnc_data["pairs"]
wmnc_scores = wmnc_data["scores"]

print("Candidate pairs:", len(pairs))

print("Loading Mahalanobis scores...")
mahal_data = np.load(MAHAL_FILE)

mahal_scores = mahal_data["distances"]

if len(pairs) != len(mahal_scores):
    raise ValueError("WMNC and Mahalanobis pair counts do not match.")

print("Combining similarity signals...")

# Normalize Mahalanobis distance
mahal_min = mahal_scores.min()
mahal_max = mahal_scores.max()

mahal_similarity = 1.0 - (
    (mahal_scores - mahal_min) /
    (mahal_max - mahal_min + 1e-8)
)

# Normalize WMNC
wmnc_min = wmnc_scores.min()
wmnc_max = wmnc_scores.max()

wmnc_normalized = (
    (wmnc_scores - wmnc_min) /
    (wmnc_max - wmnc_min + 1e-8)
)

# Hybrid similarity
hybrid_score = (
    0.5 * wmnc_normalized +
    0.5 * mahal_similarity
)

print("Hybrid similarity calculated.")

print("Building transaction neighbor lists...")

neighbors = {}

for index, (a, b) in enumerate(pairs):

    a = int(a)
    b = int(b)

    score = float(hybrid_score[index])

    if a not in neighbors:
        neighbors[a] = []

    if b not in neighbors:
        neighbors[b] = []

    neighbors[a].append((b, score))
    neighbors[b].append((a, score))

    if index % 1000000 == 0 and index > 0:
        print(
            "Processed:",
            index,
            "/",
            len(pairs)
        )

print("Selecting top-k neighbors...")

sampled_edges = []

for node, node_neighbors in neighbors.items():

    node_neighbors.sort(
        key=lambda x: x[1],
        reverse=True
    )

    top_neighbors = node_neighbors[:TOP_K]

    remaining = node_neighbors[TOP_K:]

    random_count = min(
        RANDOM_K,
        len(remaining)
    )

    if random_count > 0:
        random_indices = np.random.choice(
            len(remaining),
            size=random_count,
            replace=False
        )

        random_neighbors = [
            remaining[i]
            for i in random_indices
        ]
    else:
        random_neighbors = []

    selected = top_neighbors + random_neighbors

    for neighbor, score in selected:
        sampled_edges.append(
            [node, neighbor, score]
        )

sampled_edges = np.array(
    sampled_edges,
    dtype=np.float32
)

os.makedirs(
    os.path.dirname(OUTPUT_FILE),
    exist_ok=True
)

np.savez_compressed(
    OUTPUT_FILE,
    source=sampled_edges[:, 0].astype(np.int64),
    target=sampled_edges[:, 1].astype(np.int64),
    score=sampled_edges[:, 2]
)

print("\n========== HYBRID SAMPLING SUMMARY ==========")

print(
    "Candidate pairs:",
    len(pairs)
)

print(
    "Sampled directed edges:",
    len(sampled_edges)
)

print(
    "Top-K:",
    TOP_K
)

print(
    "Random-K:",
    RANDOM_K
)

print(
    "Average edges per node:",
    len(sampled_edges) / len(neighbors)
)

print(
    "Score minimum:",
    sampled_edges[:, 2].min()
)

print(
    "Score maximum:",
    sampled_edges[:, 2].max()
)

print(
    "NaN:",
    np.isnan(sampled_edges[:, 2]).sum()
)

print(
    "Inf:",
    np.isinf(sampled_edges[:, 2]).sum()
)

print("\nSaved:")
print(OUTPUT_FILE)