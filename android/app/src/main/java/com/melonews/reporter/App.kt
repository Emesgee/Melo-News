package com.melonews.reporter

import android.app.Application
import com.melonews.reporter.data.api.ApiClient
import com.melonews.reporter.data.local.AppDatabase
import com.melonews.reporter.sync.SyncManager
import org.osmdroid.config.Configuration

class App : Application() {
    override fun onCreate() {
        super.onCreate()
        ApiClient.init(this)
        // OSMDroid user agent (required)
        Configuration.getInstance().userAgentValue = packageName
        // Initialise DB (creates file on first launch)
        AppDatabase.getInstance(this)
        // Start background sync — drains local queue whenever internet is available
        SyncManager(this).start()
    }
}
