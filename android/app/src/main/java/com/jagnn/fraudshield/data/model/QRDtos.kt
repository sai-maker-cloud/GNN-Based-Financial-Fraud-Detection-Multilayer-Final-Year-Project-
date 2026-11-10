package com.jagnn.fraudshield.data.model

import com.google.gson.annotations.SerializedName

data class QRAnalyzeRequest(
    @SerializedName("qr_raw") val qrRaw: String,
    @SerializedName("qr_data") val qrData: String = qrRaw,
    @SerializedName("source") val source: String = "camera",
    @SerializedName("latitude") val latitude: Double? = null,
    @SerializedName("longitude") val longitude: Double? = null,
    @SerializedName("accuracy_m") val accuracyM: Float? = null
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
    @SerializedName("analyzed_at") val analyzedAt: String? = null,
    @SerializedName("metadata") val metadata: Map<String, Any>? = null
) {
    val normalizedDecision: String
        get() = when (decision.uppercase()) {
            "SAFE", "ALLOW" -> "ALLOW"
            "SUSPICIOUS", "WARN" -> "WARN"
            else -> "BLOCK"
        }

    val isStickerTamperingSuspected: Boolean
        get() = (metadata?.get("sticker_tampering_suspected") as? Boolean) == true ||
                (summaryReason?.contains("Sticker", ignoreCase = true) == true) ||
                (summaryReason?.contains("Mismatch", ignoreCase = true) == true) ||
                (summaryReason?.contains("Counter", ignoreCase = true) == true)

    val isUnverifiedPersonalQr: Boolean
        get() = (metadata?.get("unverified_personal_qr") as? Boolean) == true ||
                (summaryReason?.contains("Personal Account QR", ignoreCase = true) == true)

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

data class MerchantRegisterRequest(
    @SerializedName("shop_name") val shopName: String,
    @SerializedName("official_vpa") val officialVpa: String? = null,
    @SerializedName("raw_qr") val rawQr: String? = null,
    @SerializedName("mcc") val mcc: String? = null,
    @SerializedName("latitude") val latitude: Double,
    @SerializedName("longitude") val longitude: Double,
    @SerializedName("radius_m") val radiusM: Float = 40.0f
)

data class MerchantDto(
    @SerializedName("id") val id: Int = 0,
    @SerializedName("shop_name") val shopName: String = "",
    @SerializedName("official_vpa") val officialVpa: String = "",
    @SerializedName("mcc") val mcc: String? = null,
    @SerializedName("latitude") val latitude: Double = 0.0,
    @SerializedName("longitude") val longitude: Double = 0.0,
    @SerializedName("radius_m") val radiusM: Float = 40.0f
)

data class MerchantRegisterResponse(
    @SerializedName("status") val status: String = "",
    @SerializedName("message") val message: String = "",
    @SerializedName("merchant") val merchant: MerchantDto? = null
)

data class MerchantListResponse(
    @SerializedName("merchants") val merchants: List<MerchantDto> = emptyList()
)

data class BlacklistBlockRequest(
    @SerializedName("entity") val entity: String,
    @SerializedName("entity_type") val entityType: String = "UPI",
    @SerializedName("reason") val reason: String,
    @SerializedName("risk_score") val riskScore: Float = 1.0f
)
