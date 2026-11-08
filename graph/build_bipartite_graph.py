import pandas as pd
import numpy as np
import os

INPUT_FILE = "data/raw/ja_gnn_financial_transactions_300k.csv"
OUTPUT_DIR = "data/graphs/bipartite"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 12 shared relations
RELATIONS = {
    0: "sender",
    1: "receiver",
    2: "merchant",
    3: "device",
    4: "ip",
    5: "location",
    6: "transaction_type",
    7: "channel",
    8: "hour",
    9: "day_of_week",
    10: "receiver_merchant",
    11: "sender_merchant"
}

RELATION_COLUMNS = {
    0: ["sender_id"],
    1: ["receiver_id"],
    2: ["merchant_id"],
    3: ["device_id"],
    4: ["ip_id"],
    5: ["location_id"],
    6: ["transaction_type"],
    7: ["channel"],
    8: ["hour"],
    9: ["day_of_week"],
    10: ["receiver_id", "merchant_id"],
    11: ["sender_id", "merchant_id"]
}

print("Loading dataset...")

df = pd.read_csv(INPUT_FILE)

df["timestamp"] = pd.to_datetime(df["timestamp"])

# Only training transactions
train_df = df[df["split"] == "train"].copy()

train_df = train_df.sort_values("timestamp").reset_index(drop=True)

print("Training transactions:", len(train_df))

# Transaction nodes are the anchor nodes
num_transaction_nodes = len(train_df)

edges_source = []
edges_target = []
edges_relation = []

attribute_mapping = []

# Start attribute nodes after transaction nodes
next_attribute_id = num_transaction_nodes

# One node per (relation, attribute value)
attribute_nodes = {}

for relation_id, relation_name in RELATIONS.items():

    columns = RELATION_COLUMNS[relation_id]

    print(
        f"\nBuilding relation {relation_id}: {relation_name}"
    )

    for transaction_idx, row in train_df.iterrows():

        values = tuple(
            str(row[column])
            for column in columns
        )

        key = (relation_id, values)

        if key not in attribute_nodes:

            attribute_nodes[key] = next_attribute_id

            attribute_mapping.append({
                "attribute_node": next_attribute_id,
                "relation": relation_id,
                "relation_name": relation_name,
                "value": "|".join(values)
            })

            next_attribute_id += 1

        attribute_node = attribute_nodes[key]

        edges_source.append(transaction_idx)
        edges_target.append(attribute_node)
        edges_relation.append(relation_id)

# Convert to NumPy
edges_source = np.asarray(
    edges_source,
    dtype=np.int64
)

edges_target = np.asarray(
    edges_target,
    dtype=np.int64
)

edges_relation = np.asarray(
    edges_relation,
    dtype=np.int64
)

attribute_mapping_df = pd.DataFrame(
    attribute_mapping
)

# Node information
node_ids = np.arange(
    next_attribute_id,
    dtype=np.int64
)

node_types = np.where(
    node_ids < num_transaction_nodes,
    "transaction",
    "attribute"
)

node_info = pd.DataFrame({
    "node_id": node_ids,
    "node_type": node_types
})

# Save graph
np.savez_compressed(
    f"{OUTPUT_DIR}/train_edges.npz",
    source=edges_source,
    target=edges_target,
    relation=edges_relation
)

attribute_mapping_df.to_csv(
    f"{OUTPUT_DIR}/attribute_mapping.csv",
    index=False
)

node_info.to_csv(
    f"{OUTPUT_DIR}/node_info.csv",
    index=False
)

print("\n========== GRAPH SUMMARY ==========")

print(
    "Transaction nodes:",
    num_transaction_nodes
)

print(
    "Attribute nodes:",
    len(attribute_mapping_df)
)

print(
    "Total nodes:",
    next_attribute_id
)

print(
    "Total edges:",
    len(edges_source)
)

print("\nEdges by relation:")

for relation_id, relation_name in RELATIONS.items():

    count = np.sum(
        edges_relation == relation_id
    )

    print(
        relation_id,
        relation_name,
        ":",
        int(count)
    )

print("\nChecking graph...")

print(
    "Source min:",
    edges_source.min()
)

print(
    "Source max:",
    edges_source.max()
)

print(
    "Target min:",
    edges_target.min()
)

print(
    "Target max:",
    edges_target.max()
)

print(
    "Self loops:",
    np.sum(
        edges_source == edges_target
    )
)

print("\nSaved:")
print(
    f"{OUTPUT_DIR}/train_edges.npz"
)

print(
    f"{OUTPUT_DIR}/attribute_mapping.csv"
)

print(
    f"{OUTPUT_DIR}/node_info.csv"
)