"""
FastAPI Main Application Server.
Exposes high-speed asynchronous REST endpoints for Android QR fraud detection.
Roundtrip latency: < 200ms.
"""

import os
import sys

# Ensure root directory is in sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from backend.schemas import (
    QRAnalyzeRequest,
    QRAnalyzeResponse,
    MerchantRegisterRequest,
    HealthResponse,
    DecisionType,
    PayloadType,
    ClientAction,
    ClientActionDto
)
from backend.services.qr_router import QRPayloadRouter
from backend.services.url_service import URLAnalysisService
from backend.services.gnn_service import JAGNNInferenceService
from backend.services.decision_engine import DecisionEngine
from backend.database import db

# Global service singletons
url_service = None
gnn_service = None


def get_services():
    """Returns initialized service singletons, ensuring lazy loading if lifespan is bypassed."""
    global url_service, gnn_service
    if url_service is None:
        url_service = URLAnalysisService()
    if gnn_service is None:
        gnn_service = JAGNNInferenceService()
    return url_service, gnn_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warms all AI models and threat intelligence into RAM at server boot."""
    print("\n" + "=" * 65)
    print("      INITIALIZING FINANCIAL FRAUD GATEKEEPER SERVER")
    print("=" * 65)
    get_services()
    print("[Server Boot] All AI models pre-loaded in memory. Ready for requests!")
    print("=" * 65 + "\n")
    yield
    print("[Server Shutdown] Cleaning up resources...")


app = FastAPI(
    title="GNN-Based Financial Fraud Detection & Security Gatekeeper API",
    description="High-speed real-time microservice analyzing UPI payments and quishing web links.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Android client connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    """Root health endpoint for cloud monitoring and web previews."""
    return {
        "service": "FraudShield AI Gatekeeper Backend",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """System health check and model loading verification."""
    url_svc, gnn_svc = get_services()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        models_loaded=True,
        ja_gnn_model_loaded=gnn_svc is not None and gnn_svc.model is not None,
        url_model_loaded=url_svc is not None and url_svc.model is not None,
        threat_intel_entries=len(url_svc.threat_intel.blacklisted_urls) if url_svc else 0
    )


@app.post("/api/v1/qr/analyze", response_model=QRAnalyzeResponse, tags=["Inference"])
async def analyze_qr(request: QRAnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Main Gatekeeper Inference Endpoint.
    Analyzes raw QR payload string in < 40ms, computes risk probability,
    and returns tri-state verdict (ALLOW / WARN / BLOCK).
    """
    raw_qr = request.get_raw_qr()
    if not raw_qr:
        raise HTTPException(status_code=400, detail="Empty QR payload provided.")

    # 1. High-speed Protocol Sorter (< 0.1ms)
    route_info = QRPayloadRouter.route(raw_qr)
    payload_type = route_info["payload_type"]
    target_entity = route_info.get("target_entity", "unknown")

    # 1b. Check Permanent Device & System Hard Blacklist (Zero Latency < 0.1ms)
    # If the user previously flagged as fraud or unproceeded from a suspicious QR/URL, enforce permanent block
    if (
        db.is_entity_blocked(raw_qr) or
        db.is_entity_blocked(target_entity) or
        (route_info.get("payee_vpa") and db.is_entity_blocked(route_info["payee_vpa"])) or
        (route_info.get("domain") and db.is_entity_blocked(route_info["domain"]))
    ):
        return QRAnalyzeResponse(
            status="success",
            decision="BLOCK",
            risk_score=1.0,
            confidence=1.0,
            payload_type=payload_type.value if hasattr(payload_type, "value") else str(payload_type),
            action=ClientAction.HARD_BLOCK_PAYMENT,
            client_action=ClientActionDto(
                allow_proceed=False,
                show_warning=False,
                warning_message="PERMANENT HARD BLOCK: Entity is blacklisted on this device. Scanning & opening are strictly prohibited."
            ),
            summary_reason="PERMANENT HARD BLOCK: Threat is permanently blacklisted on this device. Redirection disabled.",
            reasons=[
                "Permanent Device Blacklist: Entity was previously flagged as danger or suspicious and cancelled.",
                "Security Policy Enforced: Target URL / QR is barred from opening on any browser or payment app."
            ],
            target_entity=target_entity,
            metadata={"device_hard_blocked": True, "permanently_blacklisted": True}
        )

    # 2. Lazy Model Initialization (only if not pre-blocked)
    url_svc, gnn_svc = get_services()

    # 3. Branching Inference Execution
    if payload_type == PayloadType.URL:
        if route_info.get("is_payment_url"):
            # Branch A1: Payment-Related URL -> Evaluated by JA-GNN Graph Intelligence + Perimeter URL Classifier
            url_res = url_svc.analyze(route_info["url"])

            # Resolve payee VPA for JA-GNN & geo-fenced counter verification
            payee_vpa = route_info.get("payee_vpa")
            if not payee_vpa:
                payee_vpa = f"{route_info.get('domain', 'merchant')}@gateway"

            nearby_merchants = db.get_merchants_near(request.latitude, request.longitude)
            location_history = db.analyze_location_vpa_history(request.latitude, request.longitude, payee_vpa)

            gnn_res = gnn_svc.analyze_transaction(
                payee_vpa=payee_vpa,
                amount=route_info.get("amount"),
                mcc=route_info.get("mcc"),
                payee_name=route_info.get("payee_name"),
                is_collect_scam=route_info.get("is_collect_scam", False),
                is_merchant_qr=route_info.get("is_merchant_qr", False),
                nearby_merchants=nearby_merchants,
                location_history=location_history,
            )

            # Risk Fusion:
            # Check if either URL phishing or JA-GNN graph model flags a threat
            risk_score = max(url_res["risk_score"], gnn_res["risk_score"])
            confidence = round((url_res["confidence"] + gnn_res["confidence"]) / 2.0, 4)

            if gnn_res["risk_score"] >= 0.74:
                summary_reason = f"JA-GNN Alert: {gnn_res['summary_reason']}"
            elif url_res["risk_score"] >= 0.74:
                summary_reason = f"Phishing Defense Alert: {url_res['summary_reason']}"
            elif gnn_res["risk_score"] <= 0.40 and url_res["risk_score"] <= 0.40:
                summary_reason = f"JA-GNN Verified: Safe payment link. {gnn_res['summary_reason']}"
            else:
                summary_reason = f"Caution: {gnn_res['summary_reason']} | {url_res['summary_reason']}"

            target_entity = payee_vpa or route_info.get("domain", "payment_gateway")
            payload_type_value = PayloadType.PAYMENT_URL

            metadata = {
                "is_payment_url": True,
                "payee_vpa": payee_vpa,
                "domain": route_info.get("domain"),
                "url_risk": url_res["risk_score"],
                "gnn_risk": gnn_res["risk_score"],
                "gnn_engine": gnn_res.get("engine", "JA_GNN_Model"),
                "is_mule": gnn_res.get("is_mule", False)
            }
            metadata.update(gnn_res.get("metadata", {}))

        else:
            # Branch A2: Standard Web URL / Quishing Analysis
            analysis_result = url_svc.analyze(route_info["url"])
            risk_score = analysis_result["risk_score"]
            confidence = analysis_result["confidence"]
            summary_reason = analysis_result["summary_reason"]
            metadata = analysis_result.get("metadata", {})
            payload_type_value = PayloadType.URL

    elif payload_type == PayloadType.UPI:
        payload_type_value = PayloadType.UPI
        # Check for Trojan Embedded URL inside UPI note
        if route_info.get("embedded_url"):
            url_res = url_svc.analyze(route_info["embedded_url"])
            if url_res["risk_score"] >= 0.74:
                risk_score = url_res["risk_score"]
                confidence = url_res["confidence"]
                summary_reason = f"Blocked: Trojan link hidden in UPI note! {url_res['summary_reason']}"
                metadata = {"embedded_phishing": True}
                decision, action = DecisionEngine.evaluate(risk_score)
                # Background logging
                background_tasks.add_task(
                    db.log_scan, request.user_id, request.device_fingerprint,
                    raw_qr, target_entity, payload_type.value, risk_score,
                    decision.value, action.value, summary_reason,
                    request.latitude, request.longitude,
                )
                return QRAnalyzeResponse(
                    status="success",
                    decision="BLOCK",
                    risk_score=risk_score,
                    confidence=confidence,
                    payload_type=payload_type.value,
                    action=action,
                    client_action=ClientActionDto(allow_proceed=False, show_warning=False, warning_message=summary_reason),
                    summary_reason=summary_reason,
                    reasons=[summary_reason, "Perimeter Defense: High-risk phishing URL embedded in UPI note."],
                    target_entity=target_entity,
                    metadata=metadata
                )

        # Branch B: JA-GNN Financial Graph + Geo-Fenced Counter Sticker Check
        payee_vpa = route_info.get("payee_vpa", "")
        nearby_merchants = db.get_merchants_near(request.latitude, request.longitude)
        location_history = db.analyze_location_vpa_history(request.latitude, request.longitude, payee_vpa)

        analysis_result = gnn_svc.analyze_transaction(
            payee_vpa=payee_vpa,
            amount=route_info.get("amount"),
            mcc=route_info.get("mcc"),
            payee_name=route_info.get("payee_name"),
            is_collect_scam=route_info.get("is_collect_scam", False),
            is_merchant_qr=route_info.get("is_merchant_qr", False),
            nearby_merchants=nearby_merchants,
            location_history=location_history,
        )
        risk_score = analysis_result["risk_score"]
        confidence = analysis_result["confidence"]
        summary_reason = analysis_result["summary_reason"]
        metadata = analysis_result.get("metadata", {})

    else:
        # Unrecognized / Invalid Format
        risk_score = 0.50
        confidence = 0.50
        summary_reason = "Warning: Unrecognized QR format. Cannot verify financial safety."
        metadata = {"unrecognized": True}
        payload_type_value = PayloadType.UNKNOWN

    # 3. Apply Calibrated Decision Engine (T1=0.40, T2=0.74)
    decision, action = DecisionEngine.evaluate(risk_score)

    # Map to standardized client decision code: ALLOW / WARN / BLOCK
    if decision == DecisionType.SAFE:
        decision_code = "ALLOW"
        client_action = ClientActionDto(allow_proceed=True, show_warning=False)
        reasons_list = [summary_reason, "All security parameters verified against neural graph & domain databases."]
    elif decision == DecisionType.SUSPICIOUS:
        decision_code = "WARN"
        client_action = ClientActionDto(allow_proceed=False, show_warning=True, warning_message=summary_reason)
        reasons_list = [summary_reason, "Unusual transaction parameter detected. Cautious confirmation required."]
    else:
        decision_code = "BLOCK"
        client_action = ClientActionDto(allow_proceed=False, show_warning=False, warning_message=summary_reason)
        reasons_list = [summary_reason, "Hard Block enforced by AI security gatekeeper to prevent fraud."]

    # 4. Asynchronous Background Logging (0 ms delay to client)
    background_tasks.add_task(
        db.log_scan,
        request.user_id,
        request.device_fingerprint,
        raw_qr,
        target_entity,
        payload_type_value.value if hasattr(payload_type_value, "value") else str(payload_type_value),
        risk_score,
        decision.value,
        action.value,
        summary_reason,
        request.latitude,
        request.longitude,
    )

    # 5. Return JSON payload to Android App
    return QRAnalyzeResponse(
        status="success",
        decision=decision_code,
        risk_score=risk_score,
        confidence=confidence,
        payload_type=payload_type_value.value if hasattr(payload_type_value, "value") else str(payload_type_value),
        action=action,
        client_action=client_action,
        summary_reason=summary_reason,
        reasons=reasons_list,
        target_entity=target_entity,
        metadata=metadata
    )


