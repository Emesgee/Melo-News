package com.melonews.reporter.ui.landing

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import com.melonews.reporter.BuildConfig
import com.melonews.reporter.R
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

        // Hide the anonymous option unless the server actually accepts it.
        // The endpoint 403s when ANONYMOUS_INGEST_ENABLED is false (ADR-0007),
        // and the offline draft queue retries silently — so a tester who used
        // this path would believe their report was filed when it was discarded.
        if (BuildConfig.ANONYMOUS_ENABLED) {
            binding.anonymousBlock.visibility = View.VISIBLE
            binding.btnAnonymous.setOnClickListener {
                startActivity(Intent(this, AnonymousSubmitActivity::class.java))
            }
        } else {
            binding.anonymousBlock.visibility = View.GONE
            // With one path left, "How would you like to report?" is a question
            // with no choice behind it.
            binding.txtLandingSubtitle.text = getString(R.string.landing_subtitle_account_only)
        }

        binding.btnSignIn.setOnClickListener {
            startActivity(Intent(this, LoginActivity::class.java))
        }
    }
}
