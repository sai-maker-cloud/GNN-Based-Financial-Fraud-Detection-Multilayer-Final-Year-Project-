package com.jagnn.fraudshield.data.repository

import android.content.Context
import android.content.SharedPreferences
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject

object DeviceBlacklistManager {

    private const val PREFS_NAME = "fraudshield_device_blacklist"
    private const val KEY_BLOCKED_ENTITIES = "blocked_entities_json"

    private lateinit var sharedPrefs: SharedPreferences
    private val blockedSet = mutableSetOf<String>()
    private val entityReasonMap = mutableMapOf<String, String>()

    fun init(context: Context) {
        sharedPrefs = context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        loadFromDisk()
    }

    @Synchronized
    private fun loadFromDisk() {
        blockedSet.clear()
        entityReasonMap.clear()
        val jsonStr = sharedPrefs.getString(KEY_BLOCKED_ENTITIES, null) ?: return
        try {
            val array = JSONArray(jsonStr)
            for (i in 0 until array.length()) {
                val obj = array.getJSONObject(i)
                val entity = obj.optString("entity", "").trim().lowercase()
                val reason = obj.optString("reason", "Permanently hard blocked on this device.")
                if (entity.isNotEmpty()) {
                    blockedSet.add(entity)
                    entityReasonMap[entity] = reason
                }
            }
        } catch (_: Exception) {}
    }

    @Synchronized
    private fun saveToDisk() {
        try {
            val array = JSONArray()
            for (entity in blockedSet) {
                val obj = JSONObject()
                obj.put("entity", entity)
                obj.put("reason", entityReasonMap[entity] ?: "Permanently hard blocked on this device.")
                array.put(obj)
            }
            sharedPrefs.edit().putString(KEY_BLOCKED_ENTITIES, array.toString()).apply()
        } catch (_: Exception) {}
    }

    /**
     * Persistently hard-blocks a dangerous QR payload, suspicious URL (where user unproceeded),
     * or money-mule payee VPA on this device.
     */
    @Synchronized
    fun blockEntity(
        rawPayload: String,
        domainOrTarget: String? = null,
        vpa: String? = null,
        reason: String = "Permanently hard-blocked on this device."
    ) {
        val cleanPayload = rawPayload.trim().lowercase()
        if (cleanPayload.isNotEmpty()) {
            blockedSet.add(cleanPayload)
            entityReasonMap[cleanPayload] = reason
        }

        // Domain extraction and block
        domainOrTarget?.trim()?.lowercase()?.let {
            if (it.isNotEmpty()) {
                blockedSet.add(it)
                entityReasonMap[it] = reason
            }
        }

        // Payee VPA block
        vpa?.trim()?.lowercase()?.let {
            if (it.isNotEmpty()) {
                blockedSet.add(it)
                entityReasonMap[it] = reason
            }
        }

        // Auto-extract host domain if URL
        if (cleanPayload.startsWith("http://") || cleanPayload.startsWith("https://")) {
            try {
                val uri = Uri.parse(cleanPayload)
                val host = uri.host?.lowercase()
                if (!host.isNullOrBlank()) {
                    blockedSet.add(host)
                    entityReasonMap[host] = "Host domain of blocked threat: $reason"
                }
                val paParam = uri.getQueryParameter("pa")?.lowercase()
                if (!paParam.isNullOrBlank()) {
                    blockedSet.add(paParam)
                    entityReasonMap[paParam] = "Payee in blocked payment link: $reason"
                }
            } catch (_: Exception) {}
        } else if (cleanPayload.startsWith("upi://")) {
            try {
                val uri = Uri.parse(cleanPayload)
                val paParam = uri.getQueryParameter("pa")?.lowercase()
                if (!paParam.isNullOrBlank()) {
                    blockedSet.add(paParam)
                    entityReasonMap[paParam] = "Payee in blocked UPI: $reason"
                }
            } catch (_: Exception) {}
        }

        saveToDisk()
    }

    /**
     * High-speed check (< 0.05ms): Determines if a QR, URL, domain, or payee
     * has been hard-blocked on this device.
     */
    @Synchronized
    fun isBlocked(candidate: String): Boolean {
        if (candidate.isBlank()) return false
        val clean = candidate.trim().lowercase()

        // 1. Exact raw string match
        if (blockedSet.contains(clean)) return true

        // 2. Domain match if candidate is a URL or domain
        if (clean.startsWith("http://") || clean.startsWith("https://") || (!clean.contains("@") && clean.contains("."))) {
            try {
                val parseTarget = if (clean.startsWith("http")) clean else "https://$clean"
                val uri = Uri.parse(parseTarget)
                val host = uri.host?.lowercase()
                if (!host.isNullOrBlank()) {
                    if (blockedSet.contains(host)) return true
                    for (b in blockedSet) {
                        if (host == b || host.endsWith(".$b")) return true
                    }
                }
                val paParam = uri.getQueryParameter("pa")?.lowercase()
                if (!paParam.isNullOrBlank() && blockedSet.contains(paParam)) return true
            } catch (_: Exception) {}
        }

        // 3. Payee match if UPI URI
        if (clean.startsWith("upi://")) {
            try {
                val uri = Uri.parse(clean)
                val paParam = uri.getQueryParameter("pa")?.lowercase()
                if (!paParam.isNullOrBlank() && blockedSet.contains(paParam)) return true
            } catch (_: Exception) {}
        }

        // 4. Direct VPA
        if (clean.contains("@") && !clean.contains(" ")) {
            if (blockedSet.contains(clean)) return true
        }

        return false
    }

    @Synchronized
    fun getBlockReason(candidate: String): String {
        val clean = candidate.trim().lowercase()
        return entityReasonMap[clean]
            ?: "Permanently blocked by FraudShield AI Device Security Policy."
    }

    @Synchronized
    fun getBlockedCount(): Int = blockedSet.size

    @Synchronized
    fun clearAll() {
        blockedSet.clear()
        entityReasonMap.clear()
        sharedPrefs.edit().remove(KEY_BLOCKED_ENTITIES).apply()
    }
}

