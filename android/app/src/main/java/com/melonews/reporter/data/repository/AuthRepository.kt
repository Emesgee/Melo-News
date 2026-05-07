package com.melonews.reporter.data.repository

import com.melonews.reporter.data.api.ApiClient
import com.melonews.reporter.data.model.ApiResult
import com.melonews.reporter.data.model.LoginRequest
import com.melonews.reporter.utils.TokenManager

class AuthRepository(private val tokenManager: TokenManager) {

    suspend fun login(email: String, password: String): ApiResult<Unit> {
        return try {
            val response = ApiClient.api.login(LoginRequest(email, password))
            if (response.isSuccessful) {
                val token = response.body()?.accessToken
                    ?: return ApiResult.Error("No token in response")
                tokenManager.saveToken(token)
                ApiResult.Success(Unit)
            } else {
                ApiResult.Error("Invalid credentials", response.code())
            }
        } catch (e: Exception) {
            ApiResult.Error(e.message ?: "Network error")
        }
    }

    suspend fun logout() {
        tokenManager.clearToken()
    }
}
