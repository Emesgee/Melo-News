package com.melonews.reporter.utils

import androidx.biometric.BiometricManager
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_STRONG
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_WEAK
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity

object BiometricHelper {

    fun isAvailable(activity: FragmentActivity): Boolean {
        val mgr = BiometricManager.from(activity)
        return mgr.canAuthenticate(BIOMETRIC_STRONG or BIOMETRIC_WEAK) ==
                BiometricManager.BIOMETRIC_SUCCESS
    }

    fun prompt(
        activity: FragmentActivity,
        onSuccess: () -> Unit,
        onFail: () -> Unit
    ) {
        val executor = ContextCompat.getMainExecutor(activity)

        val callback = object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                onSuccess()
            }
            override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                // User cancelled or no biometric — fall back to password
                onFail()
            }
            override fun onAuthenticationFailed() {
                // Biometric not recognised — let them try again or use password
            }
        }

        val info = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Sign in to Melo News")
            .setSubtitle("Use fingerprint or face to continue")
            .setNegativeButtonText("Use password")
            .setAllowedAuthenticators(BIOMETRIC_STRONG or BIOMETRIC_WEAK)
            .build()

        BiometricPrompt(activity, executor, callback).authenticate(info)
    }
}
