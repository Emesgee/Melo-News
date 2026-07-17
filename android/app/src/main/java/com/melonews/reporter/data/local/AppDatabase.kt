package com.melonews.reporter.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.TypeConverters

@Database(
    entities = [LocalStory::class, AnonymousDraft::class],
    // v3: LocalStory gains the signed-report columns and lat/lon become the
    // signed 5-decimal strings. Destructive fallback wipes the dev queue.
    version = 3,
    exportSchema = false,
)
@TypeConverters(SyncStatusConverter::class, DraftSyncStatusConverter::class)
abstract class AppDatabase : RoomDatabase() {
    abstract fun localStoryDao(): LocalStoryDao
    abstract fun anonymousDraftDao(): AnonymousDraftDao
}