@app.get("/api/v1/audit/logs", tags=["Audit"])
async def get_audit_logs(limit: int = 20):
    """Retrieves recent scan audit logs."""
    return {"logs": db.get_recent_scans(limit=limit)}


@app.post("/api/v1/blacklist/block", tags=["Blacklist"])
async def record_hard_block(data: Dict[str, Any]):
    """
    Persistently hard-blocks a dangerous or user-rejected suspicious QR / URL / VPA.
    Synchronizes with the device's permanent blacklist so it can never be scanned or opened again.
    """
    entity = data.get("entity", "").strip()
    if not entity:
        raise HTTPException(status_code=400, detail="Entity must not be empty.")
    entity_type = data.get("entity_type", "UNKNOWN")
    reason = data.get("reason", "Hard blocked by user security action")
    risk_score = float(data.get("risk_score", 1.0))

    db.block_entity(entity_id=entity, entity_type=entity_type, risk_score=risk_score, reason=reason)
    return {"status": "success", "message": f"Entity '{entity}' permanently blacklisted.", "entity": entity}


@app.get("/api/v1/blacklist", tags=["Blacklist"])
async def get_blacklist(limit: int = 50):
    """Retrieves permanently blacklisted entities."""
    return {"blocked_entities": db.get_blocked_entities(limit=limit)}


