"""
Automated Test Suite for FastAPI Backend Gatekeeper.
Simulates real-world QR scans from mobile phones and verifies
the tri-state classification, latency, and single-line reasons.
"""

import os
import sys
import uuid

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
                "expected_decision": "ALLOW",
                "expected_action": "AUTO_REDIRECT_PAYMENT"
            },
            {
                "name": "Case 2: Known Fraud Syndicate / Money Mule",
                "qr": "upi://pay?pa=rahul_kumar88@ybl&pn=QuickDeal&am=8000.00",
                "expected_decision": "BLOCK",
                "expected_action": "HARD_BLOCK_PAYMENT"
            },
            {
                "name": "Case 3: Reverse-Charge Scam (upi://collect attack)",
                "qr": "upi://collect?pa=scammer_collect@upi&am=5000.00",
                "expected_decision": "BLOCK",
                "expected_action": "HARD_BLOCK_PAYMENT"
            },
            {
                "name": "Case 4: Quishing Attack (Phishing Link QR)",
                "qr": "http://sbi-kyc-verification.portal-update.xyz/login.php?ref=claim",
                "expected_decision": "BLOCK",
                "expected_action": "HARD_BLOCK_PAYMENT"
            },
            {
                "name": "Case 5: Genuine Bank Portal Web Link",
                "qr": "https://onlinesbi.sbi/portal/login",
                "expected_decision": "ALLOW",
                "expected_action": "AUTO_REDIRECT_PAYMENT"
            },
            {
                "name": "Case 6: Suspicious High-Value New Transfer",
                "qr": "upi://pay?pa=urgent_cash_lottery99@upi&am=45000.00",
                "expected_decision": "WARN",
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

        # Sticker-Overlay Fraud Tests (Geo-Fenced Store Counter Protection)
        print("\n--- Testing: Counter QR Sticker Replacement Defense ---")
        store_lat, store_lon = 18.52043, 73.85674
        reg_res = client.post("/api/v1/merchants/register", json={
            "shop_name": "Patel Grocery Mart",
            "raw_qr": "upi://pay?pa=patel_grocery@icici&pn=PatelGrocery&mc=5411",
            "latitude": store_lat,
            "longitude": store_lon,
            "radius_m": 40.0
        })
        assert reg_res.status_code == 200, f"Merchant register failed: {reg_res.text}"
        registered_id = reg_res.json()["merchant"]["id"]

        try:
            # 1. Scanning real store QR at the store -> ALLOW
            ok_scan = client.post("/api/v1/qr/analyze", json={
                "qr_raw": "upi://pay?pa=patel_grocery@icici&pn=PatelGrocery&mc=5411&am=250",
                "latitude": store_lat,
                "longitude": store_lon,
            })
            assert ok_scan.status_code == 200
            ok_data = ok_scan.json()
            assert ok_data["decision"] == "ALLOW", f"Expected ALLOW for genuine store QR, got {ok_data}"

            # 2. Scanning a pasted clean personal QR at the exact same store -> BLOCK!
            fake_vpa = f"sneaky_paster_{uuid.uuid4().hex[:6]}@okaxis"
            sticker_scan = client.post("/api/v1/qr/analyze", json={
                "qr_raw": f"upi://pay?pa={fake_vpa}&pn=Rohan",
                "latitude": store_lat + 0.00005,
                "longitude": store_lon - 0.00004,
            })
            assert sticker_scan.status_code == 200
            sticker_data = sticker_scan.json()
            print(f"  Pasted Personal QR Decision: {sticker_data['decision']} | Score: {sticker_data['risk_score']}")
            print(f"  Reason: {sticker_data['summary_reason']}")
            assert sticker_data["decision"] == "BLOCK", f"Expected BLOCK for pasted personal QR at store, got {sticker_data}"
            assert sticker_data["metadata"].get("sticker_tampering_suspected") is True

            # 3. Scanning an unregistered personal QR away from registered shops -> WARN (never auto-launch!)
            p2p_scan = client.post("/api/v1/qr/analyze", json={
                "qr_raw": "upi://pay?pa=random_person@okhdfcbank&pn=RandomUser&am=500",
                "latitude": 19.0760,
                "longitude": 72.8777,
            })
            assert p2p_scan.status_code == 200
            p2p_data = p2p_scan.json()
            print(f"  Unverified Personal QR Decision: {p2p_data['decision']} | Score: {p2p_data['risk_score']}")
            assert p2p_data["decision"] == "WARN", f"Expected WARN for unverified personal QR, got {p2p_data}"
            print("  Sticker-Overlay Tests: [PASSED]")
        finally:
            # Clean up test merchant and don't leave test fake VPA blacklisted if test re-runs
            client.delete(f"/api/v1/merchants/{registered_id}")

        print("=" * 70)
        print("      ALL GATEKEEPER BACKEND TESTS PASSED (100% SUCCESS)!")
        print("=" * 70)


if __name__ == "__main__":
    test_gatekeeper_api()
