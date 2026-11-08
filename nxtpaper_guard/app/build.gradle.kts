import org.gradle.api.DefaultTask
import org.gradle.api.file.DirectoryProperty
import org.gradle.api.file.RegularFileProperty
import org.gradle.api.tasks.InputFile
import org.gradle.api.tasks.InputDirectory
import org.gradle.api.tasks.OutputDirectory
import org.gradle.api.tasks.TaskAction
import java.util.Properties

plugins {
    id("com.android.application")
}

// Private credentials are outside the repository on each PC. Debug checks still
// work without them; a public release must never silently become unsigned.
val releaseSigningFile = file(providers.environmentVariable("NXTPAPER_SIGNING_PROPERTIES")
    .getOrElse("${System.getProperty("user.home")}/.android/analoganchor-nxtpaper-release/signing.properties"))
val releaseSigning = Properties().apply {
    if (releaseSigningFile.isFile) releaseSigningFile.inputStream().use { load(it) }
}

android {
    namespace = "com.analoganchor.nxtpaperguard"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.analoganchor.nxtpaperguard"
        minSdk = 26
        targetSdk = 36
        versionCode = 8
        versionName = "1.0.6-beta.2"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        if (releaseSigningFile.isFile) create("publicRelease") {
            storeFile = file(requireNotNull(releaseSigning.getProperty("storeFile")))
            storePassword = requireNotNull(releaseSigning.getProperty("storePassword"))
            keyAlias = requireNotNull(releaseSigning.getProperty("keyAlias"))
            keyPassword = requireNotNull(releaseSigning.getProperty("keyPassword"))
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            isDebuggable = false
            if (releaseSigningFile.isFile) signingConfig = signingConfigs.getByName("publicRelease")
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
        debug {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        buildConfig = true
    }
}

// The APK carries the same controller reviewed and tested at the repository root.
abstract class GuardControllerAssets : DefaultTask() {
    @get:InputFile abstract val controller: RegularFileProperty
    @get:InputFile abstract val firmwareProfile: RegularFileProperty
    @get:InputFile abstract val setupController: RegularFileProperty
    @get:InputDirectory abstract val profileRegistry: DirectoryProperty
    @get:InputDirectory abstract val adapterRegistry: DirectoryProperty
    @get:OutputDirectory abstract val outputDirectory: DirectoryProperty
    @TaskAction fun generate() {
        val directory = outputDirectory.get().asFile
        // Do not leave a removed registry entry in an incremental release APK.
        val expected = project.layout.buildDirectory.dir("generated/guardAssets").get().asFile
        check(directory.canonicalFile == expected.canonicalFile)
        directory.deleteRecursively()
        directory.mkdirs()
        controller.get().asFile.copyTo(directory.resolve("nxtpaper_guard.sh"), overwrite = true)
        firmwareProfile.get().asFile.copyTo(directory.resolve("nxtpaper_firmware.properties"), overwrite = true)
        setupController.get().asFile.copyTo(directory.resolve("nxtpaper_setup.sh"), overwrite = true)
        profileRegistry.get().asFile.copyRecursively(directory.resolve("compatibility/profiles"), overwrite = true)
        adapterRegistry.get().asFile.copyRecursively(directory.resolve("compatibility/adapters"), overwrite = true)
    }
}
val packageGuardController = tasks.register<GuardControllerAssets>("packageGuardController") {
    controller.set(rootProject.layout.projectDirectory.file("../nxtpaper_guard.sh"))
    firmwareProfile.set(rootProject.layout.projectDirectory.file("../compatibility/profiles/t807d-eea-amd9.properties"))
    setupController.set(rootProject.layout.projectDirectory.file("../nxtpaper_setup.sh"))
    profileRegistry.set(rootProject.layout.projectDirectory.dir("../compatibility/profiles"))
    adapterRegistry.set(rootProject.layout.projectDirectory.dir("../compatibility/adapters"))
    outputDirectory.set(layout.buildDirectory.dir("generated/guardAssets"))
}

tasks.matching { it.name == "preReleaseBuild" }.configureEach {
    doFirst { check(releaseSigningFile.isFile) {
        "Public release signing is unavailable. Configure the private NXTPAPER_SIGNING_PROPERTIES file; never commit it."
    } }
}
androidComponents.onVariants { variant ->
    variant.sources.assets?.addGeneratedSourceDirectory(
        packageGuardController, GuardControllerAssets::outputDirectory
    )
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("dev.rikka.shizuku:api:13.1.5")
    implementation("dev.rikka.shizuku:provider:13.1.5")
    testImplementation("junit:junit:4.13.2")
}
