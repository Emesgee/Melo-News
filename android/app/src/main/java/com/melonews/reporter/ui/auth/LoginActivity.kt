package com.melonews.reporter.ui.auth

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.snackbar.Snackbar
import com.melonews.reporter.databinding.ActivityLoginBinding
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
            viewModel.login(
                binding.etEmail.text.toString().trim(),
                binding.etPassword.text.toString()
            )
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
}
