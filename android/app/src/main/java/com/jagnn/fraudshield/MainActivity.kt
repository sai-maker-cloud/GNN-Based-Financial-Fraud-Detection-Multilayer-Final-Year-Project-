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
import com.jagnn.fraudshield.utils.LocaleHelper

class MainActivity : ComponentActivity() {

    private val mainViewModel: MainViewModel by viewModels()
    private val scannerViewModel: ScannerViewModel by viewModels {
        ScannerViewModelFactory(mainViewModel.fraudRepo)
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

                        NavHost(
                            navController = navController,
                            startDestination = "home",
                            enterTransition = { fadeIn() + slideIntoContainer(AnimatedContentTransitionScope.SlideDirection.Start) },
                            exitTransition = { fadeOut() + slideOutOfContainer(AnimatedContentTransitionScope.SlideDirection.Start) },
                            popEnterTransition = { fadeIn() + slideIntoContainer(AnimatedContentTransitionScope.SlideDirection.End) },
                            popExitTransition = { fadeOut() + slideOutOfContainer(AnimatedContentTransitionScope.SlideDirection.End) }
                        ) {
                            composable("home") {
                                val uiState by scannerViewModel.uiState.collectAsState()

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

                                // In-place Explainable AI Risk Shield Modal right on the Dashboard
                                if (uiState is ScanUiState.Success) {
                                    val success = uiState as ScanUiState.Success
                                    RiskShieldModal(
                                        response = success.response,
                                        rawQr = success.rawQr,
                                        onDismiss = { scannerViewModel.dismissResult() }
                                    )
                                }

                                // In-place Analyzing Progress
                                if (uiState is ScanUiState.Analyzing) {
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
                                // In-place Error Notice
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
                                    onLanguageChange = { newLang ->
                                        mainViewModel.setLanguage(newLang)
                                    },
                                    onThemeChange = { mainViewModel.setTheme(it) },
                                    onBackendUrlChange = { mainViewModel.setBackendUrl(it) },
                                    onBackClick = { navController.popBackStack() }
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
        handleIncomingIntent(intent)
    }

    private fun handleIncomingIntent(intent: android.content.Intent?) {
        val uri = intent?.data ?: return
        val rawUriString = uri.toString().trim()
        if (rawUriString.isNotBlank()) {
            scannerViewModel.onQrScanned(rawUriString, mainViewModel.backendUrl.value)
        }
    }
}