@app.post("/api/v1/merchants/register", tags=["Merchant Counter Guard"])
async def register_merchant_qr(req: MerchantRegisterRequest):
    """
    Binds an authentic shopkeeper QR VPA to the physical store's GPS coordinates.
    Detects QR sticker-overlay fraud if someone later pastes a foreign QR at the shop.
    """
    vpa = (req.official_vpa or "").strip().lower()
    mcc = (req.mcc or "").strip()

    if req.raw_qr:
        route_info = QRPayloadRouter.route(req.raw_qr)
        if not vpa:
            vpa = (route_info.get("payee_vpa") or "").strip().lower()
        if not mcc:
            mcc = (route_info.get("mcc") or "").strip()

    if not vpa or "@" not in vpa:
        raise HTTPException(
            status_code=400,
            detail="Could not extract valid merchant UPI VPA (expected name@bank or upi://pay?pa=...)."
        )

    if db.is_entity_blocked(vpa):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot register blacklisted VPA '{vpa}' as an authentic merchant."
        )

    merchant = db.register_merchant(
        shop_name=req.shop_name,
        official_vpa=vpa,
        mcc=mcc,
        latitude=req.latitude,
        longitude=req.longitude,
        radius_m=req.radius_m,
    )
    return {
        "status": "success",
        "message": f"Registered '{merchant['shop_name']}' ({merchant['official_vpa']}) at ({merchant['latitude']:.5f}, {merchant['longitude']:.5f}).",
        "merchant": merchant,
    }


@app.get("/api/v1/merchants", tags=["Merchant Counter Guard"])
async def list_registered_merchants(limit: int = 50):
    """Lists registered physical store QR counter bindings."""
    return {"merchants": db.get_all_merchants(limit=limit)}


@app.get("/api/v1/merchants/nearby", tags=["Merchant Counter Guard"])
async def list_nearby_merchants(lat: float, lon: float):
    """Lists registered stores covering the given GPS coordinates."""
    return {"merchants": db.get_merchants_near(lat, lon)}


@app.delete("/api/v1/merchants/{merchant_id}", tags=["Merchant Counter Guard"])
async def delete_registered_merchant(merchant_id: int):
    """Deletes a registered merchant binding by ID."""
    deleted = db.delete_merchant(merchant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Merchant binding not found.")
    return {"status": "success", "deleted_id": merchant_id}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.app:app", host="0.0.0.0", port=port, reload=False)
