package com.melonews.reporter.ui.submit

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import com.google.android.gms.location.LocationServices
import com.google.android.material.snackbar.Snackbar
import com.melonews.reporter.R
import com.melonews.reporter.databinding.FragmentSubmitBinding
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class SubmitFragment : Fragment() {

    private var _binding: FragmentSubmitBinding? = null
    private val binding get() = _binding!!
    private val viewModel: SubmitViewModel by viewModels()
    private var cameraImageUri: Uri? = null

    // ── Permission launchers ─────────────────────────────────────────────

    private val locationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { granted ->
        if (granted.values.any { it }) fetchLocation()
        else snack(getString(R.string.error_network))
    }

    private val cameraLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            cameraImageUri?.path?.let { path ->
                viewModel.attachedMediaFile = File(path)
                binding.tvMediaName.text = getString(R.string.media_attached)
                binding.tvMediaName.visibility = View.VISIBLE
            }
        }
    }

    private val galleryLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let {
            val file = uriToFile(it) ?: return@let
            viewModel.attachedMediaFile = file
            binding.tvMediaName.text = getString(R.string.media_attached)
            binding.tvMediaName.visibility = View.VISIBLE
        }
    }

    // ── Lifecycle ─────────────────────────────────────────────────────────

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentSubmitBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        // Severity spinner
        val severities = listOf("LOW", "MEDIUM", "HIGH")
        binding.spinnerSeverity.adapter = ArrayAdapter(
            requireContext(),
            android.R.layout.simple_spinner_dropdown_item,
            severities
        )

        binding.btnGetLocation.setOnClickListener { requestLocation() }
        binding.btnAttachMedia.setOnClickListener { showMediaPicker() }
        binding.btnSubmit.setOnClickListener { submitReport() }
        binding.btnRegisterDevice.setOnClickListener { confirmRegisterDevice() }

        viewModel.submitState.observe(viewLifecycleOwner) { state ->
            when (state) {
                is SubmitState.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.btnSubmit.isEnabled = false
                }
                is SubmitState.Success -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnSubmit.isEnabled = true
                    val msg = if (isOnline()) getString(R.string.submit_success)
                              else getString(R.string.submit_queued)
                    snack(msg)
                    clearForm()
                    viewModel.resetState()
                }
                is SubmitState.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnSubmit.isEnabled = true
                    snack(state.message)
                    viewModel.resetState()
                }
                else -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnSubmit.isEnabled = true
                }
            }
        }

        viewModel.registerState.observe(viewLifecycleOwner) { state ->
            when (state) {
                is RegisterState.Working -> {
                    binding.btnRegisterDevice.isEnabled = false
                    binding.btnRegisterDevice.text = getString(R.string.register_working)
                }
                is RegisterState.Done -> {
                    binding.btnRegisterDevice.isEnabled = true
                    binding.btnRegisterDevice.text = getString(R.string.btn_register_device)
                    showHandleDialog(state.handle)
                }
                is RegisterState.Failed -> {
                    binding.btnRegisterDevice.isEnabled = true
                    binding.btnRegisterDevice.text = getString(R.string.btn_register_device)
                    snack(getString(R.string.register_failed, state.message))
                }
            }
        }
    }

    // ── Actions ───────────────────────────────────────────────────────────

    private fun confirmRegisterDevice() {
        android.app.AlertDialog.Builder(requireContext())
            .setTitle(R.string.btn_register_device)
            .setMessage(
                "This creates your device signing key and registers your reporter " +
                    "pseudonym. Do this once, during setup."
            )
            .setPositiveButton(android.R.string.ok) { _, _ -> viewModel.registerDevice() }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun showHandleDialog(handle: String) {
        android.app.AlertDialog.Builder(requireContext())
            .setTitle(R.string.register_done_title)
            .setMessage(getString(R.string.register_done_msg, handle))
            .setPositiveButton(android.R.string.ok, null)
            .show()
    }

    private fun submitReport() {
        viewModel.submit(
            title = binding.etTitle.text.toString(),
            body = binding.etBody.text.toString(),
            city = binding.etCity.text.toString(),
            severity = binding.spinnerSeverity.selectedItem.toString()
        )
    }

    private fun requestLocation() {
        val perms = arrayOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION
        )
        val allGranted = perms.all {
            ContextCompat.checkSelfPermission(requireContext(), it) ==
                    PackageManager.PERMISSION_GRANTED
        }
        if (allGranted) fetchLocation() else locationPermissionLauncher.launch(perms)
    }

    private fun fetchLocation() {
        val client = LocationServices.getFusedLocationProviderClient(requireActivity())
        try {
            client.lastLocation.addOnSuccessListener { loc ->
                if (loc != null) {
                    viewModel.currentLat = loc.latitude
                    viewModel.currentLon = loc.longitude
                    binding.tvLocationStatus.text =
                        "%.5f, %.5f".format(loc.latitude, loc.longitude)
                    binding.tvLocationStatus.visibility = View.VISIBLE
                } else {
                    snack("Location unavailable — try again or enter city manually")
                }
            }
        } catch (e: SecurityException) {
            snack("Location permission denied")
        }
    }

    private fun showMediaPicker() {
        val items = arrayOf("Take Photo", "Record Video", "Choose from Gallery")
        android.app.AlertDialog.Builder(requireContext())
            .setTitle("Attach Media")
            .setItems(items) { _, which ->
                when (which) {
                    0 -> launchCamera(MediaStore.ACTION_IMAGE_CAPTURE)
                    1 -> launchCamera(MediaStore.ACTION_VIDEO_CAPTURE)
                    2 -> galleryLauncher.launch("image/* video/*")
                }
            }
            .show()
    }

    private fun launchCamera(action: String) {
        try {
            val dir = requireContext().getExternalFilesDir(
                if (action == MediaStore.ACTION_IMAGE_CAPTURE) Environment.DIRECTORY_PICTURES
                else Environment.DIRECTORY_MOVIES
            ) ?: requireContext().cacheDir
            dir.mkdirs()
            val ext = if (action == MediaStore.ACTION_IMAGE_CAPTURE) ".jpg" else ".mp4"
            val file = File.createTempFile(
                "media_${SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())}",
                ext, dir
            )
            cameraImageUri = FileProvider.getUriForFile(
                requireContext(),
                "${requireContext().packageName}.fileprovider",
                file
            )
            val intent = Intent(action).apply {
                putExtra(MediaStore.EXTRA_OUTPUT, cameraImageUri)
                addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            if (intent.resolveActivity(requireContext().packageManager) != null) {
                cameraLauncher.launch(intent)
            } else {
                snack("No camera app found on this device")
            }
        } catch (e: Exception) {
            snack("Could not launch camera: ${e.message}")
        }
    }

    private fun uriToFile(uri: Uri): File? {
        return try {
            val inputStream = requireContext().contentResolver.openInputStream(uri) ?: return null
            val ext = requireContext().contentResolver.getType(uri)
                ?.substringAfterLast('/') ?: "jpg"
            val tmp = File.createTempFile("pick_", ".$ext", requireContext().cacheDir)
            tmp.outputStream().use { out -> inputStream.copyTo(out) }
            tmp
        } catch (e: Exception) {
            null
        }
    }

    private fun clearForm() {
        binding.etTitle.text?.clear()
        binding.etBody.text?.clear()
        binding.etCity.text?.clear()
        binding.tvMediaName.visibility = View.GONE
        viewModel.attachedMediaFile = null
        // Keep location — reporter stays in the same place between submissions
    }

    private fun isOnline(): Boolean {
        val cm = requireContext().getSystemService(android.content.Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val caps = cm.getNetworkCapabilities(cm.activeNetwork) ?: return false
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    private fun snack(msg: String) =
        Snackbar.make(binding.root, msg, Snackbar.LENGTH_LONG).show()

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
