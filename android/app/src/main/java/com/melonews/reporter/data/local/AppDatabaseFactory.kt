package com.melonews.reporter.data.local

import android.content.Context
import androidx.room.Room

object AppDatabaseFactory {

    private const val DB_NAME = "melo_reporter.db"

    @Volatile private var INSTANCE: AppDatabase? = null

    fun getInstance(context: Context): AppDatabase =
        INSTANCE ?: synchronized(this) {
            INSTANCE ?: Room.databaseBuilder(
                context.applicationContext,
                AppDatabase::class.java,
                DB_NAME
            )
                // Schema additions on this app today are dev-stage drafts —
                // an installed beta DB is OK to wipe on upgrade. Replace
                // with explicit Migration objects before any release that
                // expects to preserve queued user data.
                .fallbackToDestructiveMigration()
                .build()
                .also { INSTANCE = it }
        }

    fun dropInstance() {
        INSTANCE = null
    }
}
