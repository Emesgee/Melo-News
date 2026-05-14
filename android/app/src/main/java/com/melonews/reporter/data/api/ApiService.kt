package com.melonews.reporter.data.api

import com.melonews.reporter.data.model.*
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    // ── Auth ─────────────────────────────────────────────────────────────

    @POST("api/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    @POST("api/auth/register")
    suspend fun register(@Body request: RegisterRequest): Response<Unit>

    // ── Stories ───────────────────────────────────────────────────────────

    @GET("api/stories/map")
    suspend fun getMapStories(
        @Query("source") source: String = "upload",
        @Query("limit") limit: Int = 500
    ): Response<MapStoriesResponse>

    // ── Media token ───────────────────────────────────────────────────────

    @GET("api/stories/ingest/media-token")
    suspend fun getMediaToken(
        @Query("ext") ext: String
    ): Response<MediaTokenResponse>

    // ── Ingest ────────────────────────────────────────────────────────────

    @POST("api/stories/ingest")
    suspend fun ingestStory(@Body request: IngestRequest): Response<IngestResponse>

    // ── Anonymous ingest ─────────────────────────────────────────────────
    // Server route is unauthenticated (no JWT). The shared AuthInterceptor
    // omits the Authorization header when no token is stored, so this call
    // can use the same ApiClient.api instance — nothing leaks.

    @Multipart
    @POST("api/stories/anonymous-ingest")
    suspend fun anonymousIngest(
        @Part("title") title: RequestBody,
        @Part("body") body: RequestBody?,
        @Part("city") city: RequestBody?,
        @Part("country") country: RequestBody?,
        @Part("severity") severity: RequestBody?,
        @Part("lat") lat: RequestBody?,
        @Part("lon") lon: RequestBody?,
        @Part media: MultipartBody.Part?
    ): Response<AnonIngestResponse>
}
