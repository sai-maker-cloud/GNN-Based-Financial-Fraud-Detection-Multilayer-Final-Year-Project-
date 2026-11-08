package com.jagnn.fraudshield

import android.app.Application
import android.content.Context
import com.jagnn.fraudshield.utils.LocaleHelper

class FraudShieldApp : Application() {

    override fun attachBaseContext(base: Context) {
        val sharedPrefs = base.getSharedPreferences("fraudshield_prefs", Context.MODE_PRIVATE)
        val savedLang = sharedPrefs.getString("app_language", "en") ?: "en"
        super.attachBaseContext(LocaleHelper.applyLocale(base, savedLang))
    }

    override fun onCreate() {
        super.onCreate()
        com.jagnn.fraudshield.data.repository.DeviceBlacklistManager.init(this)
    }
}
