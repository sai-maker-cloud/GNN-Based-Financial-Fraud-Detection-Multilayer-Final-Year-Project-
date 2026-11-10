package com.jagnn.fraudshield.ui.screens

import android.Manifest
import android.app.role.RoleManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Palette
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material.icons.filled.Router
import androidx.compose.material.icons.filled.Security
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.jagnn.fraudshield.R
import com.jagnn.fraudshield.data.model.MerchantDto
import com.jagnn.fraudshield.data.repository.FraudRepository
import com.jagnn.fraudshield.ui.theme.ShieldGreen
import com.jagnn.fraudshield.ui.theme.ShieldGreenContainer
import com.jagnn.fraudshield.utils.LocaleHelper
import com.jagnn.fraudshield.utils.LocationHelper
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    currentLanguage: String,
    currentTheme: String,
    currentBackendUrl: String,
    fraudRepository: FraudRepository? = null,
    onLanguageChange: (String) -> Unit,
    onThemeChange: (String) -> Unit,
    onBackendUrlChange: (String) -> Unit,
    onBackClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var urlInput by remember(currentBackendUrl) { mutableStateOf(currentBackendUrl) }
    var showLanguageDialog by remember { mutableStateOf(false) }

    // Shopkeeper Store Counter QR Binding state
    var shopNameInput by remember { mutableStateOf("") }
    var shopQrOrVpaInput by remember { mutableStateOf("") }
    var isRegisteringShop by remember { mutableStateOf(false) }
    var registeredMerchants by remember { mutableStateOf<List<MerchantDto>>(emptyList()) }

    fun refreshMerchants(targetUrl: String = urlInput) {
        val repo = fraudRepository ?: return
        scope.launch {
            repo.fetchRegisteredMerchants(targetUrl).onSuccess { list ->
                registeredMerchants = list
            }
        }
    }

    LaunchedEffect(currentBackendUrl, fraudRepository) {
        refreshMerchants(currentBackendUrl)
    }

    suspend fun bindStoreWithCurrentGps() {
        val repo = fraudRepository ?: return
        isRegisteringShop = true
        try {
            val coords = LocationHelper.getCurrentCoordinates(context, timeoutMs = 2500L)
            if (coords == null) {
                Toast.makeText(
                    context,
                    "GPS unavailable. Please enable Device Location and retry.",
                    Toast.LENGTH_LONG
                ).show()
                return
            }
            val res = repo.registerMerchantCounter(
                shopName = shopNameInput,
                rawQrOrVpa = shopQrOrVpaInput,
                latitude = coords.latitude,
                longitude = coords.longitude,
                baseUrl = urlInput
            )
            res.onSuccess { msg ->
                Toast.makeText(context, "✅ $msg", Toast.LENGTH_LONG).show()
                shopNameInput = ""
                shopQrOrVpaInput = ""
                refreshMerchants()
            }.onFailure { err ->
                Toast.makeText(context, "Error: ${err.localizedMessage}", Toast.LENGTH_LONG).show()
            }
        } finally {
            isRegisteringShop = false
        }
    }

    val locationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { perms ->
        val granted = perms[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
            perms[Manifest.permission.ACCESS_COARSE_LOCATION] == true
        if (granted && shopNameInput.isNotBlank() && shopQrOrVpaInput.isNotBlank()) {
            scope.launch { bindStoreWithCurrentGps() }
        } else if (!granted) {
            Toast.makeText(context, "Location permission is required to lock QR to shop GPS.", Toast.LENGTH_LONG).show()
        }
    }

    var isDefaultGuardActive by remember {
        mutableStateOf(checkIsDefaultBrowser(context))
    }

    val roleLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) {
        isDefaultGuardActive = checkIsDefaultBrowser(context)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(text = stringResource(R.string.settings_title), fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(imageVector = Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        },
        modifier = modifier.fillMaxSize()
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 16.dp),
            contentPadding = PaddingValues(top = 8.dp, bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Language Selection Card
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(imageVector = Icons.Default.Language, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                            Spacer(modifier = Modifier.width(10.dp))
                            Text(
                                text = stringResource(R.string.setting_language),
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold)
                            )
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        val activeLang = LocaleHelper.SUPPORTED_LANGUAGES.find { it.code == currentLanguage }
                        OutlinedButton(
                            onClick = { showLanguageDialog = true },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text(
                                text = "${activeLang?.nativeName ?: "English"} (${activeLang?.englishName ?: "English"})",
                                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold)
                            )
                        }
                    }
                }
            }

            // Theme Mode Card
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(imageVector = Icons.Default.Palette, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                            Spacer(modifier = Modifier.width(10.dp))
                            Text(
                                text = stringResource(R.string.setting_theme),
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold)
                            )
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            ThemeChip(
                                label = stringResource(R.string.theme_system),
                                isSelected = currentTheme == "system",
                                onClick = { onThemeChange("system") },
                                modifier = Modifier.weight(1f)
                            )
                            ThemeChip(
                                label = stringResource(R.string.theme_light),
                                isSelected = currentTheme == "light",
                                onClick = { onThemeChange("light") },
                                modifier = Modifier.weight(1f)
                            )
                            ThemeChip(
                                label = stringResource(R.string.theme_dark),
                                isSelected = currentTheme == "dark",
                                onClick = { onThemeChange("dark") },
                                modifier = Modifier.weight(1f)
                            )
                        }
                    }
                }
            }

            // Backend Server Configuration Card
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(imageVector = Icons.Default.Router, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                            Spacer(modifier = Modifier.width(10.dp))
                            Text(
                                text = stringResource(R.string.setting_backend_url),
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold)
                            )
                        }

                        Spacer(modifier = Modifier.height(6.dp))

                        Text(
                            text = stringResource(R.string.backend_url_desc),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )

                        Spacer(modifier = Modifier.height(12.dp))

                        OutlinedTextField(
                            value = urlInput,
                            onValueChange = { urlInput = it },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true,
                            shape = RoundedCornerShape(12.dp)
                        )

                        Spacer(modifier = Modifier.height(10.dp))

                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            FilterChip(
                                selected = urlInput == "http://10.251.156.185:8000/",
                                onClick = { urlInput = "http://10.251.156.185:8000/" },
                                label = { Text("Wi-Fi PC") }
                            )
                            FilterChip(
                                selected = urlInput == "http://127.0.0.1:8000/",
                                onClick = { urlInput = "http://127.0.0.1:8000/" },
                                label = { Text("USB") }
                            )
                            FilterChip(
                                selected = urlInput == "http://10.0.2.2:8000/",
                                onClick = { urlInput = "http://10.0.2.2:8000/" },
                                label = { Text("Emulator") }
                            )
                        }

                        Spacer(modifier = Modifier.height(14.dp))

                        Button(
                            onClick = {
                                onBackendUrlChange(urlInput)
                                Toast.makeText(context, "Backend URL Updated!", Toast.LENGTH_SHORT).show()
                            },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text(text = stringResource(R.string.btn_save))
                        }
                    }
                }
            }

            // System-Wide Threat Interception Card
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = if (isDefaultGuardActive) ShieldGreenContainer.copy(alpha = 0.4f)
                        else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                    )
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = if (isDefaultGuardActive) Icons.Default.CheckCircle else Icons.Default.Security,
                                contentDescription = null,
                                tint = if (isDefaultGuardActive) ShieldGreen else MaterialTheme.colorScheme.primary
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Text(
                                text = if (isDefaultGuardActive) "System Link Guard: ACTIVE" else "System-Wide Link & Threat Guard",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                                color = if (isDefaultGuardActive) ShieldGreen else MaterialTheme.colorScheme.onSurface
                            )
                        }

                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = if (isDefaultGuardActive)
                                "FraudShield is actively intercepting and blocking dangerous links from WhatsApp, SMS, Telegram, and Gmail before any browser can open them."
                            else
                                "Intercept links clicked inside WhatsApp, SMS, Telegram, and Gmail. Automatically stops blacklisted threats and phishing sites from ever opening.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )

                        Spacer(modifier = Modifier.height(14.dp))
                        Button(
                            onClick = {
                                if (isDefaultGuardActive) {
                                    Toast.makeText(context, "🛡️ System Link Guard is already active and protecting your device!", Toast.LENGTH_SHORT).show()
                                    return@Button
                                }
                                try {
                                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                                        val roleManager = context.getSystemService(RoleManager::class.java)
                                        if (roleManager != null && roleManager.isRoleAvailable(RoleManager.ROLE_BROWSER)) {
                                            val roleIntent = roleManager.createRequestRoleIntent(RoleManager.ROLE_BROWSER)
                                            roleLauncher.launch(roleIntent)
                                            return@Button
                                        }
                                    }
                                    val defaultAppsIntent = Intent(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS).apply {
                                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                    }
                                    context.startActivity(defaultAppsIntent)
                                } catch (_: Exception) {
                                    try {
                                        val appDetailsIntent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                                            data = Uri.fromParts("package", context.packageName, null)
                                            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                        }
                                        context.startActivity(appDetailsIntent)
                                    } catch (_: Exception) {
                                        val genericIntent = Intent(Settings.ACTION_SETTINGS).apply {
                                            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                        }
                                        context.startActivity(genericIntent)
                                    }
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (isDefaultGuardActive) ShieldGreen else MaterialTheme.colorScheme.primary
                            )
                        ) {
                            Icon(
                                imageVector = if (isDefaultGuardActive) Icons.Default.CheckCircle else Icons.Default.Security,
                                contentDescription = null,
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(if (isDefaultGuardActive) "Active (Device Protected)" else "Set as System Link Guard (Default)")
                        }
                    }
                }
            }

            // Counter QR Sticker Protection Card (Shopkeeper Geo-Fence Registration)
            if (fraudRepository != null) {
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                        )
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    imageVector = Icons.Default.LocationOn,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.primary
                                )
                                Spacer(modifier = Modifier.width(10.dp))
                                Text(
                                    text = "Store Counter QR Guard (Anti-Sticker Fraud)",
                                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                                )
                            }

                            Spacer(modifier = Modifier.height(6.dp))
                            Text(
                                text = "Bind a genuine shop QR / UPI ID to this location's GPS. If anyone pastes their personal QR sticker over the shop standee, FraudShield alerts & blocks payments.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )

                            Spacer(modifier = Modifier.height(12.dp))
                            OutlinedTextField(
                                value = shopNameInput,
                                onValueChange = { shopNameInput = it },
                                label = { Text("Shop / Grocery Store Name") },
                                placeholder = { Text("e.g. Sharmaji Grocery Store") },
                                singleLine = true,
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(12.dp)
                            )

                            Spacer(modifier = Modifier.height(8.dp))
                            OutlinedTextField(
                                value = shopQrOrVpaInput,
                                onValueChange = { shopQrOrVpaInput = it },
                                label = { Text("Official Shop UPI ID or upi:// QR") },
                                placeholder = { Text("e.g. sharma_kirana@icici") },
                                singleLine = true,
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(12.dp)
                            )

                            Spacer(modifier = Modifier.height(8.dp))
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                FilterChip(
                                    selected = false,
                                    onClick = {
                                        shopNameInput = "Sharmaji Grocery Store"
                                        shopQrOrVpaInput = "upi://pay?pa=sharma_kirana@icici&pn=SharmajiGrocery&mc=5411"
                                    },
                                    label = { Text("Fill Demo Store") }
                                )
                            }

                            Spacer(modifier = Modifier.height(10.dp))
                            Button(
                                onClick = {
                                    if (shopNameInput.isBlank() || shopQrOrVpaInput.isBlank()) {
                                        Toast.makeText(context, "Enter shop name and official UPI/QR first.", Toast.LENGTH_SHORT).show()
                                        return@Button
                                    }
                                    if (LocationHelper.hasLocationPermission(context)) {
                                        scope.launch { bindStoreWithCurrentGps() }
                                    } else {
                                        locationPermissionLauncher.launch(
                                            arrayOf(
                                                Manifest.permission.ACCESS_FINE_LOCATION,
                                                Manifest.permission.ACCESS_COARSE_LOCATION
                                            )
                                        )
                                    }
                                },
                                enabled = !isRegisteringShop,
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Default.QrCodeScanner,
                                    contentDescription = null,
                                    modifier = Modifier.size(16.dp)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(if (isRegisteringShop) "Binding GPS Location..." else "Bind Store QR to Current GPS")
                            }

                            if (registeredMerchants.isNotEmpty()) {
                                Spacer(modifier = Modifier.height(12.dp))
                                Text(
                                    text = "Protected Counter QRs (${registeredMerchants.size}):",
                                    style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.SemiBold),
                                    color = ShieldGreen
                                )
                                Spacer(modifier = Modifier.height(6.dp))
                                registeredMerchants.forEach { merchant ->
                                    Surface(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .padding(vertical = 4.dp),
                                        shape = RoundedCornerShape(10.dp),
                                        color = ShieldGreenContainer.copy(alpha = 0.25f)
                                    ) {
                                        Row(
                                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.SpaceBetween
                                        ) {
                                            Column(modifier = Modifier.weight(1f)) {
                                                Text(
                                                    text = merchant.shopName,
                                                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold)
                                                )
                                                Text(
                                                    text = "${merchant.officialVpa} • GPS (${"%.4f".format(java.util.Locale.US, merchant.latitude)}, ${"%.4f".format(java.util.Locale.US, merchant.longitude)})",
                                                    style = MaterialTheme.typography.labelSmall,
                                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                                )
                                            }
                                            IconButton(
                                                onClick = {
                                                    scope.launch {
                                                        if (fraudRepository.deleteRegisteredMerchant(merchant.id, urlInput)) {
                                                            refreshMerchants()
                                                        }
                                                    }
                                                }
                                            ) {
                                                Icon(
                                                    imageVector = Icons.Default.Delete,
                                                    contentDescription = "Remove Store Binding",
                                                    tint = MaterialTheme.colorScheme.error
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Language Selector Dialog
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
                            if (currentLanguage == lang.code) {
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

@Composable
fun ThemeChip(
    label: String,
    isSelected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    FilterChip(
        selected = isSelected,
        onClick = onClick,
        label = { Text(text = label, modifier = Modifier.fillMaxWidth(), textAlign = androidx.compose.ui.text.style.TextAlign.Center) },
        modifier = modifier
    )
}

private fun checkIsDefaultBrowser(context: Context): Boolean {
    return try {
        val testIntent = Intent(Intent.ACTION_VIEW, Uri.parse("https://google.com"))
        val resolveInfo = context.packageManager.resolveActivity(testIntent, PackageManager.MATCH_DEFAULT_ONLY)
        resolveInfo?.activityInfo?.packageName == context.packageName
    } catch (_: Exception) {
        false
    }
}

