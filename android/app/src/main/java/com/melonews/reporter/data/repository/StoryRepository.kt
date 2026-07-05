package com.melonews.reporter.data.repository

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import com.melonews.reporter.data.api.ApiClient
import com.melonews.reporter.data.local.AppDatabaseFactory
import com.melonews.reporter.data.local.LocalStory
import com.melonews.reporter.data.model.ApiResult
import com.melonews.reporter.data.model.IngestRequest
import com.melonews.reporter.data.model.MapStory
import com.melonews.reporter.security.CanonicalReport
import com.melonews.reporter.security.MediaHash
import com.melonews.reporter.security.MediaSanitizer
import com.melonews.reporter.security.ReportSigner
import com.melonews.reporter.sync.SyncManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.time.Instant
import java.time.temporal.ChronoUnit
import java.util.UUID

class StoryRepository(private val context: Context) {

    private val dao = AppDatabaseFactory.getInstance(context).localStoryDao()
    private val syncManager = SyncManager(context)

    private fun isOnline(): Boolean {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val caps = cm.getNetworkCapabilities(cm.activeNetwork) ?: return false
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    suspend fun getMapStories(): ApiResult<List<MapStory>> {
        return try {
            val response = ApiClient.api.getMapStories()
            if (response.isSuccessful) {
                ApiResult.Success(response.body()?.items ?: emptyList())
            } else {
                ApiResult.Error("Failed to load stories", response.code())
            }
        } catch (e: Exception) {
            ApiResult.Error(e.message ?: "Network error")
        }
    }

    /**
     * Sign the report on this device, then queue it. Signing happens HERE, at
     * authoring time — not at send time — so the signature survives offline
     * queueing and mesh relay (a relaying peer has no key). The media is
     * sanitized and hashed now too, so the signed `media_sha256` is fixed to the
     * exact bytes the sync layer will upload.
     */
    suspend fun submitReport(request: IngestRequest, mediaFile: File?): ApiResult<String> =
        withContext(Dispatchers.IO) {
            // 1. Sanitize + hash the media once, now. The sync layer uploads this
            //    exact file (it does NOT re-sanitize), so bytes == signed hash.
            val sanitized: File? = mediaFile?.let { MediaSanitizer.sanitizeForUpload(context, it) }
            val mediaSha256: String? = sanitized?.let { MediaHash.sha256Hex(it) }

            // 2. Assemble the exact signed envelope (ADR-0008/0014/0015). local_id
            //    is fixed up front so the signature covers the same id we send.
            val localId = UUID.randomUUID().toString()
            val publishedAt = Instant.now().truncatedTo(ChronoUnit.SECONDS).toString() // ...Z
            val tags = request.tags?.map { it.trim() }?.filter { it.isNotEmpty() }?.sorted()
            val publicKey = ReportSigner.publicKeyB64()

            val fields = CanonicalReport.SignedFields(
                title = request.title,
                body = request.body,
                city = request.city,
                country = request.country,
                lat = request.lat,          // already the 5-decimal signed string
                lon = request.lon,
                severity = request.severity,
                isSensitive = request.isSensitive,
                sourceType = request.sourceType,
                subject = request.subject,
                tags = tags,
                mediaSha256 = mediaSha256,
                publicKey = publicKey,
                publishedAt = publishedAt,
                localId = localId,
            )
            val signature = ReportSigner.sign(CanonicalReport.bytes(fields))

            // 3. Persist the signed bundle. The sync layer rebuilds the wire
            //    request from these verbatim, so send == signed.
            val local = LocalStory(
                localId        = localId,
                title          = request.title,
                body           = request.body ?: "",
                city           = request.city,
                country        = request.country,
                lat            = request.lat,
                lon            = request.lon,
                severity       = request.severity,
                tags           = tags?.joinToString(","),
                subject        = request.subject,
                mediaLocalPath = sanitized?.absolutePath,
                publishedAt    = publishedAt,
                isSensitive    = request.isSensitive == "true",
                sourceType     = request.sourceType,
                mediaSha256    = mediaSha256,
                signature      = signature,
                publicKey      = publicKey,
            )
            dao.insert(local)

            // Fire-and-forget: never await the network — return immediately.
            // SyncManager's NetworkCallback handles the offline→online transition.
            if (isOnline()) {
                CoroutineScope(SupervisorJob() + Dispatchers.IO).launch {
                    try { syncManager.drainQueue() } catch (_: Exception) { }
                }
            }

            ApiResult.Success(localId)
        }

    private suspend fun uploadToAzure(sasUrl: String, file: File): Boolean =
        withContext(Dispatchers.IO) {
            try {
                val mimeType = when (file.extension.lowercase()) {
                    "mp4", "mpeg", "mov" -> "video/mp4"
                    "avi"                -> "video/avi"
                    "webm"               -> "video/webm"
                    "png"                -> "image/png"
                    "gif"                -> "image/gif"
                    "webp"               -> "image/webp"
                    else                 -> "image/jpeg"
                }
                val body = file.asRequestBody(mimeType.toMediaType())
                val req = Request.Builder()
                    .url(sasUrl)
                    .put(body)
                    .addHeader("x-ms-blob-type", "BlockBlob")
                    .build()
                ApiClient.rawOkHttpClient.newCall(req).execute().use { it.isSuccessful }
            } catch (e: Exception) {
                false
            }
        }
}
