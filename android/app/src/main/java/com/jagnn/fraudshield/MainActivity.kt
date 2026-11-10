package com.jagnn.fraudshield

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.LocalActivityResultRegistryOwner
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.animation.*
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.jagnn.fraudshield.ui.components.RiskShieldModal
import com.jagnn.fraudshield.ui.screens.HomeScreen
import com.jagnn.fraudshield.ui.screens.ScannerScreen
import com.jagnn.fraudshield.ui.screens.SettingsScreen
import com.jagnn.fraudshield.ui.theme.FraudShieldTheme
import com.jagnn.fraudshield.ui.viewmodel.MainViewModel
import com.jagnn.fraudshield.ui.viewmodel.ScanUiState
import com.jagnn.fraudshield.ui.viewmodel.ScannerViewModel
import com.jagnn.fraudshield.ui.viewmodel.ScannerViewModelFactory
import com.jagnn.fraudshield.data.repository.DeviceBlacklistManager
import com.jagnn.fraudshield.utils.LocaleHelper
import com.jagnn.fraudshield.utils.UPIIntentHandler

class MainActivity : ComponentActivity() {

    companion object {
        // Shared anti-loop tracking across any Activity instance recreation
        private var lastExternalUri: String? = null
        private var lastExternalUriTime: Long = 0
    }

    private val mainViewModel: MainViewModel by viewModels()
    private val scannerViewModel: ScannerViewModel by viewModels {
        ScannerViewModelFactory(mainViewModel.fraudRepo, application)
    }

