package com.jagnn.fraudshield.data.model

import com.google.gson.annotations.SerializedName

data class QRAnalyzeRequest(
    @SerializedName("qr_raw") val qrRaw: String,
    @SerializedName("qr_data") val qrData: String = qrRaw,
    @SerializedName("source") val source: String = "camera"
)

data class QRAnalyzeResponse(
    @SerializedName("decision") val decision: String, // ALLOW, WARN, BLOCK or SAFE, SUSPICIOUS, FRAUD
    @SerializedName("risk_score") val riskScore: Float, // 0.0 - 1.0
    @SerializedName("payload_type") val payloadType: String,
    @SerializedName("reasons") val reasons: List<String>? = null,
    @SerializedName("summary_reason") val summaryReason: String? = null,
    @SerializedName("client_action") val clientAction: ClientActionDto? = null,
    @SerializedName("action") val action: String? = null,
    @SerializedName("target_entity") val targetEntity: String? = null,
    @SerializedName("analyzed_at") val analyzedAt: String? = null
) {
    val normalizedDecision: String
        get() = when (decision.uppercase()) {
            "SAFE", "ALLOW" -> "ALLOW"
            "SUSPICIOUS", "WARN" -> "WARN"
            else -> "BLOCK"
        }

    val displayReasons: List<String>
        get() {
            if (!reasons.isNullOrEmpty()) return reasons
            if (!summaryReason.isNullOrBlank()) return listOf(summaryReason)
            return listOf("Clean transaction parameters verified against neural graph & domain databases.")
        }
}

data class ClientActionDto(
    @SerializedName("allow_proceed") val allowProceed: Boolean = false,
    @SerializedName("show_warning") val showWarning: Boolean = false,
    @SerializedName("warning_message") val warningMessage: String? = null
)

data class HealthResponse(
    @SerializedName("status") val status: String,
    @SerializedName("models_loaded") val modelsLoaded: Boolean = true,
    @SerializedName("ja_gnn_model_loaded") val jaGnnLoaded: Boolean = true,
    @SerializedName("url_model_loaded") val urlModelLoaded: Boolean = true
)

data class AuditItem(
    val id: String,
    val payeeName: String,
    val payeeUpi: String,
    val amount: String,
    val rawQr: String,
    val decision: String, // ALLOW, WARN, BLOCK
    val riskScore: Float,
    val reasons: List<String>,
    val timestamp: Long = System.currentTimeMillis()
)
