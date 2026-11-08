package com.jagnn.fraudshield.ui.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.FlashOff
import androidx.compose.material.icons.filled.FlashOn
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.jagnn.fraudshield.R
import com.jagnn.fraudshield.ui.theme.GPayBlue

@Composable
fun ScannerOverlay(
    isFlashOn: Boolean,
    isAnalyzing: Boolean,
    onBackClick: () -> Unit,
    onFlashToggle: () -> Unit,
    onManualQrSubmit: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    var showManualDialog by remember { mutableStateOf(false) }

    // Laser beam vertical animation
    val infiniteTransition = rememberInfiniteTransition(label = "laser")
    val laserYRatio by infiniteTransition.animateFloat(
        initialValue = 0.05f,
        targetValue = 0.95f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1800, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "laserYRatio"
    )

    Box(modifier = modifier.fillMaxSize()) {
        // Top Toolbar
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 40.dp, start = 16.dp, end = 16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(
                onClick = onBackClick,
                modifier = Modifier
                    .size(44.dp)
                    .background(Color.Black.copy(alpha = 0.45f), CircleShape)
            ) {
                Icon(
                    imageVector = Icons.Default.ArrowBack,
                    contentDescription = "Back",
                    tint = Color.White
                )
            }

            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                IconButton(
                    onClick = onFlashToggle,
                    modifier = Modifier
                        .size(44.dp)
                        .background(Color.Black.copy(alpha = 0.45f), CircleShape)
                ) {
                    Icon(
                        imageVector = if (isFlashOn) Icons.Default.FlashOn else Icons.Default.FlashOff,
                        contentDescription = "Flash",
                        tint = if (isFlashOn) GPayBlue else Color.White
                    )
                }

                IconButton(
                    onClick = { showManualDialog = true },
                    modifier = Modifier
                        .size(44.dp)
                        .background(Color.Black.copy(alpha = 0.45f), CircleShape)
                ) {
                    Icon(
                        imageVector = Icons.Default.PhotoLibrary,
                        contentDescription = "Manual/Gallery",
                        tint = Color.White
                    )
                }
            }
        }

        // Scanner Reticle Target Frame (Center)
        Box(
            modifier = Modifier
                .size(280.dp)
                .align(Alignment.Center)
                .clip(RoundedCornerShape(24.dp))
                .border(2.5.dp, Color.White.copy(alpha = 0.85f), RoundedCornerShape(24.dp))
        ) {
            // Animated Laser Sweep Beam
            Canvas(modifier = Modifier.fillMaxSize()) {
                val yPos = size.height * laserYRatio
                drawLine(
                    color = GPayBlue,
                    start = Offset(0f, yPos),
                    end = Offset(size.width, yPos),
                    strokeWidth = 3.dp.toPx()
                )
            }
        }

        // Instruction and Status (Bottom)
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .padding(bottom = 60.dp, start = 24.dp, end = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            if (isAnalyzing) {
                CircularProgressIndicator(
                    modifier = Modifier.size(36.dp),
                    color = GPayBlue,
                    strokeWidth = 3.5.dp
                )
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = stringResource(R.string.scanner_analyzing),
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold),
                    color = Color.White,
                    textAlign = TextAlign.Center
                )
            } else {
                Surface(
                    shape = RoundedCornerShape(20.dp),
                    color = Color.Black.copy(alpha = 0.6f)
                ) {
                    Text(
                        text = stringResource(R.string.scanner_instruction),
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color.White,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                    )
                }

                Spacer(modifier = Modifier.height(14.dp))

                OutlinedButton(
                    onClick = { showManualDialog = true },
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White),
                    border = ButtonDefaults.outlinedButtonBorder.copy(brush = androidx.compose.ui.graphics.SolidColor(Color.White.copy(alpha = 0.7f)))
                ) {
                    Text(text = "Paste / Type QR Payload (Demo Test)", fontSize = 12.sp)
                }
            }
        }
    }

    // Manual QR / UPI Input Dialog for testing
    if (showManualDialog) {
        var inputPayload by remember { mutableStateOf("upi://pay?pa=dmart_retail@hdfc&pn=DMart%20Store&am=640.00&cu=INR") }

        AlertDialog(
            onDismissRequest = { showManualDialog = false },
            title = { Text(text = "Test QR Payload") },
            text = {
                Column {
                    Text(
                        text = "Paste any QR payload (UPI URI, URL, or money mule text) to analyze with JA-GNN:",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    OutlinedTextField(
                        value = inputPayload,
                        onValueChange = { inputPayload = it },
                        modifier = Modifier.fillMaxWidth(),
                        maxLines = 4
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            FilterChip(
                                selected = false,
                                onClick = { inputPayload = "https://google.com" },
                                label = { Text("Safe URL", fontSize = 10.sp) }
                            )
                            FilterChip(
                                selected = false,
                                onClick = { inputPayload = "https://upiqr.in/pay?pa=rahul_kumar88@ybl&am=18500" },
                                label = { Text("Payment URL (JA-GNN)", fontSize = 10.sp) }
                            )
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            FilterChip(
                                selected = false,
                                onClick = { inputPayload = "upi://pay?pa=dmart_retail@hdfc&pn=DMart&am=499" },
                                label = { Text("Safe Store", fontSize = 10.sp) }
                            )
                            FilterChip(
                                selected = false,
                                onClick = { inputPayload = "upi://pay?pa=rahul_kumar88@ybl&am=18500" },
                                label = { Text("Mule Scam", fontSize = 10.sp) }
                            )
                        }
                    }
                }
            },
            confirmButton = {
                Button(onClick = {
                    showManualDialog = false
                    onManualQrSubmit(inputPayload)
                }) {
                    Text("Analyze with JA-GNN")
                }
            },
            dismissButton = {
                TextButton(onClick = { showManualDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }
}

