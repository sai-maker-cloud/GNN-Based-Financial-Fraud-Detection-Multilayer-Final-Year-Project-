package com.jagnn.fraudshield.utils

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.CancellationSignal
import android.os.Looper
import androidx.core.content.ContextCompat
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import kotlin.coroutines.resume

data class DeviceCoordinates(
    val latitude: Double,
    val longitude: Double,
    val accuracyM: Float? = null
)

object LocationHelper {

    fun hasLocationPermission(context: Context): Boolean {
        val fine = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        val coarse = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        return fine || coarse
    }

    /**
     * Fetches the device's coordinates for geo-fenced merchant QR verification.
     * Uses fresh cached location (0ms) when recent, or waits at most [timeoutMs] for a single fix,
     * falling back safely to null if location is unavailable or permission is denied.
     */
    @SuppressLint("MissingPermission")
    suspend fun getCurrentCoordinates(
        context: Context,
        timeoutMs: Long = 1200L
    ): DeviceCoordinates? {
        if (!hasLocationPermission(context)) return null

        val locationManager = context.applicationContext
            .getSystemService(Context.LOCATION_SERVICE) as? LocationManager
            ?: return null

        val cached = getBestLastKnownLocation(locationManager)
        if (cached != null) {
            val ageMs = System.currentTimeMillis() - cached.time
            if (ageMs in 0..90_000L && (!cached.hasAccuracy() || cached.accuracy <= 80f)) {
                return DeviceCoordinates(
                    latitude = cached.latitude,
                    longitude = cached.longitude,
                    accuracyM = if (cached.hasAccuracy()) cached.accuracy else null
                )
            }
        }

        // Request a fast single update (API 30+ getCurrentLocation, or legacy requestSingleUpdate on API 26-29)
        val provider = when {
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
                isProviderSafeEnabled(locationManager, LocationManager.FUSED_PROVIDER) -> LocationManager.FUSED_PROVIDER
            isProviderSafeEnabled(locationManager, LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
            isProviderSafeEnabled(locationManager, LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
            else -> null
        }

        val freshLocation = if (provider != null) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                withTimeoutOrNull(timeoutMs) {
                    suspendCancellableCoroutine<Location?> { cont ->
                        val signal = CancellationSignal()
                        cont.invokeOnCancellation { signal.cancel() }
                        try {
                            locationManager.getCurrentLocation(
                                provider,
                                signal,
                                ContextCompat.getMainExecutor(context.applicationContext)
                            ) { loc ->
                                if (cont.isActive) cont.resume(loc)
                            }
                        } catch (_: Exception) {
                            if (cont.isActive) cont.resume(null)
                        }
                    }
                }
            } else {
                withTimeoutOrNull(timeoutMs) {
                    suspendCancellableCoroutine<Location?> { cont ->
                        val listener = object : LocationListener {
                            override fun onLocationChanged(location: Location) {
                                try {
                                    locationManager.removeUpdates(this)
                                } catch (_: Exception) {}
                                if (cont.isActive) cont.resume(location)
                            }

                            @Deprecated("Deprecated in Java")
                            override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
                            override fun onProviderEnabled(provider: String) {}
                            override fun onProviderDisabled(provider: String) {}
                        }
                        cont.invokeOnCancellation {
                            try {
                                locationManager.removeUpdates(listener)
                            } catch (_: Exception) {}
                        }
                        try {
                            @Suppress("DEPRECATION")
                            locationManager.requestSingleUpdate(provider, listener, Looper.getMainLooper())
                        } catch (_: Exception) {
                            if (cont.isActive) cont.resume(null)
                        }
                    }
                }
            }
        } else {
            null
        }

        val chosen = freshLocation ?: cached ?: return null
        return DeviceCoordinates(
            latitude = chosen.latitude,
            longitude = chosen.longitude,
            accuracyM = if (chosen.hasAccuracy()) chosen.accuracy else null
        )
    }

    private fun isProviderSafeEnabled(lm: LocationManager, provider: String): Boolean {
        return try {
            lm.isProviderEnabled(provider)
        } catch (_: Exception) {
            false
        }
    }

    @SuppressLint("MissingPermission")
    private fun getBestLastKnownLocation(locationManager: LocationManager): Location? {
        val providers = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            providers.add(LocationManager.FUSED_PROVIDER)
        }
        providers.add(LocationManager.GPS_PROVIDER)
        providers.add(LocationManager.NETWORK_PROVIDER)
        providers.add(LocationManager.PASSIVE_PROVIDER)

        var best: Location? = null
        for (p in providers) {
            try {
                val loc = locationManager.getLastKnownLocation(p) ?: continue
                if (best == null || loc.time > best.time) {
                    best = loc
                }
            } catch (_: Exception) {}
        }
        return best
    }
}

