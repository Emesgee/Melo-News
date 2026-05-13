package com.melonews.reporter.security

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaMetadataRetriever
import android.media.MediaMuxer
import android.os.Build
import android.util.Log
import androidx.exifinterface.media.ExifInterface
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer

/**
 * Strips identifying metadata (GPS, device serials, location atoms) from
 * an image or video before it is uploaded to cloud storage.
 *
 * For citizen journalism in hostile environments, an embedded GPS tag is
 * enough to identify a reporter's location even if every other field on
 * the submission is anonymous. We sanitize on the device — the SAS upload
 * flow goes phone → Azure directly, the server never sees the bytes, so
 * server-side stripping cannot protect this path.
 *
 * Images: decode + re-encode via Bitmap. Orientation is baked into pixel
 * data so the visual rotation survives the strip.
 *
 * Videos: MediaExtractor + MediaMuxer re-mux. Audio/video tracks are
 * copied through unchanged (no transcode, no quality loss) but the
 * container's metadata atoms — iOS `com.apple.quicktime.location.ISO6709`,
 * Android `udta/loc`, encoder/software identifiers — are dropped because
 * MediaMuxer does not carry them over. The orientation hint is preserved
 * so portrait recordings still play right-side-up.
 *
 * On any failure the original file is returned with a warning logged;
 * the upload is never blocked by sanitization.
 */
object MediaSanitizer {

    private const val TAG = "MediaSanitizer"
    private const val SANITIZED_IMAGE_QUALITY = 92
    private const val MUXER_BUFFER_BYTES = 1 * 1024 * 1024

    private val IMAGE_EXTS = setOf("jpg", "jpeg", "png", "webp")
    // MediaMuxer's MP4 output accepts MP4-family inputs reliably; other
    // containers (webm/mkv/avi) would need codec-level conversion.
    private val MP4_VIDEO_EXTS = setOf("mp4", "mov", "m4v", "3gp", "3gpp")

    fun sanitizeForUpload(context: Context, source: File): File {
        if (!source.exists()) return source

        val ext = source.extension.lowercase()
        return when (ext) {
            in IMAGE_EXTS -> sanitizeImage(context, source, ext) ?: source
            in MP4_VIDEO_EXTS -> sanitizeVideo(context, source) ?: source
            else -> {
                Log.w(TAG, "No sanitizer for .$ext (${source.name}); uploading as-is")
                source
            }
        }
    }

    // ── Image path ────────────────────────────────────────────────────────────

    private fun sanitizeImage(context: Context, source: File, ext: String): File? {
        val format = when (ext) {
            "png"  -> Bitmap.CompressFormat.PNG
            "webp" -> webpFormat()
            else   -> Bitmap.CompressFormat.JPEG
        }
        val outExt = if (ext == "jpeg") "jpg" else ext

        var decoded: Bitmap? = null
        var oriented: Bitmap? = null
        return try {
            val orientation = readImageOrientation(source)
            decoded = BitmapFactory.decodeFile(source.absolutePath)
            if (decoded == null) {
                Log.w(TAG, "decodeFile returned null for ${source.name}; uploading raw")
                return null
            }
            oriented = applyOrientation(decoded, orientation)

            val outFile = File.createTempFile("clean_", ".$outExt", context.cacheDir)
            FileOutputStream(outFile).use { out ->
                oriented.compress(format, SANITIZED_IMAGE_QUALITY, out)
            }
            outFile
        } catch (e: Throwable) {
            Log.e(TAG, "Image sanitize failed for ${source.name}: ${e.message}", e)
            null
        } finally {
            decoded?.takeIf { it !== oriented }?.recycle()
            oriented?.recycle()
        }
    }

    private fun readImageOrientation(file: File): Int = try {
        ExifInterface(file.absolutePath).getAttributeInt(
            ExifInterface.TAG_ORIENTATION,
            ExifInterface.ORIENTATION_NORMAL,
        )
    } catch (e: Throwable) {
        ExifInterface.ORIENTATION_NORMAL
    }

    private fun applyOrientation(bitmap: Bitmap, orientation: Int): Bitmap {
        val matrix = Matrix()
        when (orientation) {
            ExifInterface.ORIENTATION_ROTATE_90 -> matrix.postRotate(90f)
            ExifInterface.ORIENTATION_ROTATE_180 -> matrix.postRotate(180f)
            ExifInterface.ORIENTATION_ROTATE_270 -> matrix.postRotate(270f)
            ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> matrix.postScale(-1f, 1f)
            ExifInterface.ORIENTATION_FLIP_VERTICAL -> matrix.postScale(1f, -1f)
            ExifInterface.ORIENTATION_TRANSPOSE -> {
                matrix.postRotate(90f); matrix.postScale(-1f, 1f)
            }
            ExifInterface.ORIENTATION_TRANSVERSE -> {
                matrix.postRotate(270f); matrix.postScale(-1f, 1f)
            }
            else -> return bitmap
        }
        return Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
    }

    @Suppress("DEPRECATION")
    private fun webpFormat(): Bitmap.CompressFormat =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Bitmap.CompressFormat.WEBP_LOSSY
        } else {
            Bitmap.CompressFormat.WEBP
        }

    // ── Video path ────────────────────────────────────────────────────────────

    private fun sanitizeVideo(context: Context, source: File): File? {
        val outFile = File.createTempFile("clean_", ".mp4", context.cacheDir)
        var extractor: MediaExtractor? = null
        var muxer: MediaMuxer? = null
        var retriever: MediaMetadataRetriever? = null

        return try {
            extractor = MediaExtractor().apply { setDataSource(source.absolutePath) }
            if (extractor.trackCount == 0) {
                Log.w(TAG, "No tracks in ${source.name}; cannot sanitize")
                outFile.delete()
                return null
            }

            muxer = MediaMuxer(outFile.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)

            // Preserve playback orientation but drop location/device atoms.
            retriever = MediaMetadataRetriever().apply { setDataSource(source.absolutePath) }
            val rotation = retriever
                .extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_ROTATION)
                ?.toIntOrNull()
                ?: 0
            if (rotation != 0) muxer.setOrientationHint(rotation)

            val trackIndexMap = HashMap<Int, Int>(extractor.trackCount)
            for (i in 0 until extractor.trackCount) {
                val format = extractor.getTrackFormat(i)
                trackIndexMap[i] = muxer.addTrack(format)
                extractor.selectTrack(i)
            }

            muxer.start()

            val buffer = ByteBuffer.allocate(MUXER_BUFFER_BYTES)
            val bufferInfo = MediaCodec.BufferInfo()

            while (true) {
                val sampleSize = extractor.readSampleData(buffer, 0)
                if (sampleSize < 0) break
                val srcTrack = extractor.sampleTrackIndex
                val dstTrack = trackIndexMap[srcTrack] ?: run {
                    extractor.advance(); continue
                }
                bufferInfo.set(0, sampleSize, extractor.sampleTime, extractor.sampleFlags)
                muxer.writeSampleData(dstTrack, buffer, bufferInfo)
                extractor.advance()
            }

            muxer.stop()
            outFile
        } catch (e: Throwable) {
            Log.e(TAG, "Video sanitize failed for ${source.name}: ${e.message}", e)
            outFile.delete()
            null
        } finally {
            try { extractor?.release() } catch (_: Throwable) {}
            try { muxer?.release() } catch (_: Throwable) {}
            try { retriever?.release() } catch (_: Throwable) {}
        }
    }
}