    override fun attachBaseContext(newBase: Context) {
        val sharedPrefs = newBase.getSharedPreferences("fraudshield_prefs", Context.MODE_PRIVATE)
        val savedLang = sharedPrefs.getString("app_language", "en") ?: "en"
        val localizedContext = LocaleHelper.applyLocale(newBase, savedLang)
        super.attachBaseContext(localizedContext)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleIncomingIntent(intent)

        setContent {
            val currentLanguage by mainViewModel.currentLanguage.collectAsState()
            val currentTheme by mainViewModel.currentTheme.collectAsState()
            val backendUrl by mainViewModel.backendUrl.collectAsState()
            val auditList by mainViewModel.auditList.collectAsState()
            val isOnline by mainViewModel.isBackendOnline.collectAsState()

            val isDark = when (currentTheme) {
                "light" -> false
                "dark" -> true
                else -> isSystemInDarkTheme()
            }

            // Dynamic reactive locale composition for real-time translation across the entire app
            val localizedConfig = remember(currentLanguage) {
                val locale = java.util.Locale(currentLanguage)
                java.util.Locale.setDefault(locale)
                val config = resources.configuration
                config.setLocale(locale)
                config.setLayoutDirection(locale)
                @Suppress("DEPRECATION")
                resources.updateConfiguration(config, resources.displayMetrics)
                LocaleHelper.getLocalizedConfiguration(resources.configuration, currentLanguage)
            }
            val localizedContext = remember(currentLanguage) {
                LocaleHelper.applyLocale(this@MainActivity, currentLanguage)
            }

            CompositionLocalProvider(
                LocalConfiguration provides localizedConfig,
                LocalContext provides localizedContext,
                LocalActivityResultRegistryOwner provides this@MainActivity
            ) {
                FraudShieldTheme(darkTheme = isDark) {
                    Surface(modifier = Modifier.fillMaxSize()) {
                        val navController = rememberNavController()
                        val uiState by scannerViewModel.uiState.collectAsState()
                        val navBackStackEntry by navController.currentBackStackEntryAsState()
                        val currentRoute = navBackStackEntry?.destination?.route

                        Box(modifier = Modifier.fillMaxSize()) {
                            NavHost(
                                navController = navController,
                                startDestination = "home",
                                enterTransition = { fadeIn() + slideIntoContainer(AnimatedContentTransitionScope.SlideDirection.Start) },
                                exitTransition = { fadeOut() + slideOutOfContainer(AnimatedContentTransitionScope.SlideDirection.Start) },
                                popEnterTransition = { fadeIn() + slideIntoContainer(AnimatedContentTransitionScope.SlideDirection.End) },
                                popExitTransition = { fadeOut() + slideOutOfContainer(AnimatedContentTransitionScope.SlideDirection.End) }
                            ) {
                                composable("home") {
                                    HomeScreen(
                                        isOnline = isOnline,
                                        currentLanguageCode = currentLanguage,
                                        currentLanguageNative = mainViewModel.getNativeLanguageName(currentLanguage),
                                        isDarkTheme = isDark,
                                        audits = auditList,
                                        onOpenScanner = { navController.navigate("scanner") },
                                        onToggleTheme = { mainViewModel.setTheme(if (isDark) "light" else "dark") },
                                        onLanguageChange = { newLang ->
                                            mainViewModel.setLanguage(newLang)
                                        },
                                        onSettingsClick = { navController.navigate("settings") },
                                        onAuditClick = { auditItem ->
                                            // Directly analyze without navigating to camera scanner
                                            scannerViewModel.onQrScanned(auditItem.rawQr, backendUrl)
                                        },
                                        onManualCheckSubmit = { payload ->
                                            // Directly analyze without navigating to camera scanner
                                            scannerViewModel.onQrScanned(payload, backendUrl)
                                        },
                                        onRefreshHealth = { mainViewModel.checkBackendHealth() }
                                    )
                                }

                                composable("scanner") {
                                    ScannerScreen(
                                        activity = this@MainActivity,
                                        viewModel = scannerViewModel,
                                        backendUrl = backendUrl,
                                        onBackClick = { navController.popBackStack() }
                                    )
                                }

                                composable("settings") {
                                    SettingsScreen(
                                        currentLanguage = currentLanguage,
                                        currentTheme = currentTheme,
                                        currentBackendUrl = backendUrl,
                                        fraudRepository = mainViewModel.fraudRepo,
                                        onLanguageChange = { newLang ->
                                            mainViewModel.setLanguage(newLang)
                                        },
                                        onThemeChange = { mainViewModel.setTheme(it) },
                                        onBackendUrlChange = { mainViewModel.setBackendUrl(it) },
                                        onBackClick = { navController.popBackStack() }
                                    )
                                }
                            }

                            // Global Explainable AI Risk Shield Modal (works from Home, Scanner, Settings, & external link clicks)
                            if (uiState is ScanUiState.Success) {
                                val success = uiState as ScanUiState.Success
                                RiskShieldModal(
                                    response = success.response,
                                    rawQr = success.rawQr,
                                    onReportThreat = { entity, entityType, reason, score ->
                                        scannerViewModel.reportThreatToServer(
                                            entity = entity,
                                            entityType = entityType,
                                            reason = reason,
                                            riskScore = score,
                                            baseUrl = backendUrl
                                        )
                                    },
                                    onDismiss = { scannerViewModel.dismissResult() }
                                )
                            }

                            // Global Analyzing Progress Dialog (ScannerScreen renders its own camera overlay indicator)
                            if (uiState is ScanUiState.Analyzing && currentRoute != "scanner") {
                                AlertDialog(
                                    onDismissRequest = {},
                                    confirmButton = {},
                                    shape = RoundedCornerShape(20.dp),
                                    text = {
                                        Row(
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .padding(16.dp),
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            CircularProgressIndicator(
                                                modifier = Modifier.size(36.dp),
                                                color = MaterialTheme.colorScheme.primary
                                            )
                                            Spacer(modifier = Modifier.width(18.dp))
                                            Text(
                                                text = "Analyzing with AI Gatekeeper...",
                                                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold)
                                            )
                                        }
                                    }
                                )
                            }

                            // Global Error Notice
                            if (uiState is ScanUiState.Error) {
                                val errorState = uiState as ScanUiState.Error
                                AlertDialog(
                                    onDismissRequest = { scannerViewModel.dismissResult() },
                                    title = { Text("AI Gatekeeper Notice") },
                                    text = { Text(errorState.message) },
                                    confirmButton = {
                                        Button(onClick = { scannerViewModel.dismissResult() }) {
                                            Text("OK")
                                        }
                                    }
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: android.content.Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIncomingIntent(intent)
    }

    private fun handleIncomingIntent(intent: android.content.Intent?) {
        val uri = intent?.data ?: return
        val rawUriString = uri.toString().trim()
        if (rawUriString.isBlank()) return

        // Consume the intent data immediately to prevent re-processing
        // on activity recreation (config changes, etc.)
        intent.data = null

        val now = System.currentTimeMillis()

        // ── Anti-loop guard ──────────────────────────────────────────────
        // If this exact URI was already processed within the last 10 seconds,
        // it means our auto-launch looped back to FraudShield (because we are
        // set as the default browser). Skip re-scanning entirely and forward
        // directly to an external browser or UPI payment app.
        if (rawUriString == lastExternalUri && (now - lastExternalUriTime) < 10_000) {
            if (!DeviceBlacklistManager.isBlocked(rawUriString)) {
                if (rawUriString.startsWith("upi://", ignoreCase = true) ||
                    rawUriString.contains("pa=", ignoreCase = true)
                ) {
                    UPIIntentHandler.launchUpiPayment(this, rawUriString)
                } else {
                    UPIIntentHandler.launchSafeUrl(this, rawUriString)
                }
            }
            return
        }

        lastExternalUri = rawUriString
        lastExternalUriTime = now

        // Normal flow: run through AI Gatekeeper scan
        scannerViewModel.onQrScanned(rawUriString, mainViewModel.backendUrl.value)
    }
}
