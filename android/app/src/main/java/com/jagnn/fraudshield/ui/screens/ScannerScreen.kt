package com.jagnn.fraudshield.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.annotation.OptIn
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import com.jagnn.fraudshield.R
import com.jagnn.fraudshield.ui.components.RiskShieldModal
import com.jagnn.fraudshield.ui.components.ScannerOverlay
import com.jagnn.fraudshield.ui.viewmodel.ScanUiState
import com.jagnn.fraudshield.ui.viewmodel.ScannerViewModel
import java.util.concurrent.Executors

@Composable
fun ScannerScreen(
    activity: ComponentActivity,
    viewModel: ScannerViewModel,
    backendUrl: String,
    onBackClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsState()

    var hasCameraPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(activity, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        hasCameraPermission = isGranted
    }

    LaunchedEffect(Unit) {
        if (!hasCameraPermission) {
            permissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    var isFlashOn by remember { mutableStateOf(false) }
    var cameraControl by remember { mutableStateOf<CameraControl?>(null) }
    var cameraError by remember { mutableStateOf<String?>(null) }

    Box(modifier = modifier.fillMaxSize().background(Color.Black)) {
        if (hasCameraPermission && cameraError == null) {
            CameraPreviewView(
                activity = activity,
                onQrDetected = { qrCode ->
                    viewModel.onQrScanned(qrCode, backendUrl)
                },
                onCameraControlReady = { control ->
                    cameraControl = control
                },
                onError = { err ->
                    cameraError = err
                }
            )

            // Overlay with Controls & Laser Beam Animation
            ScannerOverlay(
                isFlashOn = isFlashOn,
                isAnalyzing = uiState is ScanUiState.Analyzing,
                onBackClick = onBackClick,
                onFlashToggle = {
                    isFlashOn = !isFlashOn
                    try {
                        cameraControl?.enableTorch(isFlashOn)
                    } catch (_: Exception) {}
                },
                onManualQrSubmit = { manualQr ->
                    viewModel.onQrScanned(manualQr, backendUrl)
                }
            )
        } else if (cameraError != null) {
            // Camera Hardware / Initialization Error Fallback Screen
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(24.dp),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Icon(
                    imageVector = Icons.Default.Warning,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.error,
                    modifier = Modifier.size(48.dp)
                )
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = "Camera Unavailable",
                    style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                    color = Color.White
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = cameraError ?: "Could not initialize camera hardware.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.White.copy(alpha = 0.7f),
                    textAlign = TextAlign.Center
                )
                Spacer(modifier = Modifier.height(24.dp))
                Button(
                    onClick = {
                        cameraError = null
                    },
                    shape = RoundedCornerShape(20.dp)
                ) {
                    Text("Retry Camera")
                }
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedButton(
                    onClick = onBackClick,
                    shape = RoundedCornerShape(20.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)
                ) {
                    Text("Back to Dashboard")
                }
            }
        } else {
            // Camera Permission Request Screen
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(24.dp),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = stringResource(R.string.camera_permission_required),
                    style = MaterialTheme.typography.titleMedium,
                    color = Color.White,
                    textAlign = TextAlign.Center
                )
                Spacer(modifier = Modifier.height(16.dp))
                Button(
                    onClick = { permissionLauncher.launch(Manifest.permission.CAMERA) },
                    shape = RoundedCornerShape(20.dp)
                ) {
                    Text(text = stringResource(R.string.grant_permission))
                }
                Spacer(modifier = Modifier.height(12.dp))
                TextButton(onClick = onBackClick) {
                    Text("Back to Dashboard", color = Color.White.copy(alpha = 0.7f))
                }
            }
        }

        // Result Decision Shield Bottom Sheet
        if (uiState is ScanUiState.Success) {
            val success = uiState as ScanUiState.Success
            RiskShieldModal(
                response = success.response,
                rawQr = success.rawQr,
                onDismiss = { viewModel.dismissResult() }
            )
        }

        // Error Notice Dialog
        if (uiState is ScanUiState.Error) {
            val error = uiState as ScanUiState.Error
            AlertDialog(
                onDismissRequest = { viewModel.dismissResult() },
                title = { Text("Scan Analysis Notice") },
                text = { Text(error.message) },
                confirmButton = {
                    Button(onClick = { viewModel.dismissResult() }) {
                        Text("OK")
                    }
                }
            )
        }
    }
}

