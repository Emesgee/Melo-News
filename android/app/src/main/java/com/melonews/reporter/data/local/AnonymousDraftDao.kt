package com.melonews.reporter.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface AnonymousDraftDao {

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(draft: AnonymousDraft)

    @Query("SELECT * FROM anonymous_drafts WHERE syncStatus IN ('PENDING', 'FAILED') ORDER BY createdAt ASC")
    suspend fun getPending(): List<AnonymousDraft>

    /** Live count of unsynced drafts — drives the auto-drain trigger. */
    @Query("SELECT COUNT(*) FROM anonymous_drafts WHERE syncStatus IN ('PENDING', 'FAILED')")
    fun pendingCountFlow(): Flow<Int>

    @Query("UPDATE anonymous_drafts SET syncStatus = 'SYNCED', lastAttemptAt = :now WHERE id = :id")
    suspend fun markSynced(id: String, now: Long = System.currentTimeMillis())

    @Query("UPDATE anonymous_drafts SET syncStatus = :status, lastAttemptAt = :now, errorMessage = :error, retryCount = retryCount + 1 WHERE id = :id")
    suspend fun updateStatus(
        id: String,
        status: DraftSyncStatus,
        now: Long = System.currentTimeMillis(),
        error: String? = null,
    )

    /** Drop synced rows after a retention window so the table stays small. */
    @Query("DELETE FROM anonymous_drafts WHERE syncStatus = 'SYNCED' AND lastAttemptAt < :before")
    suspend fun purgeOldSynced(before: Long)

    /** Drop everything — used by panic wipe (anonymous drafts must die too). */
    @Query("DELETE FROM anonymous_drafts")
    suspend fun wipeAll()
}
