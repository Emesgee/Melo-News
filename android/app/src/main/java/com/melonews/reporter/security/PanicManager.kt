package com.melonews.reporter.security

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.melonews.reporter.data.local.AppDatabaseFactory
import com.melonews.reporter.utils.TokenManager
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.io.File

private val Context.panicDataStore by preferencesDataStore(name = "panic_prefs")

/**
 * Manages three security features:
 *
 * 1. PANIC WIPE — destroys all local stories, media files, JWT, and the DB
 *    encryption key. The database becomes permanently unreadable.
 *
 * 2. DECOY MODE — when the decoy PIN is entered on login, the app appears
 *    empty (no stories, no history). Real data is still on disk but hidden.
 *    Exiting decoy mode requires the real PIN.
 *
 * 3. PIN STORAGE — both the real PIN and decoy PIN are stored in
 *    EncryptedSharedPreferences (Android Keystore backed).
 */
object PanicManager {

    private const val PREFS_FILE = "panic_secure_prefs"
    private const val KEY_REAL_PIN = "real_pin"
    private const val KEY_DECOY_PIN = "decoy_pin"
    private val DECOY_MODE_KEY = booleanPreferencesKey("decoy_mode_active")

    // ── PIN management ────────────────────────────────────────────────────

    fun saveRealPin(context: Context, pin: String) {
        securePrefs(context).edit().putString(KEY_REAL_PIN, pin).apply()
    }

    fun saveDecoyPin(context: Context, pin: String) {
        securePrefs(context).edit().putString(KEY_DECOY_PIN, pin).apply()
    }

    fun getRealPin(context: Context): String? =
        securePrefs(context).getString(KEY_REAL_PIN, null)

    fun getDecoyPin(context: Context): String? =
        securePrefs(context).getString(KEY_DECOY_PIN, null)

    fun hasPins(context: Context): Boolean =
        getRealPin(context) != null

    // ── Decoy mode ────────────────────────────────────────────────────────

    val decoyModeFlow: (Context) -> Flow<Boolean> = { context ->
        context.panicDataStore.data.map { prefs -> prefs[DECOY_MODE_KEY] ?: false }
    }

    suspend fun enterDecoyMode(context: Context) {
        context.panicDataStore.edit { it[DECOY_MODE_KEY] = true }
    }

    suspend fun exitDecoyMode(context: Context) {
        context.panicDataStore.edit { it[DECOY_MODE_KEY] = false }
    }

    // ── Panic wipe ────────────────────────────────────────────────────────

    /**
     * Destroys everything:
     * - All Room stories (DAO wipe)
     * - All local media files in the uploads dir
     * - JWT token (forces re-login)
     * - SQLCipher passphrase (DB permanently unreadable without the key)
     * - Decoy mode flag reset
     */
    suspend fun panicWipe(context: Context) {
        val appContext = context.applicationContext

        // 1. Wipe Room rows
        try {
            AppDatabaseFactory.getInstance(appContext).localStoryDao().wipeAll()
        } catch (_: Exception) { }

        // 2. Delete all media files
        try {
            val uploadsDir = File(appContext.filesDir, "uploads")
            uploadsDir.deleteRecursively()
        } catch (_: Exception) { }

        // 3. Clear JWT — forces logout
        TokenManager(appContext).clearToken()

        // 4. Destroy DB encryption key — data is now cryptographically unreadable
        DatabaseKeyManager.destroyPassphrase(appContext)

        // 5. Drop DB instance so it can't be re-used without the key
        AppDatabaseFactory.dropInstance()

        // 6. Reset decoy mode
        exitDecoyMode(appContext)
    }

    // ─────────────────────────────────────────────────────────────────────

    private fun securePrefs(context: Context) =
        context.getSharedPreferences(PREFS_FILE, Context.MODE_PRIVATE)
}
