import numpy as np
from collections import defaultdict

CANDIDATE_FILE = "data/graphs/wmnc/wmnc_candidates.npz"
GRAPH_FILE = "data/graphs/bipartite/train_edges.npz"
OUTPUT_FILE = "data/graphs/wmnc/wmnc_scores.npz"

print("Loading candidates...")
candidates = np.load(CANDIDATE_FILE)["pairs"]

print("Candidate pairs:", len(candidates))

print("Loading graph...")
graph = np.load(GRAPH_FILE)

sources = graph["source"]
targets = graph["target"]

transaction_attributes = defaultdict(set)

for source, target in zip(sources, targets):
    transaction_attributes[int(source)].add(int(target))

print("Calculating transaction degrees...")

transaction_degree = {
    node: len(attributes)
    for node, attributes in transaction_attributes.items()
}

scores = np.zeros(len(candidates), dtype=np.float32)

for index, (a, b) in enumerate(candidates):

    attrs_a = transaction_attributes[int(a)]
    attrs_b = transaction_attributes[int(b)]

    common_attributes = attrs_a.intersection(attrs_b)

    if not common_attributes:
        scores[index] = 0.0
        continue

    degree_a = transaction_degree[int(a)]
    degree_b = transaction_degree[int(b)]

    denominator = min(degree_a, degree_b)

    if denominator == 0:
        scores[index] = 0.0
        continue

    scores[index] = len(common_attributes) / denominator

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
    scores=scores
)

print("\n========== WMNC SUMMARY ==========")
print("Pairs:", len(candidates))
print("Minimum:", scores.min())
print("Maximum:", scores.max())
print("Mean:", scores.mean())
print("Median:", np.median(scores))
print("Non-zero:", np.count_nonzero(scores))
print("NaN:", np.isnan(scores).sum())
print("Inf:", np.isinf(scores).sum())

print("\nSaved:")
print(OUTPUT_FILE)