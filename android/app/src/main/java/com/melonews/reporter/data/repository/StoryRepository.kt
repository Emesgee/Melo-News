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

    suspend fun submitReport(request: IngestRequest, mediaFile: File?): ApiResult<String> {
        val local = LocalStory(
            title          = request.title,
            body           = request.body ?: "",
            city           = request.city,
            country        = request.country,
            lat            = request.lat,
            lon            = request.lon,
            severity       = request.severity,
            tags           = request.tags?.joinToString(","),
            subject        = null,
            mediaLocalPath = mediaFile?.absolutePath,
        )
        dao.insert(local)

        // Fire-and-forget: never await the network — return success immediately.
        // SyncManager's NetworkCallback handles the offline→online transition.
        if (isOnline()) {
            CoroutineScope(SupervisorJob() + Dispatchers.IO).launch {
                try { syncManager.drainQueue() } catch (_: Exception) { }
            }
        }

        return ApiResult.Success(local.localId)
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
