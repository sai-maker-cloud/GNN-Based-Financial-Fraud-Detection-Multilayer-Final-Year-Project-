import numpy as np
import pandas as pd
import os
from collections import defaultdict

GRAPH_FILE = "data/graphs/bipartite/train_edges.npz"
OUTPUT_DIR = "data/graphs/wmnc"

MAX_NEIGHBORS = 100

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Loading graph...")

graph = np.load(GRAPH_FILE)

sources = graph["source"]
targets = graph["target"]
relations = graph["relation"]

print("Edges:", len(sources))

# --------------------------------------------------
# Build attribute -> transaction mapping
# --------------------------------------------------

attribute_transactions = defaultdict(list)

for source, target in zip(sources, targets):

    attribute_transactions[int(target)].append(
        int(source)
    )

print(
    "Unique attribute nodes:",
    len(attribute_transactions)
)

# --------------------------------------------------
# Generate candidate transaction pairs
# --------------------------------------------------

candidate_pairs = set()

processed_attributes = 0

for attribute_node, transactions in attribute_transactions.items():

    # Keep latest MAX_NEIGHBORS transactions
    if len(transactions) > MAX_NEIGHBORS:

        transactions = transactions[-MAX_NEIGHBORS:]

    n = len(transactions)

    if n < 2:
        processed_attributes += 1
        continue

    # Generate pairs sharing this attribute
    for i in range(n):

        a = transactions[i]

        for j in range(i + 1, n):

            b = transactions[j]

            if a == b:
                continue

            if a < b:
                candidate_pairs.add((a, b))
            else:
                candidate_pairs.add((b, a))

    processed_attributes += 1

    if processed_attributes % 50000 == 0:

        print(
            "Processed attributes:",
            processed_attributes,
            "| candidates:",
            len(candidate_pairs)
        )

# --------------------------------------------------
# Convert to arrays
# --------------------------------------------------

candidate_pairs = np.asarray(
    list(candidate_pairs),
    dtype=np.int64
)

print("\n========== WMNC CANDIDATES ==========")

print(
    "Candidate pairs:",
    len(candidate_pairs)
)

if len(candidate_pairs) > 0:

    print(
        "First pair:",
        candidate_pairs[0]
    )

    print(
        "Minimum node:",
        candidate_pairs.min()
    )

    print(
        "Maximum node:",
        candidate_pairs.max()
    )

    print(
        "Self loops:",
        np.sum(
            candidate_pairs[:, 0] ==
            candidate_pairs[:, 1]
        )
    )

np.savez_compressed(
    f"{OUTPUT_DIR}/wmnc_candidates.npz",
    pairs=candidate_pairs
)

print("\nSaved:")
print(
    f"{OUTPUT_DIR}/wmnc_candidates.npz"
)