package com.jagnn.fraudshield.utils

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast

object UPIIntentHandler {

    /**
     * Inspects a string to determine if it is a Web URL rather than a pure UPI scheme.
     */
    fun isWebUrl(text: String): Boolean {
        val trimmed = text.trim()
        if (trimmed.startsWith("http://", ignoreCase = true) || trimmed.startsWith("https://", ignoreCase = true)) {
            return true
        }
        if (trimmed.startsWith("www.", ignoreCase = true)) {
            return true
        }
        // Match domain-like string without spaces and without '@' (distinguishing from email/VPA)
        return !trimmed.contains(" ") && !trimmed.contains("@") &&
                (trimmed.contains(".com") || trimmed.contains(".in") || trimmed.contains(".org") ||
                 trimmed.contains(".net") || trimmed.contains(".io") || trimmed.contains(".co") ||
                 trimmed.contains(".ai") || trimmed.contains(".gov") || trimmed.contains(".edu") ||
                 trimmed.contains(".xyz") || trimmed.contains(".me") || trimmed.contains(".club"))
    }

    /**
     * Safely opens a verified URL in the user's default web browser (e.g., Chrome).
     * Enforces strict device-level blacklist interception: if blacklisted, browser is NEVER opened!
     */
    fun launchSafeUrl(context: Context, rawUrl: String) {
        val trimmed = rawUrl.trim()
        if (com.jagnn.fraudshield.data.repository.DeviceBlacklistManager.isBlocked(trimmed)) {
            Toast.makeText(
                context,
                "🔒 Hard Blocked: This URL is permanently blacklisted on this device. Browser opening is prohibited.",
                Toast.LENGTH_LONG
            ).show()
            return
        }

        try {
            val normalizedUrl = if (trimmed.startsWith("http://", ignoreCase = true) || trimmed.startsWith("https://", ignoreCase = true)) {
                trimmed
            } else {
                "https://$trimmed"
            }

            val browserIntent = Intent(Intent.ACTION_VIEW, Uri.parse(normalizedUrl)).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }

            // If FraudShield is set as default browser, avoid looping back to ourselves.
            // Explicitly target an external browser (e.g. Chrome, Firefox, Samsung Browser)
            val packageManager = context.packageManager
            val activities = packageManager.queryIntentActivities(browserIntent, android.content.pm.PackageManager.MATCH_DEFAULT_ONLY)
            val externalBrowser = activities.firstOrNull { it.activityInfo.packageName != context.packageName }

            if (externalBrowser != null) {
                browserIntent.setPackage(externalBrowser.activityInfo.packageName)
            } else {
                val knownBrowsers = listOf(
                    "com.android.chrome",
                    "org.mozilla.firefox",
                    "com.sec.android.app.sbrowser",
                    "com.brave.browser",
                    "com.opera.browser"
                )
                for (pkg in knownBrowsers) {
                    try {
                        packageManager.getPackageInfo(pkg, 0)
                        browserIntent.setPackage(pkg)
                        break
                    } catch (_: Exception) {}
                }
            }

            context.startActivity(browserIntent)
        } catch (e: Exception) {
            Toast.makeText(context, "No web browser found to open link.", Toast.LENGTH_SHORT).show()
        }
    }

    /**
     * Safely redirects to installed UPI payment apps (Google Pay, PhonePe, Paytm, BHIM)
     * using the official Android View Intent chooser.
     * Enforces strict device-level blacklist interception: if blacklisted, payment app is NEVER opened!
     */
    fun launchUpiPayment(context: Context, rawQrOrUpiString: String) {
        val trimmed = rawQrOrUpiString.trim()
        if (com.jagnn.fraudshield.data.repository.DeviceBlacklistManager.isBlocked(trimmed)) {
            Toast.makeText(
                context,
                "🔒 Hard Blocked: This transaction target is permanently blacklisted on this device.",
                Toast.LENGTH_LONG
            ).show()
            return
        }

        try {
            val uri = when {
                trimmed.startsWith("upi://", ignoreCase = true) -> Uri.parse(trimmed)
                // If it's a web URL containing UPI parameters (e.g., https://.../pay?pa=abc@upi&am=100)
                (trimmed.startsWith("http://", ignoreCase = true) || trimmed.startsWith("https://", ignoreCase = true)) &&
                        (trimmed.contains("pa=", ignoreCase = true) || trimmed.contains("pn=", ignoreCase = true)) -> {
                    val parsed = Uri.parse(trimmed)
                    val query = parsed.query
                    if (!query.isNullOrEmpty() && query.contains("pa=", ignoreCase = true)) {
                        Uri.parse("upi://pay?$query")
                    } else {
                        launchSafeUrl(context, trimmed)
                        return
                    }
                }
                isWebUrl(trimmed) -> {
                    launchSafeUrl(context, trimmed)
                    return
                }
                else -> Uri.parse("upi://pay?$trimmed")
            }

            val intent = Intent(Intent.ACTION_VIEW, uri).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }

            val chooser = Intent.createChooser(intent, "Pay with UPI").apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(chooser)
        } catch (e: Exception) {
            // Fallback to browser if it was an HTTP URL
            if (trimmed.startsWith("http://", ignoreCase = true) || trimmed.startsWith("https://", ignoreCase = true)) {
                launchSafeUrl(context, trimmed)
            } else {
                Toast.makeText(context, "No UPI payment application found on device.", Toast.LENGTH_LONG).show()
            }
        }
    }
}
