package com.melonews.reporter.ui.map

import android.graphics.Color
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.lifecycleScope
import com.melonews.reporter.data.model.MapStory
import com.melonews.reporter.databinding.FragmentMapBinding
import com.melonews.reporter.sync.SyncManager
import kotlinx.coroutines.launch
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.overlay.Marker

class MapFragment : Fragment() {

    private var _binding: FragmentMapBinding? = null
    private val binding get() = _binding!!
    private val viewModel: MapViewModel by viewModels()

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentMapBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Configure OSMDroid map
        binding.mapView.apply {
            setTileSource(TileSourceFactory.MAPNIK)
            setMultiTouchControls(true)
            controller.setZoom(7.0)
            controller.setCenter(GeoPoint(31.5, 34.5)) // Palestine centre
        }

        binding.fabRefresh.setOnClickListener {
            // Drain any queued offline stories first, then refresh the map
            lifecycleScope.launch { SyncManager(requireContext()).drainQueue() }
            viewModel.loadStories()
        }

        viewModel.loading.observe(viewLifecycleOwner) { loading ->
            binding.progressBar.visibility = if (loading) View.VISIBLE else View.GONE
        }

        viewModel.error.observe(viewLifecycleOwner) { error ->
            binding.tvError.text = error ?: ""
            binding.tvError.visibility = if (error != null) View.VISIBLE else View.GONE
        }

        viewModel.stories.observe(viewLifecycleOwner) { stories ->
            plotMarkers(stories)
        }

        viewModel.loadStories()
    }

    private fun plotMarkers(stories: List<MapStory>) {
        binding.mapView.overlays.clear()
        // Track how many markers share the same position for jitter offset.
        val positionCount = mutableMapOf<String, Int>()
        stories.forEach { story ->
            val lat = story.lat ?: return@forEach
            val lon = story.lon ?: return@forEach

            // Apply a tiny golden-angle spiral offset to markers at identical coordinates
            // so each one remains individually tappable.
            val posKey = "%.5f,%.5f".format(lat, lon)
            val idx = positionCount.getOrDefault(posKey, 0)
            positionCount[posKey] = idx + 1
            val jitterRadius = idx * 0.00015 // ~17 m per step
            val jitterAngle  = idx * 2.39996 // golden-angle spiral
            val jLat = if (idx == 0) lat else lat + jitterRadius * Math.cos(jitterAngle)
            val jLon = if (idx == 0) lon else lon + jitterRadius * Math.sin(jitterAngle)

            val marker = Marker(binding.mapView).apply {
                position = GeoPoint(jLat, jLon)
                title = story.title ?: "Untitled"
                snippet = listOfNotNull(story.city, story.severity).joinToString(" · ")
                setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                // Tint by severity
                icon = resources.getDrawable(
                    android.R.drawable.ic_menu_mylocation, null
                ).mutate().also { drawable ->
                    drawable.setTint(severityColor(story.severity))
                }

            }
            binding.mapView.overlays.add(marker)
        }
        binding.mapView.invalidate()
    }

    private fun severityColor(severity: String?) = when (severity?.uppercase()) {
        "HIGH" -> Color.RED
        "MEDIUM" -> Color.parseColor("#F57C00")
        else -> Color.parseColor("#388E3C")
    }

    override fun onResume() {
        super.onResume()
        binding.mapView.onResume()
    }

    override fun onPause() {
        super.onPause()
        binding.mapView.onPause()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
