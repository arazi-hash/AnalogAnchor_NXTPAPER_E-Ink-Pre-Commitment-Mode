import org.gradle.api.DefaultTask
import org.gradle.api.file.DirectoryProperty
import org.gradle.api.file.RegularFileProperty
import org.gradle.api.tasks.InputFile
import org.gradle.api.tasks.OutputDirectory
import org.gradle.api.tasks.TaskAction

plugins {
    id("com.android.application")
}

android {
    namespace = "com.analoganchor.nxtpaperguard"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.analoganchor.nxtpaperguard"
        minSdk = 26
        targetSdk = 36
        versionCode = 6
        versionName = "1.0.5"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
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
    @get:OutputDirectory abstract val outputDirectory: DirectoryProperty
    @TaskAction fun generate() {
        val directory = outputDirectory.get().asFile
        directory.mkdirs()
        controller.get().asFile.copyTo(directory.resolve("nxtpaper_guard.sh"), overwrite = true)
        firmwareProfile.get().asFile.copyTo(directory.resolve("nxtpaper_firmware.properties"), overwrite = true)
    }
}
val packageGuardController = tasks.register<GuardControllerAssets>("packageGuardController") {
    controller.set(rootProject.layout.projectDirectory.file("../nxtpaper_guard.sh"))
    firmwareProfile.set(rootProject.layout.projectDirectory.file("../compatibility/profiles/t807d-eea-amd9.properties"))
    outputDirectory.set(layout.buildDirectory.dir("generated/guardAssets"))
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
