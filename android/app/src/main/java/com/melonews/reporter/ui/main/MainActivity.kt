package com.melonews.reporter.ui.main

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.KeyEvent
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.setupWithNavController
import com.melonews.reporter.R
import com.melonews.reporter.databinding.ActivityMainBinding
import com.melonews.reporter.mesh.MeshRelayManager
import com.melonews.reporter.security.PanicManager
import com.melonews.reporter.ui.auth.LoginActivity
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var meshRelayManager: MeshRelayManager

    // ── Panic gesture: volume-down x5 within 3 seconds ───────────────────
    private var volumeDownCount = 0
    private var firstVolumePressTime = 0L
    private val PANIC_PRESSES = 5
    private val PANIC_WINDOW_MS = 3_000L

    // ── Nearby / Bluetooth runtime permissions (Android 12+) ─────────────

    private val nearbyPermissions: Array<String> = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        arrayOf(
            Manifest.permission.BLUETOOTH_ADVERTISE,
            Manifest.permission.BLUETOOTH_CONNECT,
            Manifest.permission.BLUETOOTH_SCAN,
            Manifest.permission.NEARBY_WIFI_DEVICES,
        )
    } else {
        arrayOf(
            Manifest.permission.BLUETOOTH,
            Manifest.permission.BLUETOOTH_ADMIN,
            Manifest.permission.ACCESS_FINE_LOCATION,
        )
    }

    private val nearbyPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { grants ->
        if (grants.values.all { it }) {
            meshRelayManager.start()
        }
        // If denied, mesh relay is silently disabled — offline queue still works
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val navHost = supportFragmentManager
            .findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        binding.bottomNav.setupWithNavController(navHost.navController)

        meshRelayManager = MeshRelayManager(this)
        requestNearbyPermissionsAndStart()
    }

    override fun onDestroy() {
        super.onDestroy()
        meshRelayManager.stop()
    }

    // ── Panic gesture handler ─────────────────────────────────────────────

    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        if (keyCode == KeyEvent.KEYCODE_VOLUME_DOWN) {
            val now = System.currentTimeMillis()
            if (volumeDownCount == 0 || now - firstVolumePressTime > PANIC_WINDOW_MS) {
                volumeDownCount = 1
                firstVolumePressTime = now
            } else {
                volumeDownCount++
            }
            if (volumeDownCount >= PANIC_PRESSES) {
                volumeDownCount = 0
                triggerPanicWipe()
                return true
            }
        }
        return super.onKeyDown(keyCode, event)
    }

    private fun triggerPanicWipe() {
        AlertDialog.Builder(this)
            .setTitle("Wipe all data?")
            .setMessage("This will permanently delete all stories and media. This cannot be undone.")
            .setPositiveButton("Wipe now") { _, _ ->
                lifecycleScope.launch {
                    PanicManager.panicWipe(applicationContext)
                    Toast.makeText(applicationContext, "All data wiped", Toast.LENGTH_SHORT).show()
                    startActivity(Intent(this@MainActivity, LoginActivity::class.java))
                    finishAffinity()
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    // ─────────────────────────────────────────────────────────────────────

    private fun requestNearbyPermissionsAndStart() {
        val allGranted = nearbyPermissions.all {
            ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
        }
        if (allGranted) {
            meshRelayManager.start()
        } else {
            nearbyPermissionLauncher.launch(nearbyPermissions)
        }
    }
}
