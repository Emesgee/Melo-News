package com.melonews.reporter.mesh

import android.content.Context
import android.util.Log
import com.google.android.gms.nearby.Nearby
import com.google.android.gms.nearby.connection.AdvertisingOptions
import com.google.android.gms.nearby.connection.ConnectionInfo
import com.google.android.gms.nearby.connection.ConnectionLifecycleCallback
import com.google.android.gms.nearby.connection.ConnectionResolution
import com.google.android.gms.nearby.connection.ConnectionsStatusCodes
import com.google.android.gms.nearby.connection.DiscoveredEndpointInfo
import com.google.android.gms.nearby.connection.DiscoveryOptions
import com.google.android.gms.nearby.connection.EndpointDiscoveryCallback
import com.google.android.gms.nearby.connection.Payload
import com.google.android.gms.nearby.connection.PayloadCallback
import com.google.android.gms.nearby.connection.PayloadTransferUpdate
import com.google.android.gms.nearby.connection.Strategy
import com.google.gson.Gson
import com.melonews.reporter.data.local.AppDatabaseFactory
import com.melonews.reporter.data.local.LocalStory
import com.melonews.reporter.data.local.SyncStatus
import com.melonews.reporter.sync.SyncManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

/**
 * Mesh relay: allows offline phones to hand stories to nearby online phones.
 *
 * Strategy: CLUSTER (many-to-many, mid-range Wi-Fi + Bluetooth).
 *
 * Flow:
 *  - ADVERTISER: this device has PENDING stories → broadcasts availability.
 *  - DISCOVERER: always scanning for advertisers → connects → receives stories
 *    → inserts into local Room queue → SyncManager uploads to Flask.
 *
 * Both roles run simultaneously so every device can both send and receive.
 *
 * Call [start] once from App.onCreate() after permissions are granted.
 * The actual Nearby permission check happens at runtime in MainActivity/App.
 *
 * ── v1 scope: text-only mesh ────────────────────────────────────────────
 * Stories with attached media (photo/video) are NOT relayed in v1 — they
 * stay PENDING on the sender until direct connectivity is available, at
 * which point SyncManager uploads the media to Azure directly.
 *
 * Why this is the v1 design, not a TODO oversight:
 *   • Nearby Connections BYTES payloads are capped at 32KB, so the JSON
 *     can't include base64 media bytes. A real implementation needs a
 *     separate Payload.fromFile() leg with payload-id correlation between
 *     a header BYTES payload and the FILE payload, plus per-endpoint
 *     receive-state tracking.
 *   • Server-side idempotency keys (local_id) mean a "relay metadata now,
 *     attach media later" pattern would silently drop the media: the
 *     second ingest call returns the existing record without updating
 *     media_url. Lifting that would require server changes too.
 *   • Without two physical devices to exercise the file-relay path,
 *     shipping it untested risks regressing the working text-only path.
 *
 * To enable media relay later:
 *   1. Add server-side support for upgrading an existing FileUpload's
 *      media_url on a follow-up ingest call with the same local_id.
 *   2. Add a header BYTES payload + Payload.fromFile() pair on the sender
 *      side, sanitize media via MediaSanitizer before relaying.
 *   3. Track pendingReceives[endpointId] on the receiver, correlate the
 *      file payload by id, write to filesDir/mesh-relay/<localId>.<ext>,
 *      then insert the LocalStory with the new mediaLocalPath.
 *   4. Manual testing on two devices over Wi-Fi + Bluetooth required.
 */
class MeshRelayManager(private val context: Context) {

