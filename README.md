# 🛡️ FraudShield AI: Multilayer Financial Fraud & Quishing Detection Gatekeeper
### *A Production-Grade Hybrid Graph Neural Network (JA-GNN) & Lexical ML Architecture for UPI & BharatQR Security*

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11-blue.svg)](https://www.python.org/)
[![PyTorch Geometric](https://img.shields.io/badge/PyTorch-Geometric%202.3+-orange.svg)](https://pytorch-geometric.readthedocs.io/)
[![ROC-AUC](https://img.shields.io/badge/ROC--AUC-96.51%25-brightgreen.svg)]()
[![Precision](https://img.shields.io/badge/Precision-86.05%25-success.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![Android](https://img.shields.io/badge/Platform-Android%2014%20(API%2034)-3DDC84.svg)](https://developer.android.com/)
[![Kotlin](https://img.shields.io/badge/Language-Kotlin%20%7C%20Jetpack%20Compose-7F52FF.svg)](https://kotlinlang.org/)
[![Cloud Ready](https://img.shields.io/badge/Cloud-Render%20%7C%20Railway-informational.svg)](https://render.com)

---

## 📌 Executive Summary

Digital payments across UPI, BharatQR, and dynamic web invoices have seen explosive adoption, but also a parallel surge in **camouflage money-mule rings**, **reverse-collect fraud**, and **quishing (QR-code phishing)**. Traditional signature-based or rule-based fraud detection fails against coordinated syndicates that mimic benign user behavior across shared device fingerprints, IP subnets, and transaction velocity.

**FraudShield AI** is an end-to-end, multi-layer security gatekeeper that intercepts payments and QR scans in **real time (< 180ms)**. It combines:
1. **Jump-Attentive Graph Neural Networks (JA-GNN)** to detect complex topological camouflage across transaction-entity graphs.
2. **Lexical Random Forest ML** to instantly identify malicious web domains and URL phishing.
3. **Hardware-Level Device Hard-Blacklisting** to permanently ban fraudulent entities from an infected device.
4. **A Native Android App (Jetpack Compose & CameraX)** with multi-language support (7 Indian languages), sound/haptic alerts, and automated intent routing to Google Pay, PhonePe, and Paytm.

---

## 🏛️ Multilayer Defense Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │          Scanned QR / Inbound URL            │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │      Intelligent QR Payload Router           │
                    │   (Detects: UPI URI vs. Generic Web URL)     │
                    └──────────────┬────────────────┬──────────────┘
                                   │                │
            ┌──────────────────────┘                └──────────────────────┐
            ▼                                                              ▼
 ┌──────────────────────┐                                       ┌──────────────────────┐
 │   PAYMENT PAYLOAD    │                                       │   WEB URL / LINK     │
 │  (upi://pay, apps)   │                                       │  (http, https, www)  │
 └──────────┬───────────┘                                       └──────────┬───────────┘
            │                                                              │
            ▼                                                              ▼
 ┌────────────────────────────────────────┐                     ┌────────────────────────────────────────┐
 │ LAYER 3: Core JA-GNN Inference Engine  │                     │ LAYER 0: Authoritative Domain Whitelist│
 │ • Heterogeneous Bipartite Graph        │                     │ • Instant O(1) Gov & Bank Registry     │
 │ • Relation-Aware Attention             │                     └──────────────────┬─────────────────────┘
 │ • Jump-Knowledge (JK) Node Fusion      │                                        │ (If Unknown)
 │ • WMNC & Mahalanobis Metric Distance   │                                        ▼
 │ • Continuous Probability (0.00 - 1.00) │                     ┌────────────────────────────────────────┐
 └──────────────────┬─────────────────────┘                     │ LAYER 1: Threat Intelligence Blacklist │
                    │                                           │ • PhishTank & 86k Active Threat DB     │
                    │                                           └──────────────────┬─────────────────────┘
                    │                                                              │ (If Not in Blacklist)
                    │                                                              ▼
                    │                                           ┌────────────────────────────────────────┐
                    │                                           │ LAYER 2: Lexical Random Forest ML      │
                    │                                           │ • 15 Structural & Entropy Features     │
                    │                                           │ • Sub-2ms Quishing Inference           │
                    │                                           └──────────────────┬─────────────────────┘
                    │                                                              │
                    └──────────────────────┬───────────────────────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │     Tri-State Automated Decision Engine      │
                    │  • SAFE (< 0.40): Dispatch to Browser/UPI    │
                    │  • SUSPICIOUS (0.40 - 0.74): Warning Modal   │
                    │  • FRAUD (≥ 0.74): Hard Shield Stop          │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │   Permanent Device Hard-Blacklist Engine     │
                    │  (Blocks URL/QR across entire device/system) │
                    └──────────────────────────────────────────────┘
```

---

## 📊 Real Verified Model Benchmarks

### 1. Jump-Attentive GNN (JA-GNN) — Financial Transaction Graph
- **Dataset**: 300,000 real-world financial transactions with 1,641,968 heterogeneous graph nodes across 12 targeted entity relations (Sender, Receiver, Merchant, Device, IP, Location, Sender-Device, Receiver-Device, Sender-IP, Receiver-IP, Device-IP, Sender-Receiver).
- **Validation**: 42,000 completely unseen transactions evaluated with calibrated threshold $T = 0.74$ and standard threshold $T = 0.50$.
- **Model Checkpoint**: [`results/checkpoints/best_ja_gnn_custom.pt`](results/checkpoints/best_ja_gnn_custom.pt)

| Metric | Calibrated Threshold ($T = 0.74$) | Standard Threshold ($T = 0.50$) | Evaluation Verdict |
| :--- | :---: | :---: | :--- |
| **Fraud Precision** | **86.05%** (`0.860470`) | 77.24% (`0.772404`) | **Meets & exceeds base paper target (≥ 85.0%)** |
| **ROC-AUC** | **96.51%** (`0.965080`) | **96.51%** (`0.965080`) | Exceptional discriminative ranking power |
| **PR-AUC** | **86.93%** (`0.869318`) | 86.93% (`0.869318`) | High resilience against extreme class imbalance |
| **Fraud Recall** | 65.10% (`0.650952`) | **86.19%** (`0.861905`) | Intercepts massive-scale money-mule operations |
| **Fraud F1-Score** | **74.12%** (`0.741189`) | **81.47%** (`0.814704`) | High harmonic balance between precision & recall |
| **Specificity (True Negative Rate)** | **98.14%** (`0.981373`) | 95.52% (`0.955182`) | **< 1.86% false alarm rate on legitimate transactions** |
| **Overall Accuracy** | **93.18%** (`0.931810`) | **94.12%** (`0.941190`) | Superior real-world production accuracy |

```
Confusion Matrix (42,000 Validation Transactions @ T=0.74):
┌─────────────────────────┬─────────────────────────┐
│ True Negative:  35,035  │ False Positive:     665 │
├─────────────────────────┼─────────────────────────┤
│ False Negative:  2,199  │ True Positive:    4,101 │
└─────────────────────────┴─────────────────────────┘
```

---

### 2. URL Phishing & Quishing Classifier — Lexical Random Forest
- **Dataset**: 70,000 labeled URLs (35,000 authentic PhishTank/threat samples + 35,000 verified legitimate domains).
- **Validation**: 14,000 unseen test samples (20% held-out test split).
- **Model Checkpoint**: [`results/checkpoints/url_phishing_model.joblib`](results/checkpoints/url_phishing_model.joblib)

| Metric | Measured Value | Practical Impact |
| :--- | :---: | :--- |
| **ROC-AUC** | **99.86%** (`0.9986`) | Near-perfect separation of phishing vs. safe links |
| **Overall Accuracy** | **98.50%** (`0.9850`) | Extremely reliable instant perimeter classification |
| **Phishing Precision** | **99.90%** (`0.9990`) | **Near-zero false alarms** (only 7 false positives out of 7,000) |
| **Phishing Recall** | **97.10%** (`0.9710`) | Intercepts 97.1% of zero-day phishing attacks |
| **F1-Score** | **98.48%** (`0.9848`) | Flawless harmonic balance |
| **Inference Latency** | **< 1.8 ms** | Real-time on-device evaluation speed |

```
Confusion Matrix (14,000 Unseen Test URLs):
┌─────────────────────────┬─────────────────────────┐
│ True Legitimate: 6,993  │ False Phishing:       7 │
├─────────────────────────┼─────────────────────────┤
│ False Legitimate:  203  │ True Phishing:    6,797 │
└─────────────────────────┴─────────────────────────┘
```

**Top Extracted Feature Importances**:
1. `domain_length` (18.40%)
2. `url_length` (11.84%)
3. `count_dots` (11.77%)
4. `path_length` (11.70%)
5. `count_hyphens` (11.68%)
6. `count_subdomains` (7.44%)
7. `shannon_entropy` (5.37%)
8. `count_slash` (4.96%)

---

## ⚡ Core Features & Engineering Highlights

### 1. Intelligent Payload Routing (`qr_router.py`)
- Automatically differentiates between **UPI payment strings** (`upi://pay?...`), **payment-related URLs** (links containing UPI parameters like `pa=`, `pn=`, `am=`), and **generic web URLs**.
- Payment URLs are routed directly into the **JA-GNN graph model** for multi-relation graph attribution.
- Safe generic URLs redirect seamlessly to the default mobile browser without unnecessary payment prompts.

### 2. Device & System-Wide Permanent Hard-Blacklist (`DeviceBlacklistManager.kt` + SQLite)
- When a user rejects a suspicious transaction or when the AI flags confirmed fraud, the entity is written to:
  1. The client's **hardware-backed local blacklist** (`DeviceBlacklistManager`).
  2. The server's **global audit SQLite database** (`fraud_audit.db`).
- Hard-blocked entities are intercepted immediately: the app prevents any browser launch or camera re-scan for that entity on the device.

### 3. Native Android Client (Kotlin & Jetpack Compose)
- **CameraX QR Scanner** with real-time dynamic bounding-box HUD.
- **Explainable AI Modal**: Displays risk breakdown, transaction type, confidence score, and specific risk drivers (e.g., "Mule account linked to banned cyber-fraud syndicate").
- **7 Indian Regional Languages**: English, Hindi (हिंदी), Marathi (मराठी), Tamil (தமிழ்), Telugu (తెలుగు), Gujarati (ગુજરાતી), and Bengali (বাংলা).
- **Sound & Haptics**: Distinct audio feedback and tactile vibration patterns for Safe, Warning, and Block states.
- **Dynamic Cloud URL Switcher**: Toggle between local USB adb mode and 24/7 cloud backends directly in the app settings.

### 4. Interactive Simulation & QR Test Dashboard (`test_qr_dashboard.html`)
- Bundled interactive HTML dashboard with 6 realistic test vectors:
  - Clean Sharmaji Grocery Store (Verified Merchant)
  - Legitimate Electricity Board Utility
  - Rahul Kumar Syndicate Mule Account (JA-GNN Flagged)
  - Urgent Bill Collect Request (Reverse-Collect Fraud)
  - Phishing Banking Portal (`secure-sbi-kyc-update.com`)
  - Malicious Quishing Link (`free-airpods-reward.cc`)

---

## 📁 Repository Directory Structure

```
Financial-Fraud-Detection/
│
├── android/                                 # Native Android Application
│   ├── app/src/main/java/com/jagnn/fraudshield/
│   │   ├── MainActivity.kt                  # System Intent interceptor & navigation
│   │   ├── data/api/RetrofitClient.kt       # Async HTTP client with dynamic cloud URL
│   │   ├── data/repository/
│   │   │   ├── DeviceBlacklistManager.kt    # Permanent hardware hard-blacklist engine
│   │   │   ├── FraudRepository.kt           # Backend inference bridge
│   │   │   └── PreferenceRepository.kt      # Datastore settings & language preferences
│   │   ├── ui/components/
│   │   │   ├── RiskShieldModal.kt           # Explainable AI risk dialog
│   │   │   ├── ScannerOverlay.kt            # Real-time CameraX scanner UI
│   │   │   └── ManualCheckCard.kt           # Manual URL/UPI inspector
│   │   └── utils/UPIIntentHandler.kt        # Seamless GPay/PhonePe dispatch
│   └── app/src/main/res/values-*/strings.xml # Translations (hi, mr, ta, te, gu, bn)
│
├── backend/                                 # Production FastAPI Microservice
│   ├── app.py                               # REST API server & CORS configuration
│   ├── database.py                          # SQLite audit logging & blacklist persistence
│   ├── schemas.py                           # Pydantic validation schemas
│   └── services/
│       ├── qr_router.py                     # Intelligent QR & Payment URL router
│       ├── gnn_service.py                   # PyTorch JA-GNN 2-hop graph inference
│       ├── url_service.py                   # Random Forest lexical & threat analysis
│       └── decision_engine.py               # Tri-state verdict calibrator
│
├── models/                                  # Deep Learning & ML Architectures
│   ├── ja_gnn/
│   │   ├── model.py                         # JA-GNN PyTorch implementation
│   │   ├── attention.py                     # Multi-head relation-aware attention
│   │   ├── hybrid_attention.py              # Jump-Knowledge layer fusion
│   │   └── sampler.py                       # Subgraph extraction utilities
│   └── url_detector/
│       ├── feature_extractor.py             # 15 lexical & entropy feature extractors
│       └── threat_intelligence.py           # PhishTank threat intel service
│
├── results/checkpoints/                     # Pre-trained Model Checkpoints
│   ├── best_ja_gnn_custom.pt                # Trained JA-GNN weights (11.7 MB)
│   ├── best_ja_gnn_custom_synthetic.pt      # Synthetic backup weights (11.7 MB)
│   └── url_phishing_model.joblib            # Trained Random Forest classifier (1.4 MB)
│
├── data/threat_intel/
│   └── threat_blacklist.json                # Pre-cached threat intelligence (86k+ hashes)
│
├── render.yaml                              # Render.com 1-click cloud deployment blueprint
├── Procfile                                 # Railway / Heroku deployment descriptor
├── requirements.txt                         # Cloud-optimized CPU dependencies
├── test_qr_dashboard.html                   # Interactive live QR testing dashboard
├── start_backend.bat                        # Windows auto-restarting local guardian script
├── start_backend_background.vbs             # Silent background worker script
└── stop_backend.bat                         # Clean process terminator script
```

---

## 🚀 Quickstart & Setup Guide

### 1. Local Backend Setup

#### Clone & Install Dependencies:
```bash
git clone https://github.com/sai-maker-cloud/GNN-Based-Financial-Fraud-Detection-Multilayer-Final-Year-Project-.git
cd GNN-Based-Financial-Fraud-Detection-Multilayer-Final-Year-Project-
pip install -r requirements.txt
```

#### Launch Backend Server:
```bash
# Windows 1-click runner with auto-restart guardian:
start_backend.bat

# Or direct uvicorn command:
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```
Open **`http://localhost:8000/docs`** to explore the interactive Swagger API documentation.

---

### 2. Cloud Deployment (24/7 Free on Render / Railway)

This repository includes [`render.yaml`](render.yaml) and [`Procfile`](Procfile) for zero-configuration cloud deployment:

1. Sign in to **[Render.com](https://dashboard.render.com)** with your GitHub account.
2. Click **New +** ➔ **Web Service** ➔ Select this repository.
3. Verify settings:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
4. Click **Deploy Web Service**.
5. Render will build and deploy your service, providing a permanent live HTTPS URL (e.g., `https://fraudshield-backend.onrender.com`).

---

### 3. Android App Configuration

1. Open the project in **Android Studio** (Hedgehog or newer).
2. Connect your Android device via USB with USB Debugging enabled.
3. Build and install the app on your phone.
4. **Configure Backend URL**:
   - Tap the **Settings gear** in the top-right corner of the app.
   - Enter your live Render URL: `https://your-service-name.onrender.com/` (or `http://10.0.2.2:8000/` for emulator, `http://127.0.0.1:8000/` for USB reverse).
   - Tap **Save**. The engine status card will turn **🟢 Engine: ONLINE**.

---

## 📡 REST API Specifications

### `POST /api/v1/qr/analyze`
Main Gatekeeper inference endpoint. Analyzes raw QR payloads in < 180ms.

#### Request:
```json
{
  "qr_payload": "upi://pay?pa=rahul_kumar88@ybl&pn=Rahul+Kumar&am=18500.00&cu=INR",
  "user_id": "USER_9941",
  "device_fingerprint": "DEV_SAMSUNG_S23_491"
}
```

#### Response:
```json
{
  "decision": "BLOCK",
  "risk_score": 0.89,
  "confidence": 0.94,
  "payload_type": "PAYMENT_URL",
  "summary_reason": "CRITICAL RISK: Connected to known cyber-fraud syndicate SYN_8892 (Mule Ring).",
  "model_used": "JA-GNN-Financial-Graph-v1",
  "latency_ms": 38.2,
  "client_action": {
    "action": "BLOCK",
    "show_warning_dialog": true,
    "allow_override": false,
    "target_entity": "rahul_kumar88@ybl",
    "sound_alert": "ALARM"
  }
}
```

---

## 👨‍💻 Final Year Project Details & Acknowledgments

- **Project Title**: GNN-Based Multilayer Financial Fraud & Quishing Detection System
- **Domain**: Machine Learning, Graph Neural Networks, Cyber-Physical Financial Security
- **Target Platforms**: Android Mobile OS & Cloud Microservices
- **Core Models**: Jump-Attentive GNN (PyTorch Geometric) & Lexical Random Forest (Scikit-Learn)
- **Author**: Sai Abhang ([@sai-maker-cloud](https://github.com/sai-maker-cloud))
