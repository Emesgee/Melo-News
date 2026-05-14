package com.melonews.reporter.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.TypeConverters

@Database(
    entities = [LocalStory::class, AnonymousDraft::class],
    version = 2,
    exportSchema = false,
)
@TypeConverters(SyncStatusConverter::class, DraftSyncStatusConverter::class)
abstract class AppDatabase : RoomDatabase() {
    abstract fun localStoryDao(): LocalStoryDao
    abstract fun anonymousDraftDao(): AnonymousDraftDao
}
