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

class LoginViewModel(private val repository: AuthRepository) : ViewModel() {

    private val _loginState = MutableLiveData<LoginState>()
    val loginState: LiveData<LoginState> = _loginState

    fun login(email: String, password: String) {
        if (email.isBlank() || password.isBlank()) {
            _loginState.value = LoginState.Error("Email and password are required")
            return
        }
        _loginState.value = LoginState.Loading
        viewModelScope.launch {
            _loginState.value = when (val result = repository.login(email, password)) {
                is ApiResult.Success -> LoginState.Success
                is ApiResult.Error -> LoginState.Error(result.message)
            }
        }
    }

    class Factory(context: Context) : ViewModelProvider.Factory {
        private val repo = AuthRepository(TokenManager(context.applicationContext))

        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            LoginViewModel(repo) as T
    }
}

sealed class LoginState {
    object Loading : LoginState()
    object Success : LoginState()
    data class Error(val message: String) : LoginState()
}
