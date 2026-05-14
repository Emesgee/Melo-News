package com.melonews.reporter.data.model

import com.google.gson.annotations.SerializedName

// ── Auth ──────────────────────────────────────────────────────────────────

data class LoginRequest(
    val email: String,
    val password: String
)

data class LoginResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("user_id") val userId: Int?
)

data class RegisterRequest(
    val username: String,
    val email: String,
    val password: String
)

// ── Map stories ──────────────────────────────────────────────────────────

data class MapStoriesResponse(
    val items: List<MapStory>
)

data class MapStoryLocation(
    val lat: Double?,
    val lon: Double?,
    val city: String?,
    val country: String?
)

data class MapStoryMetrics(
    val severity: String?,
    @SerializedName("confidence_score") val confidenceScore: Double?
)

data class MapStory(
    val id: String,
    val title: String?,
    val location: MapStoryLocation?,
    val metrics: MapStoryMetrics?
) {
    val lat: Double? get() = location?.lat
    val lon: Double? get() = location?.lon
    val city: String? get() = location?.city
    val severity: String? get() = metrics?.severity
}

// ── Media token ──────────────────────────────────────────────────────────

data class MediaTokenResponse(
    @SerializedName("upload_url") val uploadUrl: String,
    @SerializedName("blob_url") val blobUrl: String,
    @SerializedName("blob_name") val blobName: String,
    @SerializedName("expires_at") val expiresAt: String
)

// ── Ingest ───────────────────────────────────────────────────────────────

data class IngestRequest(
    val title: String,
    val body: String? = null,
    val city: String? = null,
    val country: String? = null,
    val lat: Double? = null,
    val lon: Double? = null,
    val severity: String = "LOW",
    @SerializedName("media_url") val mediaUrl: String? = null,
    val tags: List<String>? = null,
    @SerializedName("source_name") val sourceName: String = "Field Reporter",
    @SerializedName("local_id") val localId: String? = null,
)

data class IngestResponse(
    val id: String,
    val title: String?
)

// ── Anonymous ingest ─────────────────────────────────────────────────────
// Server returns no id by design — anonymity is irrevocable, the submitter
// has no handle to come back with.

data class AnonIngestResponse(
    val status: String,
    @SerializedName("pending_review") val pendingReview: Boolean
)

// ── Shared ───────────────────────────────────────────────────────────────

sealed class ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>()
    data class Error(val message: String, val code: Int = 0) : ApiResult<Nothing>()
}
