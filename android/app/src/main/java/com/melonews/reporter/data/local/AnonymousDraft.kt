package com.melonews.reporter.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import androidx.room.TypeConverter
import java.util.UUID

/**
 * A citizen submission filed in anonymous mode while the device was
 * offline. The row's [id] doubles as the server-side `submission_id`
 * idempotency key so a flaky network can replay a sync without
 * producing duplicates in the moderation queue.
 *
 * Distinct from [LocalStory] for three reasons:
 *  - No user_id, no JWT involvement — these are posted to a different
 *    endpoint (/api/stories/anonymous-ingest).
 *  - Different lifecycle — anonymous drafts never become "owned" by a
 *    user, even after sync. They simply land in the public moderation
 *    queue and disappear from the device once synced.
 *  - Different threat model — these belong to reporters who chose the
 *    anonymous path explicitly; we never link them back to an account.
 */
@Entity(tableName = "anonymous_drafts")
data class AnonymousDraft(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),

    val title: String,
    val body: String?,
    val city: String?,
    val country: String?,
    val lat: Double?,
    val lon: Double?,
    val severity: String,
    /** Absolute path to a media file in the app's private files dir.
     *  Null for text-only drafts. The file is deleted after a successful
     *  sync so a long-stale draft can't keep media around forever. */
    val mediaLocalPath: String?,

    val syncStatus: DraftSyncStatus = DraftSyncStatus.PENDING,
    val createdAt: Long = System.currentTimeMillis(),
    val lastAttemptAt: Long? = null,
    val retryCount: Int = 0,
    val errorMessage: String? = null,
)

enum class DraftSyncStatus { PENDING, SYNCED, FAILED }

class DraftSyncStatusConverter {
    @TypeConverter
    fun fromStatus(value: DraftSyncStatus): String = value.name

    @TypeConverter
    fun toStatus(value: String): DraftSyncStatus = enumValueOf(value)
}
