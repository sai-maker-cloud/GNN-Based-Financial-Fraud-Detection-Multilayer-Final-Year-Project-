package com.jagnn.fraudshield.data.api

import com.jagnn.fraudshield.data.model.BlacklistBlockRequest
import com.jagnn.fraudshield.data.model.HealthResponse
import com.jagnn.fraudshield.data.model.MerchantListResponse
import com.jagnn.fraudshield.data.model.MerchantRegisterRequest
import com.jagnn.fraudshield.data.model.MerchantRegisterResponse
import com.jagnn.fraudshield.data.model.QRAnalyzeRequest
import com.jagnn.fraudshield.data.model.QRAnalyzeResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface FraudShieldApiService {

    @POST("api/v1/qr/analyze")
    suspend fun analyzeQR(
        @Body request: QRAnalyzeRequest
    ): Response<QRAnalyzeResponse>

    @GET("api/v1/health")
    suspend fun checkHealth(): Response<HealthResponse>

    @POST("api/v1/merchants/register")
    suspend fun registerMerchant(
        @Body request: MerchantRegisterRequest
    ): Response<MerchantRegisterResponse>

    @GET("api/v1/merchants")
    suspend fun getRegisteredMerchants(): Response<MerchantListResponse>

    @DELETE("api/v1/merchants/{id}")
    suspend fun deleteMerchant(
        @Path("id") merchantId: Int
    ): Response<Map<String, Any>>

    @POST("api/v1/blacklist/block")
    suspend fun blockEntityOnServer(
        @Body request: BlacklistBlockRequest
    ): Response<Map<String, Any>>
}

