package com.jagnn.fraudshield.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.jagnn.fraudshield.data.model.QRAnalyzeResponse
import com.jagnn.fraudshield.data.repository.FraudRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed class ScanUiState {
    object Idle : ScanUiState()
    object Analyzing : ScanUiState()
    data class Success(val response: QRAnalyzeResponse, val rawQr: String) : ScanUiState()
    data class Error(val message: String) : ScanUiState()
}

class ScannerViewModel(
    private val fraudRepository: FraudRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<ScanUiState>(ScanUiState.Idle)
    val uiState: StateFlow<ScanUiState> = _uiState.asStateFlow()

    private var lastScannedQr: String? = null
    private var lastScanTimestamp: Long = 0

    fun onQrScanned(qrData: String, baseUrl: String) {
        val now = System.currentTimeMillis()
        // Prevent rapid duplicate scans within 2.5 seconds
        if (qrData == lastScannedQr && (now - lastScanTimestamp) < 2500) {
            return
        }

        lastScannedQr = qrData
        lastScanTimestamp = now

        // 0. Instant Device Hard Blacklist Intercept (< 0.05ms)
        // If this QR or website was previously detected as danger or unproceeded by the user,
        // it is completely barred from scanning, resolving, or opening on this device.
        if (com.jagnn.fraudshield.data.repository.DeviceBlacklistManager.isBlocked(qrData)) {
            val reason = com.jagnn.fraudshield.data.repository.DeviceBlacklistManager.getBlockReason(qrData)
            val blockedResponse = QRAnalyzeResponse(
                decision = "BLOCK",
                riskScore = 1.0f,
                payloadType = "PERMANENT_DEVICE_BLACKLIST",
                summaryReason = "PERMANENT HARD BLOCK: This QR or website is blacklisted on this device. Scanning and opening are strictly prohibited.",
                reasons = listOf(
                    "Device Hard Blacklist Enforced: Threat was permanently blocked on this system.",
                    "Security Enforcement: $reason",
                    "Redirection to any web browser or payment gateway is prohibited."
                ),
                targetEntity = qrData,
                clientAction = com.jagnn.fraudshield.data.model.ClientActionDto(
                    allowProceed = false,
                    showWarning = false,
                    warningMessage = "PERMANENT HARD BLOCK: Target is blacklisted on this device."
                )
            )
            _uiState.value = ScanUiState.Success(blockedResponse, qrData)
            return
        }

        _uiState.value = ScanUiState.Analyzing

        viewModelScope.launch {
            val result = fraudRepository.analyzeQR(qrData, baseUrl)
            result.onSuccess { response ->
                _uiState.value = ScanUiState.Success(response, qrData)
            }.onFailure { error ->
                _uiState.value = ScanUiState.Error(error.localizedMessage ?: "Analysis failed")
            }
        }
    }

    fun dismissResult() {
        _uiState.value = ScanUiState.Idle
        lastScannedQr = null
    }
}

