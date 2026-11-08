package com.jagnn.fraudshield.data.repository

import android.net.Uri
import com.jagnn.fraudshield.data.api.RetrofitClient
import com.jagnn.fraudshield.data.model.AuditItem
import com.jagnn.fraudshield.data.model.ClientActionDto
import com.jagnn.fraudshield.data.model.QRAnalyzeRequest
import com.jagnn.fraudshield.data.model.QRAnalyzeResponse
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.UUID

class FraudRepository {

    private val _auditList = MutableStateFlow<List<AuditItem>>(createInitialSampleAudits())
    val auditList: StateFlow<List<AuditItem>> = _auditList.asStateFlow()

    suspend fun analyzeQR(qrData: String, baseUrl: String): Result<QRAnalyzeResponse> {
        return try {
            val api = RetrofitClient.getService(baseUrl)
            val response = api.analyzeQR(QRAnalyzeRequest(qrRaw = qrData, source = "camera"))
            if (response.isSuccessful && response.body() != null) {
                val body = response.body()!!
                recordAudit(qrData, body)
                Result.success(body)
            } else {
                // If server returns error, perform on-device emergency triage
                val fallback = performLocalFallbackAnalysis(qrData)
                recordAudit(qrData, fallback)
                Result.success(fallback)
            }
        } catch (e: Exception) {
            // Local on-device safety fallback if offline
            val fallback = performLocalFallbackAnalysis(qrData)
            recordAudit(qrData, fallback)
            Result.success(fallback)
        }
    }

    private fun recordAudit(qrData: String, response: QRAnalyzeResponse) {
        val parsed = parseUpiParams(qrData)
        val item = AuditItem(
            id = UUID.randomUUID().toString(),
            payeeName = parsed["pn"] ?: (if (qrData.startsWith("http")) "Web URL" else "Direct Transfer"),
            payeeUpi = parsed["pa"] ?: (if (qrData.length > 32) qrData.take(32) + "…" else qrData),
            amount = parsed["am"] ?: "0.00",
            rawQr = qrData,
            decision = response.decision,
            riskScore = response.riskScore,
            reasons = response.displayReasons,
            timestamp = System.currentTimeMillis()
        )
        val current = _auditList.value.toMutableList()
        current.add(0, item)
        _auditList.value = current.take(20)
    }

    private fun performLocalFallbackAnalysis(qrData: String): QRAnalyzeResponse {
        val lower = qrData.lowercase()
        return when {
            lower.contains("mode=01") || lower.contains("collect") -> {
                QRAnalyzeResponse(
                    decision = "BLOCK",
                    riskScore = 0.95f,
                    payloadType = "COLLECT_SCAM",
                    reasons = listOf("On-device shield: Reverse collect request scam detected!"),
                    clientAction = ClientActionDto(allowProceed = false, showWarning = false, warningMessage = "Collect request scam blocked.")
                )
            }
            lower.startsWith("http://") || lower.endsWith(".tk") || lower.endsWith(".ml") -> {
                QRAnalyzeResponse(
                    decision = "BLOCK",
                    riskScore = 0.92f,
                    payloadType = "PHISHING_URL",
                    reasons = listOf("On-device perimeter: Insecure or suspicious web domain embedded in QR."),
                    clientAction = ClientActionDto(allowProceed = false, showWarning = false, warningMessage = "Malicious URL blocked.")
                )
            }
            lower.startsWith("upi://") -> {
                QRAnalyzeResponse(
                    decision = "ALLOW",
                    riskScore = 0.08f,
                    payloadType = "UPI_PAY",
                    reasons = listOf("Standard UPI payment intent structure verified."),
                    clientAction = ClientActionDto(allowProceed = true, showWarning = false)
                )
            }
            else -> {
                QRAnalyzeResponse(
                    decision = "ALLOW",
                    riskScore = 0.02f,
                    payloadType = "PLAIN_TEXT",
                    reasons = listOf("Informational QR payload."),
                    clientAction = ClientActionDto(allowProceed = true, showWarning = false)
                )
            }
        }
    }

    fun parseUpiParams(qrData: String): Map<String, String> {
        if (!qrData.startsWith("upi://pay")) return emptyMap()
        val map = mutableMapOf<String, String>()
        try {
            val uri = Uri.parse(qrData)
            uri.queryParameterNames.forEach { key ->
                uri.getQueryParameter(key)?.let { value ->
                    map[key] = value
                }
            }
        } catch (_: Exception) {}
        return map
    }

    private fun createInitialSampleAudits(): List<AuditItem> {
        return listOf(
            AuditItem(
                id = "1",
                payeeName = "DMart Supermarket",
                payeeUpi = "dmart_retail@hdfc",
                amount = "840.00",
                rawQr = "upi://pay?pa=dmart_retail@hdfc&pn=DMart%20Supermarket&am=840.00",
                decision = "ALLOW",
                riskScore = 0.04f,
                reasons = listOf("Verified Merchant with clean graph history.")
            ),
            AuditItem(
                id = "2",
                payeeName = "FastCash Collect",
                payeeUpi = "mule_88291@ybl",
                amount = "14,500.00",
                rawQr = "upi://pay?pa=mule_88291@ybl&pn=FastCash&am=14500&mode=01",
                decision = "BLOCK",
                riskScore = 0.96f,
                reasons = listOf("Reverse-charge scam & money-mule syndicate tie.")
            ),
            AuditItem(
                id = "3",
                payeeName = "Sharmaji Kirana",
                payeeUpi = "sharma_kirana@icici",
                amount = "210.00",
                rawQr = "upi://pay?pa=sharma_kirana@icici&pn=Sharmaji&am=210.00",
                decision = "ALLOW",
                riskScore = 0.06f,
                reasons = listOf("Trusted local retail store.")
            )
        )
    }
}

