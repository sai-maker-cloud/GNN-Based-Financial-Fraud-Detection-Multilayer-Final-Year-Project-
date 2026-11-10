package com.jagnn.fraudshield.utils

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
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
     * Safely opens a verified URL in an EXTERNAL web browser (Chrome, Firefox, etc.).
     * Uses a 4-strategy approach to guarantee the URL never loops back to FraudShield
     * when FraudShield is set as the device's default browser.
     *
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

        val normalizedUrl = if (trimmed.startsWith("http://", ignoreCase = true) || trimmed.startsWith("https://", ignoreCase = true)) {
            trimmed
        } else {
            "https://$trimmed"
        }

        // ── Strategy 1: Try Chrome directly (installed on 99%+ of Android devices) ──
        try {
            val chromeIntent = Intent(Intent.ACTION_VIEW, Uri.parse(normalizedUrl)).apply {
                setPackage("com.android.chrome")
                addCategory(Intent.CATEGORY_BROWSABLE)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            if (chromeIntent.resolveActivity(context.packageManager) != null) {
                context.startActivity(chromeIntent)
                return
            }
        } catch (_: Exception) { /* Chrome not installed or disabled, try next strategy */ }

        // ── Strategy 2: Try other well-known & OEM browsers ──
        val knownBrowsers = listOf(
            "org.mozilla.firefox",
            "com.sec.android.app.sbrowser",
            "com.brave.browser",
            "com.opera.browser",
            "com.microsoft.emmx",
            "com.mi.globalbrowser",
            "com.android.browser",
            "com.heytap.browser",
            "com.coloros.browser",
            "com.vivo.browser",
            "com.duckduckgo.mobile.android"
        )
        for (pkg in knownBrowsers) {
            if (pkg == context.packageName) continue
            try {
                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(normalizedUrl)).apply {
                    setPackage(pkg)
                    addCategory(Intent.CATEGORY_BROWSABLE)
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                if (intent.resolveActivity(context.packageManager) != null) {
                    context.startActivity(intent)
                    return
                }
            } catch (_: Exception) { /* This browser not installed, try next */ }
        }

        // ── Strategy 3: Query PackageManager for ANY external browser ──
        try {
            val genericIntent = Intent(Intent.ACTION_VIEW, Uri.parse(normalizedUrl)).apply {
                addCategory(Intent.CATEGORY_BROWSABLE)
            }
            val pm = context.packageManager
            val activities = pm.queryIntentActivities(genericIntent, PackageManager.MATCH_DEFAULT_ONLY)
            val externalBrowser = activities.firstOrNull {
                val pkg = it.activityInfo.packageName
                pkg != context.packageName && pkg != "android"
            }
            if (externalBrowser != null) {
                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(normalizedUrl)).apply {
                    setPackage(externalBrowser.activityInfo.packageName)
                    addCategory(Intent.CATEGORY_BROWSABLE)
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(intent)
                return
            }
        } catch (_: Exception) { /* Query failed, try next strategy */ }

        // ── Strategy 4: Chooser dialog that explicitly excludes FraudShield ──
        try {
            val chooserBase = Intent(Intent.ACTION_VIEW, Uri.parse(normalizedUrl)).apply {
                addCategory(Intent.CATEGORY_BROWSABLE)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            val chooser = Intent.createChooser(chooserBase, "Open in browser").apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            // Exclude FraudShield from the chooser list (API 24+)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                val selfComponent = ComponentName(
                    context.packageName,
                    "com.jagnn.fraudshield.MainActivity"
                )
                chooser.putExtra(Intent.EXTRA_EXCLUDE_COMPONENTS, arrayOf(selfComponent))
            }
            context.startActivity(chooser)
        } catch (e: Exception) {
            Toast.makeText(context, "No web browser found to open link.", Toast.LENGTH_SHORT).show()
        }
    }

    /**
     * Safely redirects to installed UPI payment apps (Google Pay, PhonePe, Paytm, BHIM).
     * Directly launches the default or single installed UPI app without extra prompts,
     * or shows a UPI app chooser (explicitly excluding FraudShield to prevent loops).
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
                // Plain VPA address (e.g., merchant@icici)
                !trimmed.contains("=") && trimmed.contains("@") -> {
                    Uri.parse("upi://pay?pa=${Uri.encode(trimmed)}")
                }
                else -> Uri.parse("upi://pay?$trimmed")
            }

            val baseIntent = Intent(Intent.ACTION_VIEW, uri).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }

            val pm = context.packageManager

            // 1. Check if the user already has an external default UPI app (and it's not FraudShield/Android resolver)
            val resolvedDefault = pm.resolveActivity(baseIntent, PackageManager.MATCH_DEFAULT_ONLY)
            val defaultPkg = resolvedDefault?.activityInfo?.packageName
            if (defaultPkg != null &&
                defaultPkg != context.packageName &&
                defaultPkg != "android" &&
                !defaultPkg.contains("resolver", ignoreCase = true)
            ) {
                val directIntent = Intent(Intent.ACTION_VIEW, uri).apply {
                    setPackage(defaultPkg)
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(directIntent)
                return
            }

            // 2. Query all installed UPI apps excluding FraudShield itself
            val upiActivities = pm.queryIntentActivities(baseIntent, PackageManager.MATCH_DEFAULT_ONLY)
                .filter {
                    val pkg = it.activityInfo.packageName
                    pkg != context.packageName && pkg != "android"
                }

            if (upiActivities.size == 1) {
                // Only one UPI app installed -> launch it directly!
                val singlePkg = upiActivities.first().activityInfo.packageName
                val directIntent = Intent(Intent.ACTION_VIEW, uri).apply {
                    setPackage(singlePkg)
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(directIntent)
                return
            }

            if (upiActivities.isNotEmpty()) {
                // Multiple UPI apps installed -> open chooser excluding FraudShield
                val chooser = Intent.createChooser(baseIntent, "Pay with UPI").apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                    val selfComponent = ComponentName(
                        context.packageName,
                        "com.jagnn.fraudshield.MainActivity"
                    )
                    chooser.putExtra(Intent.EXTRA_EXCLUDE_COMPONENTS, arrayOf(selfComponent))
                }
                context.startActivity(chooser)
                return
            }

            // 3. Fallback: probe popular Indian UPI apps explicitly
            val knownUpiApps = listOf(
                "com.google.android.apps.nbu.paisa.user",
                "com.phonepe.app",
                "net.one97.paytm",
                "in.org.npci.upiapp",
                "in.amazon.mShop.android.shopping",
                "com.whatsapp",
                "com.dreamplug.androidapp",
                "com.naviapp",
                "money.super.upi"
            )
            for (pkg in knownUpiApps) {
                try {
                    val pkgIntent = Intent(Intent.ACTION_VIEW, uri).apply {
                        setPackage(pkg)
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                    if (pkgIntent.resolveActivity(pm) != null) {
                        context.startActivity(pkgIntent)
                        return
                    }
                } catch (_: Exception) {}
            }

            // 4. Last resort chooser (excluding FraudShield)
            val chooser = Intent.createChooser(baseIntent, "Pay with UPI").apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                val selfComponent = ComponentName(
                    context.packageName,
                    "com.jagnn.fraudshield.MainActivity"
                )
                chooser.putExtra(Intent.EXTRA_EXCLUDE_COMPONENTS, arrayOf(selfComponent))
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
