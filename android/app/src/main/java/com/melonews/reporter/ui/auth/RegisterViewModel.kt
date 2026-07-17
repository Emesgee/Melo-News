package com.melonews.reporter.ui.auth

import android.content.Context
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.melonews.reporter.data.model.ApiResult
import com.melonews.reporter.data.repository.AuthRepository
import com.melonews.reporter.utils.TokenManager
import kotlinx.coroutines.launch

class RegisterViewModel(private val repository: AuthRepository) : ViewModel() {

    private val _state = MutableLiveData<RegisterState>()
    val state: LiveData<RegisterState> = _state

    fun register(username: String, email: String, password: String) {
        if (username.isBlank() || email.isBlank() || password.isBlank()) {
            _state.value = RegisterState.Error("All fields are required.")
            return
        }
        passwordRuleViolation(password)?.let { msg ->
            _state.value = RegisterState.Error(msg)
            return
        }
        _state.value = RegisterState.Loading
        viewModelScope.launch {
            _state.value = when (val result = repository.registerThenLogin(username, email, password)) {
                is ApiResult.Success -> RegisterState.Success
                is ApiResult.Error -> RegisterState.Error(result.message)
            }
        }
    }

    /**
     * Mirror of the server-side password rules in app/auth/routes.py.
     * Failing fast here saves a network round trip and gives the reporter
     * a specific message rather than the generic 400 from the API.
     */
    private fun passwordRuleViolation(p: String): String? {
        if (p.length < 8) return "Password must be at least 8 characters."
        if (!p.any { it.isLowerCase() }) return "Password must contain a lowercase letter."
        if (!p.any { it.isUpperCase() }) return "Password must contain an uppercase letter."
        if (!p.any { it.isDigit() }) return "Password must contain a digit."
        if (!p.any { it in "@\$!%*?&" }) return "Password must contain @, \$, !, %, *, ?, or &."
        return null
    }

    class Factory(context: Context) : ViewModelProvider.Factory {
        private val repo = AuthRepository(TokenManager(context.applicationContext))

        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            RegisterViewModel(repo) as T
    }
}

sealed class RegisterState {
    object Loading : RegisterState()
    object Success : RegisterState()
    data class Error(val message: String) : RegisterState()
}
