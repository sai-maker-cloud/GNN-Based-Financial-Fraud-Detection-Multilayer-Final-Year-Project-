package com.jagnn.fraudshield.data.api

import com.jagnn.fraudshield.data.model.HealthResponse
import com.jagnn.fraudshield.data.model.QRAnalyzeRequest
import com.jagnn.fraudshield.data.model.QRAnalyzeResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface FraudShieldApiService {

    @POST("api/v1/qr/analyze")
    suspend fun analyzeQR(
        @Body request: QRAnalyzeRequest
    ): Response<QRAnalyzeResponse>

    @GET("api/v1/health")
    suspend fun checkHealth(): Response<HealthResponse>
}

