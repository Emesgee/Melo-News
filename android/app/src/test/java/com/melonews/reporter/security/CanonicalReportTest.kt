package com.melonews.reporter.security

import com.google.gson.JsonObject
import com.google.gson.JsonParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.InputStreamReader

/**
 * Cross-language contract test: the Kotlin [CanonicalReport] builder MUST
 * reproduce every frozen `canonical` byte-for-byte from the SAME
 * signing_test_vectors.json the Flask server asserts (app/identity/). If this
 * fails, an Android-signed report will not verify server-side.
 *
 * The resource here is a mirror of app/identity/signing_test_vectors.json —
 * keep them identical; a drift here silently breaks signing.
 */
class CanonicalReportTest {

    private fun loadVectors(): JsonObject {
        val stream = javaClass.getResourceAsStream("/signing_test_vectors.json")
            ?: error("signing_test_vectors.json missing from test resources")
        return JsonParser.parseReader(InputStreamReader(stream, Charsets.UTF_8)).asJsonObject
    }

    private fun strOrNull(o: JsonObject, k: String): String? {
        val e = o.get(k) ?: return null
        return if (e.isJsonNull) null else e.asString
    }

    private fun fieldsFrom(payload: JsonObject): CanonicalReport.SignedFields {
        val tagsEl = payload.get("tags")
        val tags: List<String>? =
            if (tagsEl == null || tagsEl.isJsonNull) null
            else tagsEl.asJsonArray.map { it.asString }
        return CanonicalReport.SignedFields(
            title = strOrNull(payload, "title"),
            body = strOrNull(payload, "body"),
            city = strOrNull(payload, "city"),
            country = strOrNull(payload, "country"),
            lat = strOrNull(payload, "lat"),
            lon = strOrNull(payload, "lon"),
            severity = strOrNull(payload, "severity"),
            isSensitive = strOrNull(payload, "is_sensitive") ?: "false",
            sourceType = strOrNull(payload, "source_type"),
            subject = strOrNull(payload, "subject"),
            tags = tags,
            mediaSha256 = strOrNull(payload, "media_sha256"),
            publicKey = strOrNull(payload, "public_key") ?: "",
            publishedAt = strOrNull(payload, "published_at"),
            localId = strOrNull(payload, "local_id"),
        )
    }

    @Test
    fun canonicalMessageMatchesFrozenVectors() {
        val cases = loadVectors().getAsJsonArray("canonical_message")
        assertTrue("expected at least one vector", cases.size() > 0)
        for (el in cases) {
            val case = el.asJsonObject
            val name = case.get("name").asString
            val expected = case.get("canonical").asString
            val produced = CanonicalReport.json(fieldsFrom(case.getAsJsonObject("payload")))
            assertEquals("canonical mismatch: $name", expected, produced)
        }
    }

    @Test
    fun formatCoordIsFixedFiveDecimals() {
        assertEquals("10.00000", CanonicalReport.formatCoord(10.0))
        assertEquals("31.28840", CanonicalReport.formatCoord(31.2884))
        assertEquals("-0.10000", CanonicalReport.formatCoord(-0.1))
        assertEquals(null, CanonicalReport.formatCoord(null))
    }
}
