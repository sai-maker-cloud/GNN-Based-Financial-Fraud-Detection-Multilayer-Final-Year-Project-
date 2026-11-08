package com.jagnn.fraudshield.data.api

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {

    // Live 24/7 Cloud Backend deployed on Render
    const val DEFAULT_BASE_URL = "https://fraudshield-backend-vrxr.onrender.com/"

    private var currentBaseUrl = DEFAULT_BASE_URL
    private var apiService: FraudShieldApiService? = null

    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        })
        .build()

    fun getService(baseUrl: String = currentBaseUrl): FraudShieldApiService {
        val sanitizedUrl = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        if (apiService == null || currentBaseUrl != sanitizedUrl) {
            currentBaseUrl = sanitizedUrl
            val retrofit = Retrofit.Builder()
                .baseUrl(currentBaseUrl)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
            apiService = retrofit.create(FraudShieldApiService::class.java)
        }
        return apiService!!
    }

    fun updateBaseUrl(newUrl: String) {
        val sanitized = if (newUrl.endsWith("/")) newUrl else "$newUrl/"
        if (currentBaseUrl != sanitized) {
            currentBaseUrl = sanitized
            apiService = null
        }
    }
}
