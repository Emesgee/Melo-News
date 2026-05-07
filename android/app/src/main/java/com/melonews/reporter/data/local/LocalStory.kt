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
    val lat: Double?,
    val lon: Double?,
    val severity: String?,
    val tags: String?,           // comma-separated
    val subject: String?,
    val mediaLocalPath: String?, // absolute path on this device; null = text-only

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
