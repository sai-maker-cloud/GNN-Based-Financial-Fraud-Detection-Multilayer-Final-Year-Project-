package com.jagnn.fraudshield.ui.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountTree
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Dangerous
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.OpenInBrowser
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import android.widget.Toast
import com.jagnn.fraudshield.R
import com.jagnn.fraudshield.data.model.QRAnalyzeResponse
import com.jagnn.fraudshield.ui.theme.*
import com.jagnn.fraudshield.utils.SoundVibrationHelper
import com.jagnn.fraudshield.utils.UPIIntentHandler

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RiskShieldModal(
    response: QRAnalyzeResponse?,
    rawQr: String,
    onDismiss: () -> Unit
) {
    if (response == null) return

    val context = LocalContext.current
    val decision = response.normalizedDecision
    val riskScore = response.riskScore
    val payloadType = response.payloadType
    val cleanPayload = rawQr.trim()

    // Determine payload nature:
    // Pure Web URL vs. Payment URL (handled by JA-GNN) vs. pure UPI payment
    val isPaymentUrl = payloadType.contains("PAYMENT") ||
            (payloadType.contains("URL") && (cleanPayload.contains("pa=") || cleanPayload.contains("amount=") || cleanPayload.contains("am="))) ||
            (response.summaryReason?.contains("JA-GNN", ignoreCase = true) == true) ||
            (response.displayReasons.any { it.contains("JA-GNN", ignoreCase = true) })

    val isPureWebUrl = !isPaymentUrl &&
            !payloadType.contains("UPI") &&
            !cleanPayload.startsWith("upi://", ignoreCase = true) &&
            !cleanPayload.contains("pa=") &&
            (payloadType == "URL" || UPIIntentHandler.isWebUrl(cleanPayload))

    var autoLaunched by remember(response, cleanPayload) { mutableStateOf(false) }

    // Trigger haptic feedback & auto-launch on safe, auto-blacklist on danger
    LaunchedEffect(response, cleanPayload) {
        when (decision) {
            "ALLOW" -> {
                SoundVibrationHelper.vibrateSuccess(context)
                if (!autoLaunched) {
                    autoLaunched = true
                    // Brief visual confirmation delay (450ms) so user sees the green "Verified Safe" shield
                    delay(450)
                    if (isPureWebUrl) {
                        Toast.makeText(context, "✅ Verified Safe! Opening Browser...", Toast.LENGTH_SHORT).show()
                        UPIIntentHandler.launchSafeUrl(context, cleanPayload)
                    } else {
                        Toast.makeText(context, "✅ Verified Safe! Opening Payment Gateway...", Toast.LENGTH_SHORT).show()
                        UPIIntentHandler.launchUpiPayment(context, cleanPayload)
                    }
                    onDismiss()
                }
            }
            "WARN" -> SoundVibrationHelper.vibrateWarning(context)
            else -> {
                SoundVibrationHelper.vibrateFraudAlert(context)
                // DANGER / BLOCK: Auto-record permanently into device hard blacklist
                com.jagnn.fraudshield.data.repository.DeviceBlacklistManager.blockEntity(
                    rawPayload = cleanPayload,
                    domainOrTarget = response.targetEntity,
                    reason = response.summaryReason ?: "Hard blocked by FraudShield AI"
                )
            }
        }
    }

    val (primaryColor, containerColor, icon) = when (decision) {
        "ALLOW" -> Triple(ShieldGreen, ShieldGreenContainer, Icons.Default.CheckCircle)
        "WARN" -> Triple(ShieldAmber, ShieldAmberContainer, Icons.Default.Warning)
        else -> Triple(ShieldRed, ShieldRedContainer, Icons.Default.Dangerous)
    }

    // Determine AI Engine attribution based on payload and reasoning
    val aiEngineAttribution = when {
        isPaymentUrl -> "JA-GNN Financial Graph Intelligence"
        payloadType.contains("COLLECT") || cleanPayload.contains("mode=01") -> "UPI Protocol Tamper Shield"
        payloadType.contains("UPI") -> "JA-GNN Financial Graph Intelligence"
        else -> "Perimeter URL Phishing Classifier"
    }

    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = if (decision == "BLOCK") 1.14f else 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 750, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulseScale"
    )

    ModalBottomSheet(
        onDismissRequest = {
            if (decision == "WARN") {
                // If user dismissed / canceled a suspicious warning without proceeding, permanently hard-block it!
                com.jagnn.fraudshield.data.repository.DeviceBlacklistManager.blockEntity(
                    rawPayload = cleanPayload,
                    domainOrTarget = response.targetEntity,
                    reason = "Suspicious threat dismissed/cancelled by user. Permanently hard-blocked on this device."
                )
            }
            onDismiss()
        },
        shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp),
        containerColor = MaterialTheme.colorScheme.surface
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp)
                .padding(bottom = 36.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Explainable AI Engine Attribution Tag
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = if (aiEngineAttribution.contains("URL")) Icons.Default.Language else Icons.Default.AccountTree,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(14.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = aiEngineAttribution,
                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold),
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Animated Status Shield Icon
            Box(
                modifier = Modifier
                    .size(76.dp)
                    .scale(pulseScale)
                    .background(containerColor, CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = decision,
                    tint = primaryColor,
                    modifier = Modifier.size(42.dp)
                )
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Title
            val titleText = when (decision) {
                "ALLOW" -> if (isPureWebUrl) stringResource(R.string.decision_url_safe_title) else stringResource(R.string.decision_allow_title)
                "WARN" -> stringResource(R.string.decision_warn_title)
                else -> stringResource(R.string.decision_block_title)
            }

            Text(
                text = titleText,
                style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(6.dp))

            // Description
            val descText = when (decision) {
                "ALLOW" -> if (isPureWebUrl) stringResource(R.string.decision_url_safe_desc) else stringResource(R.string.decision_allow_desc)
                "WARN" -> response.clientAction?.warningMessage ?: response.summaryReason ?: stringResource(R.string.decision_warn_desc)
                else -> response.clientAction?.warningMessage ?: response.summaryReason ?: stringResource(R.string.decision_block_desc)
            }

            Text(
                text = descText,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(18.dp))

            // Risk Score Meter Card
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = stringResource(R.string.risk_score),
                            style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = "${(riskScore * 100).toInt()}%",
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                            color = primaryColor
                        )
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    LinearProgressIndicator(
                        progress = { riskScore },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(8.dp),
                        color = primaryColor,
                        trackColor = containerColor
                    )
                }
            }

            // Explainable AI Factors & Reasoning
            Spacer(modifier = Modifier.height(14.dp))
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(containerColor.copy(alpha = 0.35f), RoundedCornerShape(14.dp))
                    .padding(12.dp)
            ) {
                Text(
                    text = stringResource(R.string.detected_threats),
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                    color = primaryColor
                )
                Spacer(modifier = Modifier.height(6.dp))

                if (response.displayReasons.isNotEmpty()) {
                    response.displayReasons.forEach { reason ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 3.dp),
                            verticalAlignment = Alignment.Top
                        ) {
                            Text(
                                text = "• ",
                                color = primaryColor,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = reason,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }
                    }
                } else {
                    Text(
                        text = "Clean transaction parameters verified against neural graph & domain databases.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            // Target URI Preview (Non-clickable if blocked)
            Spacer(modifier = Modifier.height(12.dp))
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(10.dp),
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f)
            ) {
                Text(
                    text = "Payload: " + if (cleanPayload.length > 55) cleanPayload.take(55) + "…" else cleanPayload,
                    style = MaterialTheme.typography.labelSmall.copy(fontSize = 11.sp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(8.dp),
                    maxLines = 1
                )
            }

            Spacer(modifier = Modifier.height(20.dp))

            // Action Buttons with Strict Hard Block Enforcement
            when (decision) {
                "ALLOW" -> {
                    if (isPureWebUrl) {
                        // SAFE GENERIC WEB URL: Redirect to Browser
                        Button(
                            onClick = {
                                UPIIntentHandler.launchSafeUrl(context, cleanPayload)
                                onDismiss()
                            },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(52.dp),
                            shape = RoundedCornerShape(26.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = ShieldGreen)
                        ) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(16.dp),
                                color = Color.White,
                                strokeWidth = 2.dp
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Text(
                                text = "Verified Safe • Opening Browser...",
                                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                                color = Color.White
                            )
                        }
                    } else {
                        // SAFE PAYMENT (UPI or Payment URL): Provide Payment App & Browser Redirection
                        Button(
                            onClick = {
                                UPIIntentHandler.launchUpiPayment(context, cleanPayload)
                                onDismiss()
                            },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(52.dp),
                            shape = RoundedCornerShape(26.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = ShieldGreen)
                        ) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(16.dp),
                                color = Color.White,
                                strokeWidth = 2.dp
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Text(
                                text = "Verified Safe • Launching Payment...",
                                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                                color = Color.White
                            )
                        }

                        // If it's an HTTP payment URL, also offer direct browser checkout link
                        if (cleanPayload.startsWith("http://", ignoreCase = true) || cleanPayload.startsWith("https://", ignoreCase = true)) {
                            Spacer(modifier = Modifier.height(10.dp))
                            OutlinedButton(
                                onClick = {
                                    UPIIntentHandler.launchSafeUrl(context, cleanPayload)
                                    onDismiss()
                                },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(48.dp),
                                shape = RoundedCornerShape(24.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Default.OpenInBrowser,
                                    contentDescription = null,
                                    modifier = Modifier.size(16.dp)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = "Open Payment Page in Browser",
                                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold)
                                )
                            }
                        }
                    }
                }

                "WARN" -> {
                    // SUSPICIOUS: Allow cancellation or cautious override
                    Button(
                        onClick = {
                            // User unproceeds / cancels suspicious transaction -> PERMANENTLY HARD BLOCK ON THIS DEVICE!
                            com.jagnn.fraudshield.data.repository.DeviceBlacklistManager.blockEntity(
                                rawPayload = cleanPayload,
                                domainOrTarget = response.targetEntity,
                                reason = "Suspicious threat rejected by user. Permanently hard-blocked on this device."
                            )
                            android.widget.Toast.makeText(
                                context,
                                "🔒 Threat permanently blacklisted on this device. Future access blocked.",
                                android.widget.Toast.LENGTH_LONG
                            ).show()
                            onDismiss()
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(50.dp),
                        shape = RoundedCornerShape(25.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                    ) {
                        Text(
                            text = if (isPureWebUrl) "Cancel & Block Threat" else stringResource(R.string.btn_cancel_payment),
                            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    OutlinedButton(
                        onClick = {
                            if (isPureWebUrl) {
                                UPIIntentHandler.launchSafeUrl(context, cleanPayload)
                            } else {
                                UPIIntentHandler.launchUpiPayment(context, cleanPayload)
                            }
                            onDismiss()
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(50.dp),
                        shape = RoundedCornerShape(25.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = ShieldAmber)
                    ) {
                        Text(
                            text = if (isPureWebUrl) stringResource(R.string.btn_proceed_link_anyway) else stringResource(R.string.btn_proceed_anyway),
                            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold)
                        )
                    }
                }

                else -> { // BLOCK: STRICT HARD BLOCK
                    // Show Hard Block Warning Banner
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        color = ShieldRedContainer
                    ) {
                        Row(
                            modifier = Modifier.padding(10.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.Lock,
                                contentDescription = "Locked",
                                tint = ShieldRed,
                                modifier = Modifier.size(18.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = stringResource(R.string.hard_block_notice),
                                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                color = ShieldRed
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // ONLY dismiss alert is provided. Redirection to browser or payment app is completely blocked!
                    Button(
                        onClick = onDismiss,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(52.dp),
                        shape = RoundedCornerShape(26.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = ShieldRed)
                    ) {
                        Text(
                            text = stringResource(R.string.btn_dismiss),
                            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                            color = Color.White
                        )
                    }
                }
            }
        }
    }
}
