package com.jagnn.fraudshield.ui.components

import android.content.ClipboardManager
import android.content.Context
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentPaste
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.jagnn.fraudshield.R
import com.jagnn.fraudshield.ui.theme.GPayBlue

@Composable
fun ManualCheckCard(
    onAnalyzeSubmit: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    var inputPayload by remember { mutableStateOf("") }

    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 1.dp
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            // Card Title & Subtitle
            Text(
                text = stringResource(R.string.manual_check_title),
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                color = MaterialTheme.colorScheme.onSurface
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = stringResource(R.string.manual_check_desc),
                style = MaterialTheme.typography.bodySmall.copy(fontSize = 11.5.sp),
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(14.dp))

            // URL / UPI Text Input Field with Paste Icon
            OutlinedTextField(
                value = inputPayload,
                onValueChange = { inputPayload = it },
                placeholder = {
                    Text(
                        text = stringResource(R.string.manual_check_hint),
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
                    )
                },
                trailingIcon = {
                    IconButton(
                        onClick = {
                            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
                            val clipData = clipboard?.primaryClip?.getItemAt(0)?.text?.toString()
                            if (!clipData.isNullOrBlank()) {
                                inputPayload = clipData
                            }
                        }
                    ) {
                        Icon(
                            imageVector = Icons.Default.ContentPaste,
                            contentDescription = stringResource(R.string.paste_clipboard),
                            tint = GPayBlue
                        )
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                maxLines = 3,
                shape = RoundedCornerShape(14.dp)
            )

            Spacer(modifier = Modifier.height(10.dp))

            // Test Presets Row
            Text(
                text = stringResource(R.string.preset_samples),
                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold),
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(6.dp))

            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    FilterChip(
                        selected = false,
                        onClick = { inputPayload = "https://google.com" },
                        label = { Text(stringResource(R.string.preset_safe_url), fontSize = 10.5.sp) }
                    )
                    FilterChip(
                        selected = false,
                        onClick = { inputPayload = "https://upiqr.in/pay?pa=rahul_kumar88@ybl&am=18500" },
                        label = { Text(stringResource(R.string.preset_payment_url), fontSize = 10.5.sp) }
                    )
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    FilterChip(
                        selected = false,
                        onClick = { inputPayload = "upi://pay?pa=dmart_retail@hdfc&pn=DMart%20Store&am=640.00&mc=5411" },
                        label = { Text(stringResource(R.string.preset_safe), fontSize = 10.5.sp) }
                    )
                    FilterChip(
                        selected = false,
                        onClick = { inputPayload = "https://secure-banking-login.phishing-site.tk/verify?token=abc123" },
                        label = { Text(stringResource(R.string.preset_phishing), fontSize = 10.5.sp) }
                    )
                    FilterChip(
                        selected = false,
                        onClick = { inputPayload = "upi://pay?pa=rahul_kumar88@ybl&pn=FastTransfer&am=18500" },
                        label = { Text(stringResource(R.string.preset_mule), fontSize = 10.5.sp) }
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Primary Check Action Button
            Button(
                onClick = {
                    if (inputPayload.isNotBlank()) {
                        onAnalyzeSubmit(inputPayload.trim())
                    }
                },
                enabled = inputPayload.isNotBlank(),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp),
                shape = RoundedCornerShape(24.dp),
                colors = ButtonDefaults.buttonColors(containerColor = GPayBlue)
            ) {
                Icon(
                    imageVector = Icons.Default.Search,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = stringResource(R.string.btn_check_ai),
                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold, color = Color.White)
                )
            }
        }
    }
}

