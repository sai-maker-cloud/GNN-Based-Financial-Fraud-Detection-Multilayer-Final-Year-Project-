# Jump-Attentive Graph Neural Network (JA-GNN) for Financial Fraud Detection

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyTorch Geometric](https://img.shields.io/badge/PyTorch-Geometric-orange.svg)](https://pytorch-geometric.readthedocs.io/)
[![ROC-AUC](https://img.shields.io/badge/ROC--AUC-96.68%25-brightgreen.svg)]()
[![Precision](https://img.shields.io/badge/Precision-86.15%25-success.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Android%20Mobile%20%7C%20FastAPI-purple.svg)]()

A state-of-the-art, graph-based financial fraud detection framework designed to overcome **camouflage fraud** and **organized money-mule rings** in real-time digital transaction systems (e.g., UPI, BharatQR).

---

## 🌟 Key Architecture & Contributions

1. **Relation-Aware Attention**:
   Dynamically weights multi-hop edges across transaction networks, capturing suspicious co-occurrences of shared devices, IPs, and merchant nodes while filtering out benign background activity.

2. **Jump-Knowledge (JK) Representation**:
   Connects intermediate representations across varying graph depths to simultaneously capture fine-grained node features (amount, velocity) and global syndicate topologies.

3. **Multi-Stage Security Gatekeeper**:
   - **Perimeter Defense**: Quishing & URL Phishing ML classifier to stop malicious links embedded in QR codes.
   - **Core Financial Engine**: JA-GNN deep graph inference for transaction risk scoring.
   - **Tri-State Automated Dispatch**:
     - `SAFE` ($P < 0.40$): Frictionless Android UPI Intent dispatch to user's payment app (GPay / PhonePe / Paytm).
     - `SUSPICIOUS` ($0.40 \le P < 0.74$): Alert modal requiring explicit user confirmation.
     - `FRAUD` ($P \ge 0.74$): Hard shield stop blocking the transaction.

---

## 📊 Benchmark Evaluation Summary

Evaluated on 42,000 unseen validation transactions from a 300,000 transaction graph with 808,122 total nodes:

| Metric | Threshold $T = 0.74$ (Calibrated) | Threshold $T = 0.50$ (Standard) | Target Criteria |
| :--- | :---: | :---: | :---: |
| **ROC-AUC** | **96.68%** (`0.966840`) | 96.68% (`0.966840`) | High discriminative power |
| **PR-AUC** | **85.67%** (`0.856692`) | 85.67% (`0.856692`) | Resilient to class imbalance |
| **Fraud Precision** | **86.15%** (`0.861533`) | 65.58% (`0.655848`) | $\ge 86.00\%$ target met |
| **Fraud Recall** | **78.77%** (`0.787650`) | 88.79% (`0.887948`) | High fraud capture rate |
| **Fraud F1-Score** | **82.29%** (`0.822934`) | 75.44% (`0.754394`) | Balanced performance |
| **Overall Accuracy** | **95.33%** (`0.953286`) | 92.07% (`0.920714`) | High total correctness |

---

## 📁 Repository Directory Structure

```
Financial-Fraud-Detection/
│
├── models/                         # Model Architectures
│   ├── __init__.py                 # Top-level model exports
│   └── ja_gnn/                     # Jump-Attentive GNN package
│       ├── __init__.py             # Public exports (JAGNN, RelationAttention)
│       ├── model.py                # Main JAGNN model architecture
│       ├── attention.py            # Multi-head relation attention
│       ├── hybrid_attention.py     # Hybrid attention layer
│       └── sampler.py              # Neighborhood sampler helpers
│
├── training/                       # Production Training Pipelines
│   ├── __init__.py
│   ├── config.py                   # Hyperparameters & data paths
│   ├── graph_loader.py             # Padded PyG graph dataset loader
│   ├── neighbor_loader.py          # Bipartite neighbor loader
│   ├── relation_neighbor_loader.py # Multi-relation batch sampler
│   └── train_ja_gnn.py             # 20-epoch PyG training script
│
├── evaluation/                     # Benchmarking & Metrics
│   ├── __init__.py
│   └── evaluate_ja_gnn.py          # Comprehensive validation & metric report
│
├── graph/                          # Graph Construction & Topology Analytics
│   ├── __init__.py
│   ├── build_bipartite_graph.py    # Bipartite transaction-entity graph generator
│   ├── calculate_wmnc.py           # Weighted mutual neighbor co-occurrence
│   ├── calculate_mahalanobis.py    # Metric distance calculation
│   └── analyze_fraud_graph.py      # Graph topology analysis
│
├── preprocessing/                  # Feature Engineering & Normalization
│   ├── __init__.py
│   ├── prepare_dataset.py          # Raw transaction data preparation
│   └── scale_features.py           # Robust feature scaling & encoding
│
├── results/                        # Checkpoints & Artifacts
│   ├── checkpoints/
│   │   └── best_ja_gnn_custom.pt   # Verified trained model weights
│   └── evaluation_summary.txt      # Verified benchmark summary
│
├── scripts/                        # Utility & Analysis Tools
│   ├── threshold_analysis.py       # Decision threshold optimizer
│   └── debug/                      # Archived diagnostic scripts
│
├── data/                           # Data storage (raw, processed, graphs)
└── requirements.txt                # Python environment dependencies
```

---

## 🚀 Quickstart

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Evaluate Trained JA-GNN
```bash
python evaluation/evaluate_ja_gnn.py
```

### 3. Model Import Usage
```python
from models.ja_gnn import JAGNN

# Instantiate model architecture
model = JAGNN(
    in_channels=16,
    hidden_channels=64,
    out_channels=1,
    num_relations=3,
    num_layers=2
)
```

---

## 🔒 Multi-Model Pipeline (In Progress)
- [x] **JA-GNN Financial Graph Model** (`results/checkpoints/best_ja_gnn_custom.pt`)
- [ ] **URL Phishing / Quishing Classifier** (`models/url_detector/`)
- [ ] **FastAPI Inference Microservice** (`backend/`)
- [ ] **Native Android Scanner App** (`android/`)
