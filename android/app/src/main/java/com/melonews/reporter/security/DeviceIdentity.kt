package com.melonews.reporter.security

import java.security.MessageDigest

/**
 * The device's pseudonymous identity (ADR-0003 / ADR-0013).
 *
 * Thin facade over [ReportSigner]: the public key IS the pseudonym, and
 * [handle] is the human-readable `k-xxxx` label the reader/steward sees. The
 * derivation MUST match the server's `derive_handle`
 * (app/identity/signing.py) — SHA-256 of the base64 public key string, first 10
 * hex chars — so the tester can read a handle off the phone and the steward can
 * vouch that exact pseudonym (ADR-0016).
 */
object DeviceIdentity {

    /** base64 SPKI DER of the P-256 key; creates the key on first call. */
    fun publicKeyB64(): String = ReportSigner.publicKeyB64()

    /** Whether a device key already exists (no side effect). */
    fun isRegistered(): Boolean = ReportSigner.hasKey()

    /** The `k-xxxx` pseudonym handle for this device's key. */
    fun handle(): String = deriveHandle(publicKeyB64())

    /** Server-matching handle derivation (see app/identity/signing.py). */
    fun deriveHandle(publicKeyB64: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(publicKeyB64.trim().toByteArray(Charsets.UTF_8))
        val hex = digest.joinToString("") { "%02x".format(it) }
        return "k-" + hex.substring(0, 10)
    }
}
