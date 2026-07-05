package com.melonews.reporter.security

import java.io.File
import java.security.MessageDigest

/**
 * SHA-256 of the media bytes, as a lowercase hex digest (ADR-0008 / ADR-0015).
 *
 * Hashed over the **sanitized** file — the bytes produced by
 * [MediaSanitizer.sanitizeForUpload] and the exact bytes uploaded to Azure — so
 * the signed `media_sha256` matches what a reader can later re-hash to verify
 * the media was not swapped (reader-side verification, ADR-0009). Lowercase hex
 * to match the server contract.
 */
object MediaHash {

    /** Lowercase hex SHA-256 of [file]'s bytes, streamed so large video is fine. */
    fun sha256Hex(file: File): String {
        val md = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(8192)
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                md.update(buffer, 0, read)
            }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }
}
