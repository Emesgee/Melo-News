package com.melonews.reporter.ui.auth

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.EditText
import androidx.activity.viewModels
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.snackbar.Snackbar
import com.melonews.reporter.databinding.ActivityLoginBinding
import com.melonews.reporter.security.PanicManager
import com.melonews.reporter.ui.main.MainActivity
import com.melonews.reporter.utils.BiometricHelper
import com.melonews.reporter.utils.TokenManager
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private val viewModel: LoginViewModel by viewModels { LoginViewModel.Factory(this) }
    private lateinit var tokenManager: TokenManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        tokenManager = TokenManager(applicationContext)

        // If token exists and biometric is available, offer biometric login
        lifecycleScope.launch {
            val token = tokenManager.tokenFlow.first()
            if (!token.isNullOrBlank() && BiometricHelper.isAvailable(this@LoginActivity)) {
                BiometricHelper.prompt(
                    activity = this@LoginActivity,
                    onSuccess = { goToMain() },
                    onFail = { /* stay on login screen for password */ }
                )
            }
        }

        binding.btnLogin.setOnClickListener {
            // Check if entered password matches decoy PIN first
            val enteredPin = binding.etPassword.text.toString()
            val decoyPin = PanicManager.getDecoyPin(this)
            if (decoyPin != null && enteredPin == decoyPin) {
                lifecycleScope.launch {
                    PanicManager.enterDecoyMode(applicationContext)
                    goToMain()
                }
                return@setOnClickListener
            }
            viewModel.login(
                binding.etEmail.text.toString().trim(),
                binding.etPassword.text.toString()
            )
        }

        // "No account? Register" — opens the in-app registration flow.
        // After successful register, RegisterActivity auto-logs the user
        // in and jumps straight to MainActivity.
        binding.tvRegisterLink.setOnClickListener {
            startActivity(Intent(this, RegisterActivity::class.java))
        }

        // Long-press login title to set up security PINs
        binding.root.setOnLongClickListener {
            showPinSetupDialog()
            true
        }

        viewModel.loginState.observe(this) { state ->
            when (state) {
                is LoginState.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.btnLogin.isEnabled = false
                }
                is LoginState.Success -> goToMain()
                is LoginState.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnLogin.isEnabled = true
                    Snackbar.make(binding.root, state.message, Snackbar.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun goToMain() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }

    private fun showPinSetupDialog() {
        val layout = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(60, 20, 60, 20)
        }
        val etDecoy = EditText(this).apply { hint = "Set decoy PIN (shown to attacker)" }
        layout.addView(etDecoy)

        AlertDialog.Builder(this)
            .setTitle("Security PINs")
            .setMessage("The decoy PIN makes the app appear empty when entered instead of your password. Useful if forced to unlock your phone.")
            .setView(layout)
            .setPositiveButton("Save") { _, _ ->
                val decoy = etDecoy.text.toString().trim()
                if (decoy.isNotEmpty()) {
                    PanicManager.saveDecoyPin(this, decoy)
                    Snackbar.make(binding.root, "Decoy PIN saved", Snackbar.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
}
