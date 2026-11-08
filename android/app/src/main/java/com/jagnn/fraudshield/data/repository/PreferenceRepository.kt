package com.jagnn.fraudshield.data.repository

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.jagnn.fraudshield.data.api.RetrofitClient
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "fraudshield_prefs")

class PreferenceRepository(private val context: Context) {

    companion object {
        val KEY_LANGUAGE = stringPreferencesKey("app_language")
        val KEY_THEME = stringPreferencesKey("app_theme")
        val KEY_BACKEND_URL = stringPreferencesKey("backend_url")
    }

    private val sharedPrefs = context.getSharedPreferences("fraudshield_prefs", Context.MODE_PRIVATE)

    val initialLanguage: String
        get() = sharedPrefs.getString("app_language", "en") ?: "en"

    val initialBackendUrl: String
        get() = sharedPrefs.getString("backend_url", RetrofitClient.DEFAULT_BASE_URL) ?: RetrofitClient.DEFAULT_BASE_URL

    val languageFlow: Flow<String> = context.dataStore.data.map { prefs ->
        prefs[KEY_LANGUAGE] ?: initialLanguage
    }

    val themeFlow: Flow<String> = context.dataStore.data.map { prefs ->
        prefs[KEY_THEME] ?: "system"
    }

    val backendUrlFlow: Flow<String> = context.dataStore.data.map { prefs ->
        prefs[KEY_BACKEND_URL] ?: initialBackendUrl
    }

    suspend fun saveLanguage(languageCode: String) {
        sharedPrefs.edit().putString("app_language", languageCode).commit()
        context.dataStore.edit { prefs ->
            prefs[KEY_LANGUAGE] = languageCode
        }
    }

    suspend fun saveTheme(themeMode: String) {
        context.dataStore.edit { prefs ->
            prefs[KEY_THEME] = themeMode
        }
    }

    suspend fun saveBackendUrl(url: String) {
        sharedPrefs.edit().putString("backend_url", url).commit()
        context.dataStore.edit { prefs ->
            prefs[KEY_BACKEND_URL] = url
        }
        RetrofitClient.updateBaseUrl(url)
    }
}
