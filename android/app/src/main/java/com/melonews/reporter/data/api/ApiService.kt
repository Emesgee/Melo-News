package com.melonews.reporter.data.api

import com.melonews.reporter.data.model.*
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    // ── Auth ─────────────────────────────────────────────────────────────

    @POST("api/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

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
}
