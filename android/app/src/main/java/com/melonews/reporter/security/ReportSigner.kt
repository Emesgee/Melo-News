package com.melonews.reporter.security

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.security.keystore.StrongBoxUnavailableException
import android.util.Base64
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.Signature
import java.security.spec.ECGenParameterSpec

/**
 * The reporter's device identity key (ADR-0013).
 *
 * An ECDSA P-256 keypair generated inside the AndroidKeyStore — hardware-backed
 * (StrongBox where available, otherwise the TEE) and **non-extractable**: the
 * private key never enters app memory or storage, so a seized/imaged device
 * cannot export it. The public key IS the pseudonym; it is exported as base64 of
 * the X.509 SubjectPublicKeyInfo (SPKI) DER, which the Flask server decodes with
 * `load_der_public_key` (see app/identity/signing.py).
 *
 * Signatures are DER-encoded ECDSA over the canonical message
 * ([CanonicalReport.bytes]) via SHA256withECDSA, base64-encoded for transport.
 *
 * NOTE: user-authentication binding (biometric/PIN per signature) is
 * deliberately NOT set here — deferred to the ADR-0011 real-reporter hardening;
 * the sandbox drill signs without a per-report prompt.
 */
object ReportSigner {

    private const val ANDROID_KEYSTORE = "AndroidKeyStore"
    private const val KEY_ALIAS = "melonews_report_identity_p256"

    /** True once a device identity key exists. */
    fun hasKey(): Boolean = keyStore().containsAlias(KEY_ALIAS)

    /**
     * The pseudonym: base64 (standard, no line wrapping) of the SPKI DER public
     * key. Creates the keypair on first call. ~124 chars for P-256 — fits the
     * server's User.public_key VARCHAR(128).
     */
    fun publicKeyB64(): String {
        val entry = getOrCreateEntry()
        val spkiDer = entry.certificate.publicKey.encoded  // X.509 SubjectPublicKeyInfo
        return Base64.encodeToString(spkiDer, Base64.NO_WRAP)
    }

    /**
     * Sign [message] (the canonical report bytes) with the device key. Returns
     * the base64 DER ECDSA signature. Creates the keypair on first call.
     */
    fun sign(message: ByteArray): String {
        val entry = getOrCreateEntry()
        val signature = Signature.getInstance("SHA256withECDSA").apply {
            initSign(entry.privateKey)
            update(message)
        }.sign()
        return Base64.encodeToString(signature, Base64.NO_WRAP)
    }

    private fun keyStore(): KeyStore =
        KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }

    private fun getOrCreateEntry(): KeyStore.PrivateKeyEntry {
        val ks = keyStore()
        (ks.getEntry(KEY_ALIAS, null) as? KeyStore.PrivateKeyEntry)?.let { return it }
        generateKeyPair()
        return ks.getEntry(KEY_ALIAS, null) as KeyStore.PrivateKeyEntry
    }

    private fun generateKeyPair() {
        // Prefer StrongBox (dedicated secure element); fall back to TEE-backed
        // AndroidKeyStore on devices without it (ADR-0013: "TEE, or StrongBox
        // where available").
        try {
            generate(strongBox = true)
        } catch (_: StrongBoxUnavailableException) {
            generate(strongBox = false)
        }
    }

    private fun generate(strongBox: Boolean) {
        val spec = KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_SIGN)
            .setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1"))
            .setDigests(KeyProperties.DIGEST_SHA256)
            .apply { if (strongBox) setIsStrongBoxBacked(true) }
            .build()
        KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, ANDROID_KEYSTORE)
            .apply { initialize(spec) }
            .generateKeyPair()
    }
}
