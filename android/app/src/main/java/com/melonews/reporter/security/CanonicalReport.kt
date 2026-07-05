package com.melonews.reporter.security

import java.util.Locale

/**
 * The canonical signing message (ADR-0014 / ADR-0015).
 *
 * MUST reproduce, byte-for-byte, what the Flask server rebuilds in
 * `app/identity/signing.py::canonical_message`, which is:
 *
 *     json.dumps(doc, sort_keys=True, separators=(",",":"), ensure_ascii=False)
 *
 * A JSON library (Gson/Moshi) will NOT match that — different key ordering,
 * spacing, HTML-escaping of `<>&=`, and unicode escaping. So the JSON is
 * hand-built here to match CPython's `json` module exactly:
 *   - keys sorted ascending by code point,
 *   - compact separators (`,` and `:`, no spaces),
 *   - raw UTF-8 (non-ASCII NOT escaped — matches ensure_ascii=False),
 *   - only `"`, `\`, and control chars U+0000..U+001F escaped,
 *   - explicit `null` for absent fields.
 *
 * Every signed value is a JSON string or null EXCEPT `tags` (a sorted array of
 * strings). The client is the sole formatter: coordinates are fixed 5-decimal
 * strings (see [formatCoord]), is_sensitive is "true"/"false", media_sha256 is
 * a lowercase hex digest or null, published_at is an ISO-8601 UTC string.
 *
 * The frozen cross-language contract is `signing_test_vectors.json` (mirrored
 * from app/identity/), asserted by CanonicalReportTest AND the server tests.
 */
object CanonicalReport {

    /**
     * The exact fields bound by the signature (ADR-0008 scope). Coordinates,
     * is_sensitive, and media_sha256 arrive already client-formatted as strings;
     * this object never re-formats (it only assembles), so the bytes it signs
     * are the bytes it sends.
     */
    data class SignedFields(
        val title: String?,
        val body: String?,
        val city: String?,
        val country: String?,
        val lat: String?,          // fixed 5-decimal string, e.g. "31.28840"
        val lon: String?,
        val severity: String?,     // LOW | MEDIUM | HIGH
        val isSensitive: String,   // "true" | "false"
        val sourceType: String?,   // eyewitness | secondhand | official | unknown
        val subject: String?,
        val tags: List<String>?,   // sorted at build time; null when empty
        val mediaSha256: String?,  // lowercase hex, or null when text-only
        val publicKey: String,     // base64 SPKI DER of the P-256 key
        val publishedAt: String?,  // ISO-8601 UTC, e.g. "2026-07-05T14:03:00Z"
        val localId: String?,
    )

    /** The canonical bytes to sign / that the server verifies. */
    fun bytes(fields: SignedFields): ByteArray = json(fields).toByteArray(Charsets.UTF_8)

    /** The canonical string (UTF-8). Exposed for the cross-language vector test. */
    fun json(fields: SignedFields): String {
        // key -> value; String, null, or List<String> (tags) only.
        val doc = linkedMapOf<String, Any?>(
            "body" to fields.body,
            "city" to fields.city,
            "country" to fields.country,
            "is_sensitive" to fields.isSensitive,
            "lat" to fields.lat,
            "local_id" to fields.localId,
            "lon" to fields.lon,
            "media_sha256" to fields.mediaSha256,
            "public_key" to fields.publicKey,
            "published_at" to fields.publishedAt,
            "severity" to fields.severity,
            "source_type" to fields.sourceType,
            "subject" to fields.subject,
            "tags" to fields.tags?.sorted(),
            "title" to fields.title,
        )
        val sb = StringBuilder("{")
        doc.keys.sorted().forEachIndexed { i, key ->
            if (i > 0) sb.append(',')
            sb.append('"').append(escape(key)).append("\":")
            appendValue(sb, doc[key])
        }
        return sb.append('}').toString()
    }

    private fun appendValue(sb: StringBuilder, value: Any?) {
        when (value) {
            null -> sb.append("null")
            is String -> sb.append('"').append(escape(value)).append('"')
            is List<*> -> {
                sb.append('[')
                value.forEachIndexed { i, el ->
                    if (i > 0) sb.append(',')
                    sb.append('"').append(escape(el as String)).append('"')
                }
                sb.append(']')
            }
            else -> throw IllegalArgumentException("unsupported signed value type: $value")
        }
    }

    /**
     * JSON string escaping identical to CPython's `json.dumps(ensure_ascii=False)`:
     * escape backslash, double-quote, the short control escapes (\b \t \n \f \r),
     * and any other control char as `\u00xx` (lowercase hex). Everything else,
     * including non-ASCII, is emitted raw. Control chars are matched by code
     * point to keep this source free of fragile literal control characters.
     */
    private fun escape(s: String): String {
        val sb = StringBuilder(s.length + 8)
        for (ch in s) {
            when {
                ch == '\\' -> sb.append("\\\\")
                ch == '"' -> sb.append("\\\"")
                ch.code == 0x08 -> sb.append("\\b")
                ch.code == 0x09 -> sb.append("\\t")
                ch.code == 0x0A -> sb.append("\\n")
                ch.code == 0x0C -> sb.append("\\f")
                ch.code == 0x0D -> sb.append("\\r")
                ch.code < 0x20 -> sb.append("\\u").append(String.format("%04x", ch.code))
                else -> sb.append(ch)
            }
        }
        return sb.toString()
    }

    /**
     * Format a coordinate to the signed form: exactly 5 fractional digits
     * (~1.1 m, ADR-0014), a deliberate privacy coarsening. The value that is
     * stored/displayed must equal this signed value. Locale.US so the decimal
     * separator is always '.'.
     */
    fun formatCoord(value: Double?): String? =
        value?.let { String.format(Locale.US, "%.5f", it) }
}
