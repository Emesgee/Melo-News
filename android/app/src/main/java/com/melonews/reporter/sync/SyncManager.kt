package com.melonews.reporter.sync

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import com.melonews.reporter.data.api.ApiClient
import com.melonews.reporter.data.local.AppDatabase
import com.melonews.reporter.data.local.LocalStory
import com.melonews.reporter.data.local.SyncStatus
import com.melonews.reporter.data.model.IngestRequest
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.util.concurrent.TimeUnit

// Note: JWT is injected automatically by ApiClient.AuthInterceptor.

/**
 * Drains the LocalQueue whenever internet connectivity is available.
 *
 * Two triggers:
 *  1. Room pendingCountFlow — fires when a new story is queued while online.
 *  2. ConnectivityManager NetworkCallback — fires when the device regains
 *     internet after being offline (airplane mode → back online, etc.).
 *
 * Call [start] once from App.onCreate().
 */
class SyncManager(private val context: Context) {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val dao = AppDatabase.getInstance(context).localStoryDao()
    private val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
    private val drainMutex = Mutex()

    fun start() {
        // Trigger 1: new story queued while already online
        scope.launch {
            dao.pendingCountFlow()
                .distinctUntilChanged()
                .collect { count ->
                    if (count > 0 && isOnline()) {
                        drainQueue()
                    }
                }
        }

        // Trigger 2: device comes back online (airplane mode off, Wi-Fi reconnects, etc.)
        val request = NetworkRequest.Builder()
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build()

        cm.registerNetworkCallback(request, object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                scope.launch {
                    // Timing obfuscation: wait a random 30s–5min window before transmitting.
                    // This prevents network observers from correlating "device came online"
                    // with "data was sent" — protecting reporter identity and location.
                    val jitterMs = (30_000L..300_000L).random()
                    delay(jitterMs)
                    drainQueue()
                }
            }
        })
    }

    /** Attempt to send every pending/failed story to the Flask backend. */
    suspend fun drainQueue() {
        if (!isOnline()) return
        if (drainMutex.isLocked) return  // already draining, skip duplicate trigger
        drainMutex.withLock {

        val pending = dao.getPending()
        for (story in pending) {
            if (story.retryCount >= MAX_RETRIES) {
                dao.updateStatus(story.localId, SyncStatus.FAILED, error = "Max retries exceeded")
                continue
            }

            // Exponential back-off: only throttle FAILED stories, not fresh PENDING ones
            if (story.syncStatus == SyncStatus.FAILED && !isBackOffElapsed(story)) continue

            try {
                val blobUrl = story.mediaLocalPath?.let { path ->
                    uploadMedia(path, story.localId)
                }

                val request = IngestRequest(
                    title = story.title,
                    body = story.body.ifBlank { null },
                    city = story.city,
                    country = story.country,
                    lat = story.lat,
                    lon = story.lon,
                    severity = story.severity ?: "LOW",
                    mediaUrl = blobUrl,
                    tags = story.tags?.split(",")?.map { it.trim() }?.filter { it.isNotEmpty() },
                )

                val response = ApiClient.api.ingestStory(request)
                if (response.isSuccessful) {
                    dao.markSynced(story.localId)
                } else {
                    // Server rejected the payload — mark FAILED so it doesn't retry forever
                    dao.updateStatus(story.localId, SyncStatus.FAILED,
                        error = "HTTP ${response.code()}: ${response.errorBody()?.string()}")
                }
            } catch (e: Exception) {
                // Network/Tailscale not ready yet — leave as PENDING so next trigger retries immediately
                dao.updateStatus(story.localId, SyncStatus.PENDING, error = e.message)
            }
        }

        // Clean up stories synced more than 7 days ago
        dao.purgeOldSynced(System.currentTimeMillis() - TimeUnit.DAYS.toMillis(7))
        } // end withLock
    }

    private suspend fun uploadMedia(localPath: String, @Suppress("UNUSED_PARAMETER") storyId: String): String? {
        val file = File(localPath)
        if (!file.exists()) return null

        val ext = file.extension.ifBlank { "jpg" }
        val tokenResp = ApiClient.api.getMediaToken(ext)
        if (!tokenResp.isSuccessful || tokenResp.code() == 503) return null

        val info = tokenResp.body() ?: return null
        val mimeType = when (ext.lowercase()) {
            "mp4", "mpeg", "mov" -> "video/mp4"
            "avi" -> "video/avi"
            "webm" -> "video/webm"
            "png" -> "image/png"
            "gif" -> "image/gif"
            "webp" -> "image/webp"
            else -> "image/jpeg"
        }
        val body = file.asRequestBody(mimeType.toMediaType())
        val req = Request.Builder()
            .url(info.uploadUrl)
            .put(body)
            .addHeader("x-ms-blob-type", "BlockBlob")
            .build()
        val ok = ApiClient.rawOkHttpClient.newCall(req).execute().use { it.isSuccessful }
        return if (ok) info.blobUrl else null
    }

    private fun isOnline(): Boolean {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val cap = cm.getNetworkCapabilities(cm.activeNetwork) ?: return false
        return cap.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    private fun isBackOffElapsed(story: LocalStory): Boolean {
        val last = story.lastAttemptAt ?: return true
        val backOffMs = minOf(
            TimeUnit.MINUTES.toMillis(1) * (1L shl story.retryCount), // 1m, 2m, 4m, 8m …
            TimeUnit.MINUTES.toMillis(30)                               // capped at 30 min
        )
        return System.currentTimeMillis() - last >= backOffMs
    }

    companion object {
        private const val MAX_RETRIES = 10
    }
}
