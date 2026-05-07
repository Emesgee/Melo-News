package com.melonews.reporter.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface LocalStoryDao {

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(story: LocalStory)

    /** All stories still waiting to reach the server. */
    @Query("SELECT * FROM local_stories WHERE syncStatus IN ('PENDING', 'FAILED') ORDER BY createdAt ASC")
    suspend fun getPending(): List<LocalStory>

    /** Live count — used by SyncManager to react when new items are queued. */
    @Query("SELECT COUNT(*) FROM local_stories WHERE syncStatus IN ('PENDING', 'FAILED')")
    fun pendingCountFlow(): Flow<Int>

    @Query("UPDATE local_stories SET syncStatus = :status, lastAttemptAt = :now, errorMessage = :error, retryCount = retryCount + 1 WHERE localId = :id")
    suspend fun updateStatus(id: String, status: SyncStatus, now: Long = System.currentTimeMillis(), error: String? = null)

    @Query("UPDATE local_stories SET syncStatus = 'SYNCED', lastAttemptAt = :now WHERE localId = :id")
    suspend fun markSynced(id: String, now: Long = System.currentTimeMillis())

    /** Remove stories synced more than 7 days ago to keep the DB small. */
    @Query("DELETE FROM local_stories WHERE syncStatus = 'SYNCED' AND lastAttemptAt < :before")
    suspend fun purgeOldSynced(before: Long)
}
