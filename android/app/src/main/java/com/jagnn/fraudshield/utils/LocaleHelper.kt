package com.jagnn.fraudshield.utils

import android.content.Context
import android.content.res.Configuration
import java.util.Locale

object LocaleHelper {

    val SUPPORTED_LANGUAGES = listOf(
        LanguageOption("en", "English", "English"),
        LanguageOption("hi", "Hindi", "हिंदी"),
        LanguageOption("mr", "Marathi", "मराठी"),
        LanguageOption("gu", "Gujarati", "ગુજરાતી"),
        LanguageOption("ta", "Tamil", "தமிழ்"),
        LanguageOption("te", "Telugu", "తెలుగు"),
        LanguageOption("bn", "Bengali", "বাংলা")
    )

    data class LanguageOption(
        val code: String,
        val englishName: String,
        val nativeName: String
    )

    fun applyLocale(context: Context, languageCode: String): Context {
        val locale = Locale(languageCode)
        Locale.setDefault(locale)

        val config = Configuration(context.resources.configuration)
        config.setLocale(locale)
        config.setLayoutDirection(locale)

        return context.createConfigurationContext(config)
    }

    fun getLocalizedConfiguration(baseConfig: Configuration, languageCode: String): Configuration {
        val locale = Locale(languageCode)
        Locale.setDefault(locale)
        val config = Configuration(baseConfig)
        config.setLocale(locale)
        config.setLayoutDirection(locale)
        return config
    }
}
