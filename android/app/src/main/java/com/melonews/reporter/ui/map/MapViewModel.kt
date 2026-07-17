package com.melonews.reporter.ui.map

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.melonews.reporter.data.model.ApiResult
import com.melonews.reporter.data.model.EventMarker
import com.melonews.reporter.data.repository.StoryRepository
import com.melonews.reporter.security.PanicManager
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class MapViewModel(app: Application) : AndroidViewModel(app) {

    private val repository = StoryRepository(app)

    private val _events = MutableLiveData<List<EventMarker>>()
    val events: LiveData<List<EventMarker>> = _events

    private val _error = MutableLiveData<String?>()
    val error: LiveData<String?> = _error

    private val _loading = MutableLiveData(false)
    val loading: LiveData<Boolean> = _loading

    fun loadEvents() {
        _loading.value = true
        viewModelScope.launch {
            // In decoy mode show an empty map — no incidents visible
            val isDecoy = PanicManager.decoyModeFlow(getApplication()).first()
            if (isDecoy) {
                _events.value = emptyList()
                _loading.value = false
                return@launch
            }
            when (val result = repository.getEvents()) {
                is ApiResult.Success -> {
                    _events.value = result.data.filter { it.lat != null && it.lon != null }
                    _error.value = null
                }
                is ApiResult.Error -> _error.value = result.message
            }
            _loading.value = false
        }
    }
}
