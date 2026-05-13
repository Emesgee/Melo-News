package com.melonews.reporter.security

import android.content.Context

object DatabaseKeyManager {

    private const val PREFS_FILE = "db_key_prefs"

    /** Called by panic wipe — clears any stored key material. */
    fun destroyPassphrase(context: Context) {
        context.getSharedPreferences(PREFS_FILE, Context.MODE_PRIVATE)
            .edit().clear().apply()
    }
}
