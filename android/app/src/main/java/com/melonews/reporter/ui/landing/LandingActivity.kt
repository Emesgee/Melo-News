package com.melonews.reporter.ui.landing

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.melonews.reporter.databinding.ActivityLandingBinding
import com.melonews.reporter.ui.anon.AnonymousSubmitActivity
import com.melonews.reporter.ui.auth.LoginActivity

/**
 * App entry point. Presents an explicit choice between anonymous
 * submission (safer default) and account-based access. Avoids
 * auto-logging the reporter in just because a JWT is sitting on disk —
 * a seized device shouldn't reveal an identity by default.
 *
 * Anonymous mode does NOT touch the local Room queue, SyncManager, or
 * MeshRelayManager — those are account-mode features. Anonymous is a
 * deliberate "one shot, no trace" path that requires live connectivity.
 */
class LandingActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLandingBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLandingBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnAnonymous.setOnClickListener {
            startActivity(Intent(this, AnonymousSubmitActivity::class.java))
        }

        binding.btnSignIn.setOnClickListener {
            startActivity(Intent(this, LoginActivity::class.java))
        }
    }
}
