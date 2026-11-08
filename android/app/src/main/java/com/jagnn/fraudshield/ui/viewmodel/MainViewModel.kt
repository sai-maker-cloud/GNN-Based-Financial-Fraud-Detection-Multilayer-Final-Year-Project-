package com.jagnn.fraudshield.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.jagnn.fraudshield.data.api.RetrofitClient
import com.jagnn.fraudshield.data.model.AuditItem
import com.jagnn.fraudshield.data.repository.FraudRepository
import com.jagnn.fraudshield.data.repository.PreferenceRepository
import com.jagnn.fraudshield.utils.LocaleHelper
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val prefRepo = PreferenceRepository(application)
    val fraudRepo = FraudRepository()

    val currentLanguage: StateFlow<String> = prefRepo.languageFlow
        .stateIn(viewModelScope, SharingStarted.Eagerly, prefRepo.initialLanguage)

    val currentTheme: StateFlow<String> = prefRepo.themeFlow
        .stateIn(viewModelScope, SharingStarted.Eagerly, "system")

    val backendUrl: StateFlow<String> = prefRepo.backendUrlFlow
        .stateIn(viewModelScope, SharingStarted.Eagerly, prefRepo.initialBackendUrl)

    val auditList: StateFlow<List<AuditItem>> = fraudRepo.auditList

    // Start with false (do not fake online before checking!)
    private val _isBackendOnline = MutableStateFlow(false)
    val isBackendOnline: StateFlow<Boolean> = _isBackendOnline.asStateFlow()

    init {
        // Continuous background health watcher: immediately polls and reconnects if server restarts
        viewModelScope.launch {
            while (true) {
                checkBackendHealth()
                val nextDelay = if (_isBackendOnline.value) 12000L else 3500L
                delay(nextDelay)
            }
        }
    }

    fun checkBackendHealth() {
        viewModelScope.launch {
            val configuredTarget = backendUrl.value

            // Candidates to probe: configured URL first, then Laptop Wi-Fi IP, then USB localhost, then Emulator
            val candidates = listOf(
                configuredTarget,
                "http://10.251.156.185:8000/",
                "http://127.0.0.1:8000/",
                "http://10.0.2.2:8000/"
            ).distinct()

            for (candidate in candidates) {
                if (tryProbeHealth(candidate)) {
                    if (candidate != configuredTarget) {
                        prefRepo.saveBackendUrl(candidate)
                    }
                    _isBackendOnline.value = true
                    return@launch
                }
            }

            // Server not responding on any tested address
            _isBackendOnline.value = false
        }
    }

    private suspend fun tryProbeHealth(candidateUrl: String): Boolean {
        return try {
            val api = RetrofitClient.getService(candidateUrl)
            val resp = api.checkHealth()
            val status = resp.body()?.status?.lowercase() ?: ""
            resp.isSuccessful && (status == "healthy" || status == "active" || resp.body()?.modelsLoaded == true)
        } catch (_: Exception) {
            false
        }
    }

    fun setLanguage(languageCode: String) {
        viewModelScope.launch {
            prefRepo.saveLanguage(languageCode)
        }
    }

    fun setTheme(themeMode: String) {
        viewModelScope.launch {
            prefRepo.saveTheme(themeMode)
        }
    }

    fun setBackendUrl(url: String) {
        viewModelScope.launch {
            prefRepo.saveBackendUrl(url)
            checkBackendHealth()
        }
    }

    fun getNativeLanguageName(code: String): String {
        return LocaleHelper.SUPPORTED_LANGUAGES.find { it.code == code }?.nativeName ?: "English"
    }
}
