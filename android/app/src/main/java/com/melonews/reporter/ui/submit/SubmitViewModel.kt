package com.melonews.reporter.ui.submit

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.melonews.reporter.data.model.ApiResult
import com.melonews.reporter.data.model.IngestRequest
import com.melonews.reporter.data.repository.StoryRepository
import com.melonews.reporter.security.CanonicalReport
import com.melonews.reporter.security.PanicManager
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import java.io.File

class SubmitViewModel(app: Application) : AndroidViewModel(app) {

    private val repository = StoryRepository(app)

    private val _submitState = MutableLiveData<SubmitState>()
    val submitState: LiveData<SubmitState> = _submitState

    var currentLat: Double? = null
    var currentLon: Double? = null
    var attachedMediaFile: File? = null

    fun submit(
        title: String,
        body: String,
        city: String,
        severity: String
    ) {
        if (title.isBlank()) {
            _submitState.value = SubmitState.Error("Title is required")
            return
        }

        // Coarsen coordinates to the signed 5-decimal form here (ADR-0014), so
        // the value that gets signed, stored, and sent is one and the same.
        val request = IngestRequest(
            title = title.trim(),
            body = body.trim().ifBlank { null },
            city = city.trim().ifBlank { null },
            lat = CanonicalReport.formatCoord(currentLat),
            lon = CanonicalReport.formatCoord(currentLon),
            severity = severity
        )

        _submitState.value = SubmitState.Loading
        viewModelScope.launch {
            // Decoy mode: pretend submission succeeded but do nothing
            val isDecoy = PanicManager.decoyModeFlow(getApplication()).first()
            if (isDecoy) {
                _submitState.value = SubmitState.Success
                return@launch
            }
            _submitState.value = when (val result =
                repository.submitReport(request, attachedMediaFile)
            ) {
                is ApiResult.Success -> SubmitState.Success
                is ApiResult.Error -> SubmitState.Error(result.message)
            }
        }
    }

    fun resetState() {
        _submitState.value = SubmitState.Idle
    }
}

sealed class SubmitState {
    object Idle : SubmitState()
    object Loading : SubmitState()
    object Success : SubmitState()
    data class Error(val message: String) : SubmitState()
}