@OptIn(ExperimentalGetImage::class)
@Composable
fun CameraPreviewView(
    activity: ComponentActivity,
    onQrDetected: (String) -> Unit,
    onCameraControlReady: (CameraControl) -> Unit,
    onError: (String) -> Unit
) {
    val cameraExecutor = remember { Executors.newSingleThreadExecutor() }
    var activeCameraProvider by remember { mutableStateOf<ProcessCameraProvider?>(null) }

    DisposableEffect(Unit) {
        onDispose {
            try {
                activeCameraProvider?.unbindAll()
                cameraExecutor.shutdown()
            } catch (_: Exception) {}
        }
    }

    val barcodeScanner = remember {
        val options = BarcodeScannerOptions.Builder()
            .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
            .build()
        BarcodeScanning.getClient(options)
    }

    AndroidView(
        factory = { _ ->
            val previewView = PreviewView(activity)

            try {
                val cameraProviderFuture = ProcessCameraProvider.getInstance(activity.applicationContext)

                cameraProviderFuture.addListener({
                    try {
                        if (activity.isFinishing || activity.isDestroyed) {
                            return@addListener
                        }

                        val cameraProvider = cameraProviderFuture.get()
                        activeCameraProvider = cameraProvider

                        val preview = Preview.Builder().build().also {
                            it.setSurfaceProvider(previewView.surfaceProvider)
                        }

                        val imageAnalysis = ImageAnalysis.Builder()
                            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                            .build()

                        imageAnalysis.setAnalyzer(cameraExecutor) { imageProxy ->
                            val mediaImage = imageProxy.image
                            if (mediaImage != null) {
                                try {
                                    val inputImage = InputImage.fromMediaImage(
                                        mediaImage,
                                        imageProxy.imageInfo.rotationDegrees
                                    )
                                    barcodeScanner.process(inputImage)
                                        .addOnSuccessListener { barcodes ->
                                            for (barcode in barcodes) {
                                                val qrValue = barcode.rawValue
                                                if (!qrValue.isNullOrBlank()) {
                                                    onQrDetected(qrValue)
                                                }
                                            }
                                        }
                                        .addOnFailureListener {
                                            // Frame analysis failure ignored
                                        }
                                        .addOnCompleteListener {
                                            try { imageProxy.close() } catch (_: Exception) {}
                                        }
                                } catch (_: Exception) {
                                    try { imageProxy.close() } catch (_: Exception) {}
                                }
                            } else {
                                try { imageProxy.close() } catch (_: Exception) {}
                            }
                        }

                        val cameraSelector = if (cameraProvider.hasCamera(CameraSelector.DEFAULT_BACK_CAMERA)) {
                            CameraSelector.DEFAULT_BACK_CAMERA
                        } else if (cameraProvider.hasCamera(CameraSelector.DEFAULT_FRONT_CAMERA)) {
                            CameraSelector.DEFAULT_FRONT_CAMERA
                        } else {
                            CameraSelector.DEFAULT_BACK_CAMERA
                        }

                        cameraProvider.unbindAll()
                        val camera = cameraProvider.bindToLifecycle(
                            activity,
                            cameraSelector,
                            preview,
                            imageAnalysis
                        )
                        onCameraControlReady(camera.cameraControl)

                    } catch (e: Exception) {
                        onError("Camera initialization failed: ${e.localizedMessage ?: "Unknown error"}")
                    }
                }, ContextCompat.getMainExecutor(activity.applicationContext))

            } catch (e: Exception) {
                onError("Failed to start Camera Provider: ${e.localizedMessage ?: "Unknown error"}")
            }

            previewView
        },
        modifier = Modifier.fillMaxSize()
    )
}
