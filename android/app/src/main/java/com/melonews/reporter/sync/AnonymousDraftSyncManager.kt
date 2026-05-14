package com.melonews.reporter.sync

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.util.Log
import com.melonews.reporter.data.api.ApiClient
import com.melonews.reporter.data.local.AnonymousDraft
import com.melonews.reporter.data.local.AppDatabaseFactory
import com.melonews.reporter.data.local.DraftSyncStatus
import com.melonews.reporter.security.MediaSanitizer
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.util.concurrent.TimeUnit

/**
 * Drains the anonymous-drafts queue whenever the device has internet.
 *
 * Parallel to [SyncManager] but with a much simpler model: no JWT, no
 * mesh, no per-story user_id. Each draft is posted to
 * /api/stories/anonymous-ingest with its primary-key id as the
 * server-side `submission_id` so a flaky network retry is idempotent.
 *
 * Two triggers, mirroring SyncManager:
 *  1. Room pending-count flow — fires when a new draft is queued while
 *     the device is online.
 *  2. ConnectivityManager NetworkCallback — fires when the device comes
 *     back online after a blackout, with a small jitter so a fleet of
 *     reporters re-emerging from the same blackout don't all hit the
 *     server in the same second.
 */
class AnonymousDraftSyncManager(private val context: Context) {

    companion object {
        private const val TAG = "AnonDraftSync"
        private const val MAX_RETRIES = 10
        private val SYNCED_RETENTION_MS = TimeUnit.DAYS.toMillis(2)
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val dao = AppDatabaseFactory.getInstance(context).anonymousDraftDao()
    private val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
    private val drainMutex = Mutex()

    fun start() {
        // Trigger 1: new draft queued while already online
        scope.launch {
            dao.pendingCountFlow()
                .distinctUntilChanged()
                .collect { count ->
                    if (count > 0 && isOnline()) drainQueue()
                }
        }

        // Trigger 2: device comes back online
        val request = NetworkRequest.Builder()
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build()
        cm.registerNetworkCallback(request, object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                scope.launch {
                    // Jitter so a city full of reporters re-emerging from a
                    // blackout doesn't stampede the server in the same second.
                    delay((5_000L..60_000L).random())
                    drainQueue()
                }
            }
        })
    }

    suspend fun drainQueue() {
        if (!isOnline()) return
        if (drainMutex.isLocked) return
        drainMutex.withLock {
            val pending = dao.getPending()
            for (draft in pending) {
                if (draft.retryCount >= MAX_RETRIES) {
                    dao.updateStatus(draft.id, DraftSyncStatus.FAILED, error = "Max retries exceeded")
                    continue
                }
                if (draft.syncStatus == DraftSyncStatus.FAILED && !isBackOffElapsed(draft)) continue

                try {
                    val mediaPart = buildMediaPart(draft)
                    val response = ApiClient.api.anonymousIngest(
                        title = draft.title.toPlain(),
                        body = draft.body?.toPlain(),
                        city = draft.city?.toPlain(),
                        country = draft.country?.toPlain(),
                        severity = draft.severity.toPlain(),
                        lat = draft.lat?.toString()?.toPlain(),
                        lon = draft.lon?.toString()?.toPlain(),
                        submissionId = draft.id.toPlain(),
                        media = mediaPart,
                    )

                    if (response.isSuccessful) {
                        dao.markSynced(draft.id)
                        // Delete the staged media file once the server has it.
                        draft.mediaLocalPath?.let { path ->
                            runCatching { File(path).takeIf { it.exists() }?.delete() }
                        }
                    } else {
                        val code = response.code()
                        if (code in 400..499 && code != 429) {
                            // Permanent client error (invalid payload) — don't keep retrying.
                            dao.updateStatus(draft.id, DraftSyncStatus.FAILED, error = "HTTP $code")
                        } else {
                            dao.updateStatus(draft.id, DraftSyncStatus.PENDING, error = "HTTP $code")
                        }
                    }
                } catch (e: Exception) {
                    Log.w(TAG, "drain failed for ${draft.id}: ${e.message}")
                    dao.updateStatus(draft.id, DraftSyncStatus.PENDING, error = e.message)
                }
            }

            dao.purgeOldSynced(System.currentTimeMillis() - SYNCED_RETENTION_MS)
        }
    }

    private fun buildMediaPart(draft: AnonymousDraft): MultipartBody.Part? {
        val raw = draft.mediaLocalPath?.let { File(it) }?.takeIf { it.exists() } ?: return null
        val cleaned = MediaSanitizer.sanitizeForUpload(context, raw)
        val mime = when (cleaned.extension.lowercase()) {
            "mp4", "mov", "m4v", "3gp", "3gpp" -> "video/mp4"
            "png" -> "image/png"
            "webp" -> "image/webp"
            "gif" -> "image/gif"
            else -> "image/jpeg"
        }
        val body = cleaned.asRequestBody(mime.toMediaTypeOrNull())
        return MultipartBody.Part.createFormData("media", cleaned.name, body)
    }

    private fun isOnline(): Boolean {
        val caps = cm.getNetworkCapabilities(cm.activeNetwork) ?: return false
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    private fun isBackOffElapsed(draft: AnonymousDraft): Boolean {
        val last = draft.lastAttemptAt ?: return true
        val backOffMs = minOf(
            TimeUnit.MINUTES.toMillis(1) * (1L shl draft.retryCount),
            TimeUnit.MINUTES.toMillis(30),
        )
        return System.currentTimeMillis() - last >= backOffMs
    }

    private fun String.toPlain(): RequestBody =
        toRequestBody("text/plain".toMediaTypeOrNull())
}
