package com.melonews.reporter.data.repository

import com.melonews.reporter.data.api.ApiClient
import com.melonews.reporter.data.model.ApiResult
import com.melonews.reporter.data.model.LoginRequest
import com.melonews.reporter.data.model.RegisterRequest
import com.melonews.reporter.utils.TokenManager
import org.json.JSONObject

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

    /**
     * Register then immediately log in with the same credentials so the
     * reporter doesn't have to retype their password. The server's
     * /api/auth/register endpoint returns no JWT, hence the second call.
     */
    suspend fun registerThenLogin(
        username: String,
        email: String,
        password: String,
    ): ApiResult<Unit> {
        return try {
            val response = ApiClient.api.register(RegisterRequest(username, email, password))
            if (!response.isSuccessful) {
                val msg = parseServerError(response.errorBody()?.string())
                    ?: defaultRegisterError(response.code())
                return ApiResult.Error(msg, response.code())
            }
            login(email, password)
        } catch (e: Exception) {
            ApiResult.Error(e.message ?: "Network error")
        }
    }

    suspend fun logout() {
        tokenManager.clearToken()
    }

    private fun parseServerError(body: String?): String? {
        if (body.isNullOrBlank()) return null
        return try {
            val json = JSONObject(body)
            json.optString("error").takeIf { it.isNotBlank() }
                ?: json.optString("message").takeIf { it.isNotBlank() }
        } catch (e: Throwable) {
            null
        }
    }

    private fun defaultRegisterError(code: Int): String = when (code) {
        400 -> "Check your details — password must be 8+ characters with upper, lower, digit, and a special character (@\$!%*?&)."
        409 -> "Email is already registered."
        429 -> "Too many attempts — wait a minute and try again."
        else -> "Registration failed (HTTP $code)"
    }
}
