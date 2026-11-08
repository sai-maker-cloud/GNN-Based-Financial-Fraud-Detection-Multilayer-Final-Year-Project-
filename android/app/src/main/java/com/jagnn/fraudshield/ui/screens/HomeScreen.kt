package com.jagnn.fraudshield.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.jagnn.fraudshield.R
import com.jagnn.fraudshield.data.model.AuditItem
import com.jagnn.fraudshield.ui.components.*
import com.jagnn.fraudshield.ui.theme.GPayBlue
import com.jagnn.fraudshield.utils.LocaleHelper

@Composable
fun HomeScreen(
    isOnline: Boolean,
    currentLanguageCode: String,
    currentLanguageNative: String,
    isDarkTheme: Boolean,
    audits: List<AuditItem>,
    onOpenScanner: () -> Unit,
    onToggleTheme: () -> Unit,
    onLanguageChange: (String) -> Unit,
    onSettingsClick: () -> Unit,
    onAuditClick: (AuditItem) -> Unit,
    onManualCheckSubmit: (String) -> Unit,
    onRefreshHealth: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    var showLanguageDialog by remember { mutableStateOf(false) }
    var selectedFilter by remember { mutableStateOf("ALL") }

    val totalScanned = audits.size
    val totalBlocked = audits.count { it.decision == "BLOCK" }
    val totalSafe = audits.count { it.decision == "ALLOW" }

    val filteredAudits = when (selectedFilter) {
        "BLOCKED" -> audits.filter { it.decision == "BLOCK" }
        "SAFE" -> audits.filter { it.decision == "ALLOW" }
        else -> audits
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopGPayBar(
                currentLanguageNative = currentLanguageNative,
                isDarkTheme = isDarkTheme,
                onToggleTheme = onToggleTheme,
                onLanguageClick = { showLanguageDialog = true },
                onSettingsClick = onSettingsClick
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onOpenScanner,
                icon = {
                    Icon(
                        imageVector = Icons.Default.QrCodeScanner,
                        contentDescription = "Scan QR",
                        tint = Color.White
                    )
                },
                text = {
                    Text(
                        text = stringResource(R.string.scan_and_protect),
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                },
                containerColor = GPayBlue,
                shape = RoundedCornerShape(28.dp),
                elevation = FloatingActionButtonDefaults.elevation(6.dp)
            )
        }
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
            contentPadding = PaddingValues(bottom = 96.dp)
        ) {
            // 1. Live Engine Status Card (Counters & GNN Status)
            item {
                EngineStatusCard(
                    isOnline = isOnline,
                    totalScanned = totalScanned,
                    totalBlocked = totalBlocked,
                    totalSafe = totalSafe,
                    onCardClick = onRefreshHealth,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
                )
            }

            // 2. Camera Scan Action Hero Card
            item {
                Spacer(modifier = Modifier.height(10.dp))
                ScanActionCard(
                    onScanClick = onOpenScanner,
                    onPasteTestClick = {
                        // Quick shortcut to focus manual input or trigger demo
                        onManualCheckSubmit("upi://pay?pa=dmart_retail@hdfc&pn=DMart%20Store&am=640.00&mc=5411")
                    },
                    modifier = Modifier.padding(horizontal = 16.dp)
                )
            }

            // 3. Manual URL / QR Verification Input Field
            item {
                Spacer(modifier = Modifier.height(14.dp))
                ManualCheckCard(
                    onAnalyzeSubmit = onManualCheckSubmit,
                    modifier = Modifier.padding(horizontal = 16.dp)
                )
            }

            // 4. Security Layers Breakdown
            item {
                Spacer(modifier = Modifier.height(18.dp))
                SecurityLayersList(
                    modifier = Modifier.padding(horizontal = 16.dp)
                )
            }

            // 5. Audit History Header with Filter Chips
            item {
                Spacer(modifier = Modifier.height(20.dp))
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = stringResource(R.string.recent_scans),
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                        color = MaterialTheme.colorScheme.onSurface
                    )

                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        FilterChip(
                            selected = selectedFilter == "ALL",
                            onClick = { selectedFilter = "ALL" },
                            label = { Text(stringResource(R.string.filter_all), fontSize = 11.sp) }
                        )
                        FilterChip(
                            selected = selectedFilter == "BLOCKED",
                            onClick = { selectedFilter = "BLOCKED" },
                            label = { Text(stringResource(R.string.filter_blocked), fontSize = 11.sp) }
                        )
                        FilterChip(
                            selected = selectedFilter == "SAFE",
                            onClick = { selectedFilter = "SAFE" },
                            label = { Text(stringResource(R.string.filter_safe), fontSize = 11.sp) }
                        )
                    }
                }
            }

            // 6. Audit Cards List
            item {
                Spacer(modifier = Modifier.height(10.dp))
                if (filteredAudits.isEmpty()) {
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 16.dp),
                        shape = RoundedCornerShape(16.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f)
                    ) {
                        Text(
                            text = stringResource(R.string.no_audits),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(20.dp),
                            textAlign = androidx.compose.ui.text.style.TextAlign.Center
                        )
                    }
                } else {
                    AuditHistory(
                        audits = filteredAudits,
                        onItemClick = onAuditClick
                    )
                }
            }
        }
    }

    // Direct One-Click Language Selection Dialog
    if (showLanguageDialog) {
        AlertDialog(
            onDismissRequest = { showLanguageDialog = false },
            title = { Text(text = stringResource(R.string.setting_language), fontWeight = FontWeight.Bold) },
            text = {
                Column {
                    LocaleHelper.SUPPORTED_LANGUAGES.forEach { lang ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    onLanguageChange(lang.code)
                                    showLanguageDialog = false
                                }
                                .padding(vertical = 12.dp, horizontal = 4.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = lang.nativeName,
                                    style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.SemiBold)
                                )
                                Text(
                                    text = lang.englishName,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            if (currentLanguageCode == lang.code) {
                                Icon(
                                    imageVector = Icons.Default.Check,
                                    contentDescription = "Selected",
                                    tint = MaterialTheme.colorScheme.primary
                                )
                            }
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showLanguageDialog = false }) {
                    Text("Close")
                }
            }
        )
    }
}
