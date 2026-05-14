package com.melonews.reporter.ui.anon

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.view.View
import android.widget.ArrayAdapter
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.lifecycle.lifecycleScope
import com.google.android.gms.location.LocationServices
import com.google.android.material.snackbar.Snackbar
import com.melonews.reporter.data.api.ApiClient
import com.melonews.reporter.data.local.AnonymousDraft
import com.melonews.reporter.data.local.AppDatabaseFactory
import com.melonews.reporter.databinding.ActivityAnonymousSubmitBinding
import com.melonews.reporter.security.MediaSanitizer
import com.melonews.reporter.sync.AnonymousDraftSyncManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID

/**
 * One-shot anonymous submission flow.
 *
 * Posts directly to /api/stories/anonymous-ingest with no JWT. Does NOT
 * touch the local Room queue, SyncManager, or MeshRelayManager — those
 * are account-mode features. Requires live connectivity; offline
 * resilience for anonymous submission is the planned text-mesh follow-up.
 *
 * Media files are sanitized through MediaSanitizer before upload so a
 * reporter's GPS / device tags never leave the phone embedded in the
 * media bytes. The server also sanitizes, but the SAS-direct flow is
 * not used here, so client-side sanitization is the only safety layer
 * before the request leaves the device.
 */
class AnonymousSubmitActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAnonymousSubmitBinding
    private var attachedMediaFile: File? = null
    private var cameraImageUri: Uri? = null
    private var currentLat: Double? = null
    private var currentLon: Double? = null

    private val maxMediaBytes: Long = 50L * 1024 * 1024  // mirror server cap

    // ── Permission / picker launchers ─────────────────────────────────────

    private val locationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { granted ->
        if (granted.values.any { it }) fetchLocation()
        else snack("Location permission denied")
    }

    private val cameraLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            cameraImageUri?.path?.let { path ->
                val file = File(path)
                if (file.length() > maxMediaBytes) {
                    snack("Media is over 50 MB — choose a smaller file.")
                    return@registerForActivityResult
                }
                attachedMediaFile = file
                binding.tvMediaName.text = "Media attached"
                binding.tvMediaName.visibility = View.VISIBLE
            }
        }
    }

    private val galleryLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let {
            val file = uriToFile(it) ?: return@let
            if (file.length() > maxMediaBytes) {
                snack("Media is over 50 MB — choose a smaller file.")
                file.delete()
                return@let
            }
            attachedMediaFile = file
            binding.tvMediaName.text = "Media attached"
            binding.tvMediaName.visibility = View.VISIBLE
        }
    }

    // ── Lifecycle ─────────────────────────────────────────────────────────

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAnonymousSubmitBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.spinnerSeverity.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            listOf("LOW", "MEDIUM", "HIGH")
        )

        binding.btnGetLocation.setOnClickListener { requestLocation() }
        binding.btnAttachMedia.setOnClickListener { showMediaPicker() }
        binding.btnSubmit.setOnClickListener { submit() }
    }

    // ── Submission ────────────────────────────────────────────────────────

    private fun submit() {
        val title = binding.etTitle.text.toString().trim()
        if (title.isEmpty()) {
            snack("Title is required.")
            return
        }

        val body = binding.etBody.text.toString().trim().ifBlank { null }
        val city = binding.etCity.text.toString().trim().ifBlank { null }
        val severity = binding.spinnerSeverity.selectedItem.toString()

        // Stable id generated once per submission. Used as the server
        // submission_id when posting directly so a double-tap retry is
        // idempotent, and as the AnonymousDraft primary key when queued
        // offline so the eventual sync uses the same key.
        val submissionId = UUID.randomUUID().toString()

        setLoading(true)

        if (!isOnline()) {
            queueDraftOffline(submissionId, title, body, city, severity)
            return
        }

        lifecycleScope.launch {
            try {
                val mediaPart = withContext(Dispatchers.IO) { buildMediaPart() }
                val response = ApiClient.api.anonymousIngest(
                    title = title.toPlain(),
                    body = body?.toPlain(),
                    city = city?.toPlain(),
                    country = null,
                    severity = severity.toPlain(),
                    lat = currentLat?.toString()?.toPlain(),
                    lon = currentLon?.toString()?.toPlain(),
                    submissionId = submissionId.toPlain(),
                    media = mediaPart,
                )

                if (response.isSuccessful) {
                    onSubmitted(queued = false)
                } else {
                    val code = response.code()
                    val msg = when (code) {
                        429 -> "Rate limit reached. Try again later."
                        413 -> "Media file is too large (50 MB max)."
                        else -> "Server rejected the submission (HTTP $code)."
                    }
                    snack(msg)
                    setLoading(false)
                }
            } catch (e: Exception) {
                // Network blew up mid-request — queue the draft so we don't
                // lose the user's work. The sync manager will retry on next
                // connectivity event.
                queueDraftOffline(submissionId, title, body, city, severity, reason = e.message)
            }
        }
    }

    /**
     * Move the picked media file into the app's private files dir so it
     * outlives this Activity and survives an OS cacheDir cleanup. Returns
     * the new path, or null if there was no media or the copy failed.
     */
    private fun stageMediaForDraft(draftId: String): String? {
        val raw = attachedMediaFile?.takeIf { it.exists() } ?: return null
        return try {
            val dir = File(filesDir, "anonymous-drafts").apply { mkdirs() }
            val ext = raw.extension.ifBlank { "bin" }
            val dest = File(dir, "$draftId.$ext")
            raw.inputStream().use { input ->
                dest.outputStream().use { output -> input.copyTo(output) }
            }
            dest.absolutePath
        } catch (e: Exception) {
            null
        }
    }

    private fun queueDraftOffline(
        submissionId: String,
        title: String,
        body: String?,
        city: String?,
        severity: String,
        reason: String? = null,
    ) {
        lifecycleScope.launch(Dispatchers.IO) {
            val stagedPath = stageMediaForDraft(submissionId)
            val draft = AnonymousDraft(
                id = submissionId,
                title = title,
                body = body,
                city = city,
                country = null,
                lat = currentLat,
                lon = currentLon,
                severity = severity,
                mediaLocalPath = stagedPath,
            )
            AppDatabaseFactory.getInstance(this@AnonymousSubmitActivity)
                .anonymousDraftDao()
                .insert(draft)

            // Kick the sync manager — usually a no-op if we're truly
            // offline, but fires immediately if we just lost connection
            // briefly and it's already back by the time we land here.
            runCatching { AnonymousDraftSyncManager(this@AnonymousSubmitActivity).drainQueue() }

            withContext(Dispatchers.Main) { onSubmitted(queued = true, reason = reason) }
        }
    }

    /**
     * Sanitize media (strip EXIF/GPS, transcode-free re-mux for video) and
     * wrap it as a Multipart part. Returns null if no media is attached.
     */
    private fun buildMediaPart(): MultipartBody.Part? {
        val raw = attachedMediaFile ?: return null
        if (!raw.exists()) return null

        val cleaned = MediaSanitizer.sanitizeForUpload(this, raw)
        val mime = when (cleaned.extension.lowercase()) {
            "mp4", "mov", "m4v", "3gp", "3gpp" -> "video/mp4"
            "png" -> "image/png"
            "webp" -> "image/webp"
            "gif" -> "image/gif"
            else -> "image/jpeg"
        }
        val reqBody = cleaned.asRequestBody(mime.toMediaTypeOrNull())
        return MultipartBody.Part.createFormData("media", cleaned.name, reqBody)
    }

    private fun onSubmitted(queued: Boolean, reason: String? = null) {
        setLoading(false)
        val (title, msg) = if (queued) {
            val tail = if (reason != null) "\n\nReason for the queue: $reason" else ""
            "Saved as draft" to (
                "You are offline. Your story is saved on this device and will be sent " +
                    "to the moderation queue when connectivity returns. " +
                    "You still will not be able to track its status afterwards — " +
                    "that is the trade-off for anonymity.$tail"
                )
        } else {
            "Submission received" to (
                "Your story is queued for editorial review. You will not be able to " +
                    "track its status — that is the trade-off for anonymity."
                )
        }

        AlertDialog.Builder(this)
            .setTitle(title)
            .setMessage(msg)
            .setCancelable(false)
            .setPositiveButton("Submit another") { _, _ -> clearForm() }
            .setNegativeButton("Done") { _, _ -> finish() }
            .show()
    }

    private fun clearForm() {
        binding.etTitle.text?.clear()
        binding.etBody.text?.clear()
        binding.etCity.text?.clear()
        binding.spinnerSeverity.setSelection(0)
        binding.tvMediaName.visibility = View.GONE
        binding.tvLocationStatus.visibility = View.GONE
        attachedMediaFile = null
        currentLat = null
        currentLon = null
    }

    // ── Location ──────────────────────────────────────────────────────────

    private fun requestLocation() {
        val perms = arrayOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION
        )
        val granted = perms.all {
            ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
        }
        if (granted) fetchLocation() else locationPermissionLauncher.launch(perms)
    }

    private fun fetchLocation() {
        val client = LocationServices.getFusedLocationProviderClient(this)
        try {
            client.lastLocation.addOnSuccessListener { loc ->
                if (loc != null) {
                    currentLat = loc.latitude
                    currentLon = loc.longitude
                    binding.tvLocationStatus.text = "%.5f, %.5f".format(loc.latitude, loc.longitude)
                    binding.tvLocationStatus.visibility = View.VISIBLE
                } else {
                    snack("Location unavailable — type the city manually instead.")
                }
            }
        } catch (e: SecurityException) {
            snack("Location permission denied.")
        }
    }

    // ── Media picker ──────────────────────────────────────────────────────

    private fun showMediaPicker() {
        val items = arrayOf("Take Photo", "Record Video", "Choose from Gallery")
        AlertDialog.Builder(this)
            .setTitle("Attach Media")
            .setItems(items) { _, which ->
                when (which) {
                    0 -> launchCamera(MediaStore.ACTION_IMAGE_CAPTURE)
                    1 -> launchCamera(MediaStore.ACTION_VIDEO_CAPTURE)
                    2 -> galleryLauncher.launch("*/*")
                }
            }
            .show()
    }

    private fun launchCamera(action: String) {
        try {
            val dir = getExternalFilesDir(
                if (action == MediaStore.ACTION_IMAGE_CAPTURE) Environment.DIRECTORY_PICTURES
                else Environment.DIRECTORY_MOVIES
            ) ?: cacheDir
            dir.mkdirs()
            val ext = if (action == MediaStore.ACTION_IMAGE_CAPTURE) ".jpg" else ".mp4"
            val file = File.createTempFile(
                "anon_${SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())}",
                ext,
                dir
            )
            cameraImageUri = FileProvider.getUriForFile(
                this,
                "$packageName.fileprovider",
                file
            )
            val intent = Intent(action).apply {
                putExtra(MediaStore.EXTRA_OUTPUT, cameraImageUri)
                addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            if (intent.resolveActivity(packageManager) != null) {
                cameraLauncher.launch(intent)
            } else {
                snack("No camera app found on this device.")
            }
        } catch (e: Exception) {
            snack("Could not launch camera: ${e.message}")
        }
    }

    private fun uriToFile(uri: Uri): File? {
        return try {
            val stream = contentResolver.openInputStream(uri) ?: return null
            val ext = contentResolver.getType(uri)?.substringAfterLast('/') ?: "jpg"
            val tmp = File.createTempFile("anon_pick_", ".$ext", cacheDir)
            tmp.outputStream().use { out -> stream.copyTo(out) }
            tmp
        } catch (e: Exception) {
            null
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────

    private fun setLoading(loading: Boolean) {
        binding.progressBar.visibility = if (loading) View.VISIBLE else View.GONE
        binding.btnSubmit.isEnabled = !loading
    }

    private fun isOnline(): Boolean {
        val cm = getSystemService(CONNECTIVITY_SERVICE) as ConnectivityManager
        val caps = cm.getNetworkCapabilities(cm.activeNetwork) ?: return false
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    private fun String.toPlain(): RequestBody =
        toRequestBody("text/plain".toMediaTypeOrNull())

    private fun snack(msg: String) =
        Snackbar.make(binding.root, msg, Snackbar.LENGTH_LONG).show()
}
