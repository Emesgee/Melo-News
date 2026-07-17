package com.melonews.reporter.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import androidx.room.TypeConverter
import java.util.UUID

/**
 * A field-reporter submission held locally until it can be delivered to the server
 * (either directly over internet or relayed via a peer device).
 *
 * sync_status lifecycle:
 *   PENDING  → created on this device, not yet sent anywhere
 *   RELAYED  → handed to a peer device for forwarding (no internet path available)
 *   SYNCED   → confirmed received by the Flask backend (safe to ignore / expire)
 */
@Entity(tableName = "local_stories")
data class LocalStory(
    /** Stable UUID generated on creation — prevents duplicate ingestion on the server. */
    @PrimaryKey
    val localId: String = UUID.randomUUID().toString(),

    // Core story fields matching IngestRequest
    val title: String,
    val body: String,
    val city: String?,
    val country: String?,
    // lat/lon are the exact 5-decimal SIGNED strings (ADR-0014), stored verbatim
    // so the send path never re-derives them and the signature stays valid.
    val lat: String?,
    val lon: String?,
    val severity: String?,
    val tags: String?,           // comma-separated, stored in the SIGNED (sorted) order
    val subject: String?,
    // mediaLocalPath points at the already-SANITIZED file (StoryRepository
    // sanitizes at authoring time) — the exact bytes whose hash was signed.
    val mediaLocalPath: String?, // null = text-only

    // On-device signature bundle (ADR-0013/0015), computed at authoring time so
    // it survives offline queueing and mesh relay (a relaying peer has no key).
    // Null on any legacy/unsigned row.
    val publishedAt: String? = null,   // ISO-8601 UTC, signed attestation time
    val isSensitive: Boolean = false,  // signed as "true"/"false" on the wire
    val sourceType: String? = null,    // signed
    val mediaSha256: String? = null,   // signed hex digest of the sanitized bytes
    val signature: String? = null,     // base64 DER ECDSA over the canonical message
    val publicKey: String? = null,     // base64 SPKI DER — the pseudonym

    val syncStatus: SyncStatus = SyncStatus.PENDING,
    val createdAt: Long = System.currentTimeMillis(),
    /** Epoch ms of last sync attempt — used for retry back-off. */
    val lastAttemptAt: Long? = null,
    val retryCount: Int = 0,
    val errorMessage: String? = null,
)

enum class SyncStatus { PENDING, RELAYED, SYNCED, FAILED }

/** Room TypeConverter so SyncStatus enum is stored as a String column. */
class SyncStatusConverter {
    @TypeConverter
    fun fromStatus(value: SyncStatus): String = value.name

    @TypeConverter
    fun toStatus(value: String): SyncStatus =
        enumValueOf(value)
}