    companion object {
        private const val TAG = "MeshRelay"
        private const val SERVICE_ID = "com.melonews.reporter.mesh"
        private val STRATEGY = Strategy.P2P_CLUSTER
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val dao = AppDatabaseFactory.getInstance(context).localStoryDao()
    private val connectionsClient = Nearby.getConnectionsClient(context)
    private val gson = Gson()

    // ── Connection lifecycle ──────────────────────────────────────────────

    private val connectionLifecycleCallback = object : ConnectionLifecycleCallback() {
        override fun onConnectionInitiated(endpointId: String, info: ConnectionInfo) {
            // Auto-accept all connections from other Melo News Reporter instances
            connectionsClient.acceptConnection(endpointId, payloadCallback)
                .addOnFailureListener { Log.w(TAG, "acceptConnection failed: $it") }
        }

        override fun onConnectionResult(endpointId: String, result: ConnectionResolution) {
            if (result.status.statusCode == ConnectionsStatusCodes.STATUS_OK) {
                Log.d(TAG, "Connected to $endpointId — sending pending stories")
                scope.launch { sendPendingStories(endpointId) }
            }
        }

        override fun onDisconnected(endpointId: String) {
            Log.d(TAG, "Disconnected from $endpointId")
        }
    }

    // ── Payload received (we are the relay receiver) ──────────────────────

    private val payloadCallback = object : PayloadCallback() {
        override fun onPayloadReceived(endpointId: String, payload: Payload) {
            if (payload.type != Payload.Type.BYTES) return
            val bytes = payload.asBytes() ?: return
            val json = String(bytes, Charsets.UTF_8)
            scope.launch { receiveStory(json) }
        }

        override fun onPayloadTransferUpdate(endpointId: String, update: PayloadTransferUpdate) {
            // No-op — bytes are small enough to be single-chunk
        }
    }

    // ── Discovery (find advertisers nearby) ───────────────────────────────

    private val endpointDiscoveryCallback = object : EndpointDiscoveryCallback() {
        override fun onEndpointFound(endpointId: String, info: DiscoveredEndpointInfo) {
            Log.d(TAG, "Found endpoint $endpointId — requesting connection")
            connectionsClient.requestConnection(
                android.os.Build.MODEL,
                endpointId,
                connectionLifecycleCallback
            ).addOnFailureListener { Log.w(TAG, "requestConnection failed: $it") }
        }

        override fun onEndpointLost(endpointId: String) {
            Log.d(TAG, "Lost endpoint $endpointId")
        }
    }

    // ── Public API ────────────────────────────────────────────────────────

    fun start() {
        startAdvertising()
        startDiscovery()
    }

    fun stop() {
        connectionsClient.stopAdvertising()
        connectionsClient.stopDiscovery()
        connectionsClient.stopAllEndpoints()
    }

    // ── Private helpers ───────────────────────────────────────────────────

    private fun startAdvertising() {
        val options = AdvertisingOptions.Builder().setStrategy(STRATEGY).build()
        connectionsClient.startAdvertising(
            android.os.Build.MODEL,
            SERVICE_ID,
            connectionLifecycleCallback,
            options
        ).addOnFailureListener { Log.w(TAG, "startAdvertising failed: $it") }
    }

    private fun startDiscovery() {
        val options = DiscoveryOptions.Builder().setStrategy(STRATEGY).build()
        connectionsClient.startDiscovery(
            SERVICE_ID,
            endpointDiscoveryCallback,
            options
        ).addOnFailureListener { Log.w(TAG, "startDiscovery failed: $it") }
    }

    /**
     * Send all text-only PENDING stories to a connected peer that may be online.
     *
     * Stories with media are skipped — relaying the metadata without the
     * media would let the receiver create a server record that the sender
     * can never attach media to later (idempotency keeps the first ingest
     * winning). Those stories stay PENDING and wait for direct sync.
     */
    private suspend fun sendPendingStories(endpointId: String) {
        val pending = dao.getPending()
        if (pending.isEmpty()) return

        for (story in pending) {
            if (story.mediaLocalPath != null) {
                Log.d(TAG, "Skipping mesh relay of ${story.localId}: has media (waits for direct sync)")
                continue
            }

            // Defense in depth: even though text-only stories shouldn't carry
            // file paths, we explicitly null the field on the wire so a
            // future schema change doesn't accidentally leak local paths to
            // a peer device.
            val relayCopy = story.copy(mediaLocalPath = null)
            val json = gson.toJson(relayCopy)
            val payload = Payload.fromBytes(json.toByteArray(Charsets.UTF_8))
            connectionsClient.sendPayload(endpointId, payload)
                .addOnSuccessListener {
                    Log.d(TAG, "Relayed story ${story.localId} to $endpointId")
                    scope.launch {
                        dao.updateStatus(story.localId, SyncStatus.RELAYED, error = null)
                    }
                }
                .addOnFailureListener { Log.w(TAG, "sendPayload failed: $it") }
        }
    }

    /**
     * Receive a story relayed from a peer, insert it into local Room queue,
     * and immediately try to sync to Flask (we may be the online device).
     */
    private suspend fun receiveStory(json: String) {
        try {
            val story = gson.fromJson(json, LocalStory::class.java)
            // Only insert if we don't already have this local_id
            val existing = dao.getByLocalId(story.localId)
            if (existing != null) {
                Log.d(TAG, "Already have relayed story ${story.localId} — skipping")
                return
            }
            // Reset sync status so SyncManager will upload it, and force
            // mediaLocalPath to null: any path in the JSON points to a file
            // on the sender's device that doesn't exist here. Trying to
            // upload it would silently send the story without media.
            val relayed = story.copy(
                syncStatus = SyncStatus.PENDING,
                retryCount = 0,
                errorMessage = null,
                mediaLocalPath = null,
            )
            dao.insert(relayed)
            Log.d(TAG, "Received relayed story ${story.localId} — queued for upload")
            // Attempt immediate upload
            SyncManager(context).drainQueue()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to receive relayed story: $e")
        }
    }
}
