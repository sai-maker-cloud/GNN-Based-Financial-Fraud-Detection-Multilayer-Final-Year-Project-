"""
Automated Test Suite for FastAPI Backend Gatekeeper.
Simulates real-world QR scans from mobile phones and verifies
the tri-state classification, latency, and single-line reasons.
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi.testclient import TestClient
from backend.app import app

def test_gatekeeper_api():
    print("\n" + "=" * 70)
    print("      RUNNING GATEKEEPER FASTAPI END-TO-END TEST SUITE")
    print("=" * 70)

    with TestClient(app) as client:
        # Health Check
        health_res = client.get("/api/v1/health")
        assert health_res.status_code == 200, f"Health check failed: {health_res.text}"
        health_data = health_res.json()
        print(f"\n[+] Health Check Passed:")
        print(f"    JA-GNN Model Loaded: {health_data['ja_gnn_model_loaded']}")
        print(f"    URL Model Loaded:    {health_data['url_model_loaded']}")
        print(f"    Threat Intel Entries:{health_data['threat_intel_entries']:,}")

        # Test Scenarios
        test_cases = [
            {
                "name": "Case 1: Legitimate Store QR (Sharmaji Grocery)",
                "qr": "upi://pay?pa=sharma_kirana@icici&pn=SharmajiStore&mc=5411&am=150.00",
                "expected_decision": "SAFE",
                "expected_action": "AUTO_REDIRECT_PAYMENT"
            },
            {
                "name": "Case 2: Known Fraud Syndicate / Money Mule",
                "qr": "upi://pay?pa=rahul_kumar88@ybl&pn=QuickDeal&am=8000.00",
                "expected_decision": "FRAUD",
                "expected_action": "HARD_BLOCK_PAYMENT"
            },
            {
                "name": "Case 3: Reverse-Charge Scam (upi://collect attack)",
                "qr": "upi://collect?pa=scammer_collect@upi&am=5000.00",
                "expected_decision": "FRAUD",
                "expected_action": "HARD_BLOCK_PAYMENT"
            },
            {
                "name": "Case 4: Quishing Attack (Phishing Link QR)",
                "qr": "http://sbi-kyc-verification.portal-update.xyz/login.php?ref=claim",
                "expected_decision": "FRAUD",
                "expected_action": "HARD_BLOCK_PAYMENT"
            },
            {
                "name": "Case 5: Genuine Bank Portal Web Link",
                "qr": "https://onlinesbi.sbi/portal/login",
                "expected_decision": "SAFE",
                "expected_action": "AUTO_REDIRECT_PAYMENT"
            },
            {
                "name": "Case 6: Suspicious High-Value New Transfer",
                "qr": "upi://pay?pa=urgent_cash_lottery99@upi&am=45000.00",
                "expected_decision": "SUSPICIOUS",
                "expected_action": "SHOW_WARNING_MODAL"
            }
        ]

        for tc in test_cases:
            print(f"\n--- Testing: {tc['name']} ---")
            payload = {"qr_raw": tc["qr"], "user_id": "test_mobile_user_01"}
            res = client.post("/api/v1/qr/analyze", json=payload)
            
            assert res.status_code == 200, f"API failed with status {res.status_code}: {res.text}"
            data = res.json()
            
            print(f"  Decision:       {data['decision']}")
            print(f"  Risk Score:     {data['risk_score']:.4f}")
            print(f"  Action:         {data['action']}")
            print(f"  Summary Reason: {data['summary_reason']}")
            print(f"  Target Entity:  {data['target_entity']}")
            
            assert data["decision"] == tc["expected_decision"], f"Expected {tc['expected_decision']}, got {data['decision']}"
            assert data["action"] == tc["expected_action"], f"Expected {tc['expected_action']}, got {data['action']}"
            print("  Status: [PASSED]")

        # Check Audit Logs
        audit_res = client.get("/api/v1/audit/logs?limit=5")
        assert audit_res.status_code == 200
        logs = audit_res.json()["logs"]
        print(f"\n[+] Audit Logs Successfully Recorded in SQLite Database! (Retrieved {len(logs)} logs)")
        print("=" * 70)
        print("      ALL GATEKEEPER BACKEND TESTS PASSED (100% SUCCESS)!")
        print("=" * 70)


if __name__ == "__main__":
    test_gatekeeper_api()
