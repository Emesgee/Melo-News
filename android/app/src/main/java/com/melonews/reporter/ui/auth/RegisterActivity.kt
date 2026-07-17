package com.melonews.reporter.ui.auth

import android.content.Intent
import android.os.Bundle
import android.view.View
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.snackbar.Snackbar
import com.melonews.reporter.databinding.ActivityRegisterBinding
import com.melonews.reporter.ui.main.MainActivity

/**
 * Account creation on the device. Posts to /api/auth/register and, on
 * success, immediately calls /api/auth/login with the same credentials
 * so the reporter doesn't have to retype their password.
 *
 * Failures surface the server's actual message (e.g. "Email is already
 * registered") via the AuthRepository error parser, so the reporter
 * sees something specific rather than a generic "registration failed".
 */
class RegisterActivity : AppCompatActivity() {

    private lateinit var binding: ActivityRegisterBinding
    private val viewModel: RegisterViewModel by viewModels { RegisterViewModel.Factory(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRegisterBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnRegister.setOnClickListener {
            viewModel.register(
                username = binding.etUsername.text.toString().trim(),
                email = binding.etEmail.text.toString().trim(),
                password = binding.etPassword.text.toString(),
            )
        }

        binding.tvSignInLink.setOnClickListener { finish() }  // back to LoginActivity

        viewModel.state.observe(this) { state ->
            when (state) {
                is RegisterState.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.btnRegister.isEnabled = false
                }
                is RegisterState.Success -> {
                    // Auto-login already saved the JWT in TokenManager.
                    // Replace the auth stack so back doesn't return here.
                    val intent = Intent(this, MainActivity::class.java)
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
                    startActivity(intent)
                    finish()
                }
                is RegisterState.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnRegister.isEnabled = true
                    Snackbar.make(binding.root, state.message, Snackbar.LENGTH_LONG).show()
                }
            }
        }
    }
}
