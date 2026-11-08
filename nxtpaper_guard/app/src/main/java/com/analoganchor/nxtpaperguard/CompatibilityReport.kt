package com.analoganchor.nxtpaperguard

/** A display-only snapshot. Constructing or sharing it never performs a phone command. */
data class CompatibilityReport(
    val appVersion: String,
    val appVersionCode: Int,
    val deviceFacts: Map<String, String>,
    val access: Access,
    val assessment: SupportAssessment? = null,
    val trial: SetupTrialStatus? = null,
    val qualified: Boolean = false,
    val controllerPresent: Boolean? = null,
    val assessmentAgeSeconds: Long? = null,
    val setupAgeSeconds: Long? = null,
    val observationError: String? = null
) {
    enum class Access { NOT_RUNNING, PERMISSION_REQUIRED, AUTHORIZED }

    fun render(): String = buildString {
        appendLine("NXTPAPER_E-Ink-Pre-Commitment-Mode ${safeValue(appVersion, 64)}")
        appendLine("report_schema=2")
        appendLine("app_version_code=$appVersionCode")
        appendLine("shizuku_connection=${if (access == Access.NOT_RUNNING) "UNAVAILABLE" else "CONNECTED"}")
        appendLine("shizuku_authorization=${when (access) {
            Access.NOT_RUNNING -> "NOT_CHECKED"
            Access.PERMISSION_REQUIRED -> "REQUIRED"
            Access.AUTHORIZED -> "GRANTED"
        }}")
        appendLine("device_identity_source=APP_PROCESS")
        for ((key, value) in deviceFacts.toSortedMap()) {
            if (key in deviceFields) appendLine("app_$key=${safeValue(value)}")
        }
        appendLine("assessment_observation=${if (assessment == null) "NOT_CHECKED" else "CACHED"}")
        appendLine("assessment_age_seconds=${age(assessmentAgeSeconds)}")
        appendLine("support=${assessment?.level?.name ?: "NOT_CHECKED"}")
        appendLine("reason=${assessment?.reason?.let(::safeCode) ?: when (access) {
            Access.NOT_RUNNING -> "SHIZUKU_NOT_RUNNING"
            Access.PERMISSION_REQUIRED -> "SHIZUKU_PERMISSION_REQUIRED"
            Access.AUTHORIZED -> "NOT_CHECKED"
        }}")
        for ((key, value) in assessment?.facts.orEmpty().toSortedMap()) {
            if (key in assessmentFields) appendLine("$key=${safeValue(value)}")
        }
        appendLine("setup_observation=${if (trial == null) "NOT_CHECKED" else "CACHED"}")
        appendLine("setup_age_seconds=${age(setupAgeSeconds)}")
        appendLine("setup=${trial?.phase?.let(::safeCode) ?: "NOT_CHECKED"}")
        appendLine("setup_reason=${trial?.reason?.takeIf { it.isNotEmpty() }?.let(::safeCode) ?: "NONE"}")
        appendLine("last_local_qualification=${if (trial == null) "NOT_CHECKED" else if (qualified) "PASSED" else "INCOMPLETE"}")
        appendLine("last_controller_present=${controllerPresent?.toString() ?: "NOT_CHECKED"}")
        appendLine("observation_error=${observationError?.let(::safeCode) ?: "NONE"}")
        appendLine("Cached observations describe the last checks, not current protection. Unavailable access prevents fresh checks.")
        appendLine("App identity comes from Android in this app's profile. Assessment facts come from the last shell check.")
        appendLine("No serials, accounts, process tokens, selected-app lists or raw dumps are included.")
        append("Local setup success is evidence for this phone/build only. Review before sharing publicly.")
    }

    companion object {
        const val ISSUE_FORM_URL = "https://github.com/arazi-hash/AnalogAnchor_NXTPAPER_E-Ink-Pre-Commitment-Mode/issues/new?template=compatibility.yml"
        private val deviceFields = setOf("model", "device", "android", "sdk", "fingerprint", "build_display", "security_patch")
        private val assessmentFields = setOf("model", "device", "android", "sdk", "fingerprint", "adapter", "adapter_revision",
            "keylayout", "keylayout_sha256", "enter_key", "exit_key", "slider_feature", "raw_input_readable",
            "push_button_protocol", "runtime_enter_name", "runtime_exit_name", "systemui_version", "launcher_version", "manager_version")

        // Reject rather than truncate untrusted values, so a partial value cannot look like a valid build.
        private fun safeValue(value: String, limit: Int = 512): String =
            if (value.length in 1..limit && value.matches(Regex("[A-Za-z0-9_./:+ ()-]+"))) value else "OMITTED_INVALID_VALUE"

        private fun safeCode(value: String): String =
            if (value.matches(Regex("[A-Z][A-Z0-9_]{0,95}"))) value else "UNKNOWN"

        private fun age(seconds: Long?): String = seconds?.takeIf { it >= 0 }?.toString() ?: "UNKNOWN"
    }
}
