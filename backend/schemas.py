"""
Pydantic Data Contracts and Schemas for FastAPI Backend.
Defines strict type validation for incoming mobile requests and outgoing responses.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class DecisionType(str, Enum):
    """Calibrated tri-state decision outcomes."""
    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    FRAUD = "FRAUD"
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"


class PayloadType(str, Enum):
    """Supported QR payload formats."""
    UPI = "UPI"
    URL = "URL"
    PAYMENT_URL = "PAYMENT_URL"
    UNKNOWN = "UNKNOWN"


class ClientAction(str, Enum):
    """Action instructed to the Android client."""
    AUTO_REDIRECT_PAYMENT = "AUTO_REDIRECT_PAYMENT"
    SHOW_WARNING_MODAL = "SHOW_WARNING_MODAL"
    HARD_BLOCK_PAYMENT = "HARD_BLOCK_PAYMENT"
    DISPLAY_ERROR = "DISPLAY_ERROR"


class ClientActionDto(BaseModel):
    """Nested client action contract matching Android expectations."""
    allow_proceed: bool
    show_warning: bool
    warning_message: Optional[str] = None


class QRAnalyzeRequest(BaseModel):
    """Incoming request payload from the Android mobile app or API testers."""
    qr_raw: Optional[str] = Field(None, description="Raw UTF-8 string decoded from the QR code")
    qr_data: Optional[str] = Field(None, description="Alternative field name for QR data")
    user_id: Optional[str] = Field("user_android_client", description="Unique user or client ID")
    device_fingerprint: Optional[str] = Field(None, description="Client device hardware hash")
    source: Optional[str] = Field("camera", description="Trigger source: camera, manual, or external_intent")
    latitude: Optional[float] = Field(None, description="Device GPS latitude for geo-fenced merchant QR verification")
    longitude: Optional[float] = Field(None, description="Device GPS longitude for geo-fenced merchant QR verification")
    accuracy_m: Optional[float] = Field(None, description="GPS accuracy in meters")

    def get_raw_qr(self) -> str:
        """Returns the non-empty QR payload string."""
        return (self.qr_raw or self.qr_data or "").strip()


class MerchantRegisterRequest(BaseModel):
    """Registers an authentic merchant counter QR at a physical store location."""
    shop_name: str = Field(..., min_length=2, description="Human-readable shop or business name")
    official_vpa: Optional[str] = Field(None, description="Verified merchant UPI ID (pa=)")
    raw_qr: Optional[str] = Field(None, description="Optional raw upi:// QR string to parse VPA and MCC from")
    mcc: Optional[str] = Field(None, description="4-digit Merchant Category Code (e.g. 5411)")
    latitude: float = Field(..., description="Physical store latitude")
    longitude: float = Field(..., description="Physical store longitude")
    radius_m: float = Field(40.0, ge=10.0, le=500.0, description="Geo-fence radius in meters")


class QRAnalyzeResponse(BaseModel):
    """Structured response returned back to the Android mobile app."""
    status: str = Field("success", description="Status of the request execution")
    decision: str = Field(..., description="Final tri-state verdict: ALLOW, WARN, BLOCK")
    risk_score: float = Field(..., description="Continuous risk score between 0.0 and 1.0")
    confidence: float = Field(..., description="Statistical confidence of the model prediction")
    payload_type: str = Field(..., description="Detected payload type: UPI or URL")
    action: ClientAction = Field(..., description="Action to be performed by the mobile app")
    client_action: ClientActionDto = Field(..., description="Client action details for Android")
    summary_reason: str = Field(..., description="Single-line human-readable explanation of the verdict")
    reasons: List[str] = Field(default_factory=list, description="List of reasons for explainable AI")
    target_entity: Optional[str] = Field(None, description="Extracted Payee VPA or Web Domain")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Detailed diagnostic signals")


class HealthResponse(BaseModel):
    """System readiness check response."""
    status: str
    version: str = "1.0.0"
    models_loaded: bool = True
    ja_gnn_model_loaded: bool = True
    url_model_loaded: bool = True
    threat_intel_entries: int = 0
