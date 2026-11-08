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
            if (isWebUrl(trimmed)) {
                // If the target is a web URL, forward directly to browser handler
                launchSafeUrl(context, trimmed)
                return
            }

            val uri = if (trimmed.startsWith("upi://")) {
                Uri.parse(trimmed)
            } else {
                Uri.parse("upi://pay?$trimmed")
            }

            val intent = Intent(Intent.ACTION_VIEW, uri).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }

            val chooser = Intent.createChooser(intent, "Pay with UPI").apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(chooser)
        } catch (e: Exception) {
            Toast.makeText(context, "No UPI payment application found on device.", Toast.LENGTH_LONG).show()
        }
    }
            context.startActivity(chooser)
        } catch (e: Exception) {
            Toast.makeText(context, "No UPI payment application found on device.", Toast.LENGTH_LONG).show()
        }
    }
}
