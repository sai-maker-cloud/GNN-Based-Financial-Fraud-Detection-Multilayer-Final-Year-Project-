import pandas as pd
import numpy as np
import os

INPUT_FILE = "data/raw/ja_gnn_financial_transactions_300k.csv"
OUTPUT_DIR = "data/graphs/bipartite"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 12 targeted financial entity relations (eliminating 40,000-degree hub nodes)
RELATIONS = {
    0: "sender",
    1: "receiver",
    2: "merchant",
    3: "device",
    4: "ip",
    5: "location",
    6: "sender_device",
    7: "receiver_device",
    8: "sender_ip",
    9: "receiver_ip",
    10: "device_ip",
    11: "sender_receiver"
}

RELATION_COLUMNS = {
    0: ["sender_id"],
    1: ["receiver_id"],
    2: ["merchant_id"],
    3: ["device_id"],
    4: ["ip_id"],
    5: ["location_id"],
    6: ["sender_id", "device_id"],
    7: ["receiver_id", "device_id"],
    8: ["sender_id", "ip_id"],
    9: ["receiver_id", "ip_id"],
    10: ["device_id", "ip_id"],
    11: ["sender_id", "receiver_id"]
}

print("Loading dataset...")
df = pd.read_csv(INPUT_FILE)
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Only training transactions for graph construction
train_df = df[df["split"] == "train"].copy()
train_df = train_df.sort_values("timestamp").reset_index(drop=True)
num_transaction_nodes = len(train_df)
print("Training transactions:", num_transaction_nodes)

edges_source = []
edges_target = []
edges_relation = []
attribute_mapping = []

next_attribute_id = num_transaction_nodes
attribute_nodes = {}

for relation_id, relation_name in RELATIONS.items():
    columns = RELATION_COLUMNS[relation_id]
    print(f"Building relation {relation_id}: {relation_name} ({columns})...")

    if len(columns) == 1:
        col_list = train_df[columns[0]].astype(str).tolist()
        val_tuples = [(v,) for v in col_list]
    else:
        c1 = train_df[columns[0]].astype(str).tolist()
        c2 = train_df[columns[1]].astype(str).tolist()
        val_tuples = list(zip(c1, c2))

    for transaction_idx, values in enumerate(val_tuples):
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

edges_source = np.asarray(edges_source, dtype=np.int64)
edges_target = np.asarray(edges_target, dtype=np.int64)
edges_relation = np.asarray(edges_relation, dtype=np.int64)

attribute_mapping_df = pd.DataFrame(attribute_mapping)

node_ids = np.arange(next_attribute_id, dtype=np.int64)
node_types = np.where(node_ids < num_transaction_nodes, "transaction", "attribute")
node_info = pd.DataFrame({
    "node_id": node_ids,
    "node_type": node_types
})

# Save bipartite graph
np.savez_compressed(
    f"{OUTPUT_DIR}/train_edges.npz",
    source=edges_source,
    target=edges_target,
    relation=edges_relation
)

attribute_mapping_df.to_csv(f"{OUTPUT_DIR}/attribute_mapping.csv", index=False)
node_info.to_csv(f"{OUTPUT_DIR}/node_info.csv", index=False)

print("\n========== GRAPH SUMMARY ==========")
print(f"Transaction nodes: {num_transaction_nodes}")
print(f"Attribute nodes:   {len(attribute_mapping_df)}")
print(f"Total nodes:       {next_attribute_id}")
print(f"Total edges:       {len(edges_source)}")
print(f"Edges min source:  {edges_source.min()}, max: {edges_source.max()}")
print(f"Edges min target:  {edges_target.min()}, max: {edges_target.max()}")
print("Saved bipartite graph files successfully.")
