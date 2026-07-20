plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp") version "1.9.23-1.0.19"
}

android {
    namespace = "com.melonews.reporter"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.melonews.reporter"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        // API endpoint. Defaults to the deployed drill server over HTTPS —
        // required, not cosmetic: network_security_config.xml sets
        // cleartextTrafficPermitted=false, so the app cannot talk to a plain
        // HTTP host at this domain at all.
        //
        // Override for local development (e.g. a Tailscale-reachable dev box):
        //   ./gradlew :app:assembleDebug -PmeloApiBaseUrl=http://100.120.77.28:5000/
        // Any such host must also be listed in network_security_config.xml.
        // NOTE: Retrofit requires the trailing slash.
        val meloApiBaseUrl = (project.findProperty("meloApiBaseUrl") as String?)
            ?: "https://drill.melonews.tech/"
        buildConfigField("String", "API_BASE_URL", "\"$meloApiBaseUrl\"")

        // Anonymous submission is DISABLED to match the server, which returns
        // 403 from /api/stories/anonymous-ingest unless ANONYMOUS_INGEST_ENABLED
        // is set (ADR-0007: unauthenticated public ingest is the easiest
        // Sybil/spam vector, and anonymous reports count 0 toward corroboration).
        // Showing the option while the server refuses it means a reporter's
        // submission is silently discarded — the worst failure mode for a tool
        // whose premise is trustworthiness.
        // Re-enable ONLY together with the server flag:
        //   ./gradlew :app:assembleDebug -PmeloAnonymousEnabled=true
        val meloAnonymousEnabled = (project.findProperty("meloAnonymousEnabled") as String?) ?: "false"
        buildConfigField("boolean", "ANONYMOUS_ENABLED", meloAnonymousEnabled)
    }

    buildFeatures {
        viewBinding = true
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    // Kotlin coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")

    // AndroidX core
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("androidx.activity:activity-ktx:1.8.2")
    implementation("androidx.fragment:fragment-ktx:1.6.2")

    // Lifecycle
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.7.0")
    implementation("androidx.lifecycle:lifecycle-livedata-ktx:2.7.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")

    // DataStore (secure JWT storage)
    implementation("androidx.datastore:datastore-preferences:1.0.0")

    // Navigation
    implementation("androidx.navigation:navigation-fragment-ktx:2.7.7")
    implementation("androidx.navigation:navigation-ui-ktx:2.7.7")

    // UI
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")

    // Network
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Map (works offline — important for conflict zones)
    implementation("org.osmdroid:osmdroid-android:6.1.18")

    // Image loading
    implementation("io.coil-kt:coil:2.5.0")

    // EXIF metadata (read orientation before stripping, drives ExifSanitizer)
    implementation("androidx.exifinterface:exifinterface:1.3.7")

    // GPS location
    implementation("com.google.android.gms:play-services-location:21.1.0")

    // Biometric (fingerprint + face unlock)
    implementation("androidx.biometric:biometric:1.1.0")

    // Room (offline local queue)
    val roomVersion = "2.6.1"
    implementation("androidx.room:room-runtime:$roomVersion")
    implementation("androidx.room:room-ktx:$roomVersion")
    ksp("androidx.room:room-compiler:$roomVersion")

    // Nearby Connections (mesh relay between devices)
    implementation("com.google.android.gms:play-services-nearby:19.1.0")

    // Unit tests (JVM). gson is used to load the cross-language signing vectors.
    testImplementation("junit:junit:4.13.2")
    testImplementation("com.google.code.gson:gson:2.10.1")

    // Note: DB at-rest encryption is provided by Android File-Based Encryption (FBE),
    // which is mandatory on all devices since Android 7 (minSdk=26 here).
}
