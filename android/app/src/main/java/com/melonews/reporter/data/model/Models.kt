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

// lat/lon are STRINGS, not numbers: the server signs `payload.get('lat')`
// verbatim (ADR-0014), so the wire value must be the exact 5-decimal signed
// string. Every field below marked "(signed)" is part of the tamper-evident
// envelope (ADR-0008/0015) and must equal what ReportSigner signed; the rest
// (media_url, source_name) are server-assigned/unsigned.
data class IngestRequest(
    val title: String,                                                   // signed
    val body: String? = null,                                            // signed
    val city: String? = null,                                            // signed
    val country: String? = null,                                         // signed
    val lat: String? = null,                                             // signed (5-decimal string)
    val lon: String? = null,                                             // signed
    val severity: String = "LOW",                                        // signed
    @SerializedName("is_sensitive") val isSensitive: String = "false",   // signed ("true"/"false")
    @SerializedName("source_type") val sourceType: String = "eyewitness",// signed
    val subject: String? = null,                                         // signed
    @SerializedName("media_sha256") val mediaSha256: String? = null,     // signed (hex, or null)
    val tags: List<String>? = null,                                      // signed (sorted array)
    @SerializedName("published_at") val publishedAt: String? = null,     // signed (ISO-8601 UTC)
    @SerializedName("public_key") val publicKey: String? = null,         // signed (base64 SPKI DER)
    val signature: String? = null,                                       // the DER ECDSA signature
    @SerializedName("media_url") val mediaUrl: String? = null,           // unsigned (server ref)
    @SerializedName("source_name") val sourceName: String = "Field Reporter",
    @SerializedName("local_id") val localId: String? = null,             // signed
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
