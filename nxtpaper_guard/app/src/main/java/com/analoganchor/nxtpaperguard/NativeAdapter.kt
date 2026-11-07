package com.analoganchor.nxtpaperguard

import java.security.MessageDigest

/** Reviewed semantics; data can select values but cannot introduce shell code. */
data class NativeAdapter(val values: Map<String, String>) {
    val id: String get() = values.getValue("id")
    val revision: String get() = values.getValue("revision")

    companion object {
        private val expected = mapOf(
            "schema" to "1", "id" to "tcl-slider-v1", "revision" to "1",
            "feature" to "vendor.software.support.tcl_switch", "input_name" to "tswt",
            "symbol_on" to "KEYCODE_TSWT_ON", "symbol_off" to "KEYCODE_TSWT_OFF",
            "linux_on" to "592", "linux_off" to "593", "raw_on" to "KEY_BRIGHTNESS_MIN",
            "raw_off" to "KEY_BRIGHTNESS_MAX", "layout_on" to "TSWT_ON", "layout_off" to "TSWT_OFF",
            "tswt_key" to "TSWT_state", "ink_key" to "nxtpaper_ink_style_state",
            "book_key" to "nxtpaper_book_style_state", "applying_key" to "nxtpaper_is_applying_theme",
            "animation_key" to "nxtpaper_animation_state", "preset_key" to "tct_nxtpaper_mode_select",
            "preset" to "3", "immediate_key" to "tct_nxtpaper_switch_imm", "immediate" to "1",
            "evidence" to "FINDINGS.md"
        )

        fun parse(text: String): NativeAdapter {
            val values = parseData(text)
            require(values == expected) { "Unimplemented native adapter" }
            return NativeAdapter(values.toMap())
        }
    }
}

internal fun parseData(text: String): Map<String, String> {
    require(!text.startsWith('\uFEFF') && '\r' !in text && '\u0000' !in text)
    val result = linkedMapOf<String, String>()
    for (line in text.lineSequence()) {
        if (line.isEmpty() || line.startsWith('#')) continue
        val parts = line.split('=', limit = 2)
        require(parts.size == 2 && parts[0].matches(Regex("[a-z][a-z0-9_]*")) &&
            parts[1].matches(Regex("[A-Za-z0-9_./:+-]+")) && parts[0] !in result)
        result[parts[0]] = parts[1]
    }
    return result
}

internal fun dataText(values: Map<String, String>): String =
    values.toSortedMap().entries.joinToString("\n", postfix = "\n") { "${it.key}=${it.value}" }

internal fun sha256(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256")
    .digest(bytes).joinToString("") { "%02x".format(it.toInt() and 0xff) }

data class RuntimeKeyPair(val enter: Int, val exit: Int, val enterName: String, val exitName: String) {
    val resolved: Boolean get() = enter in 1..32767 && exit in 1..32767 && enter != exit &&
        enterName == "KEYCODE_TSWT_ON" && exitName == "KEYCODE_TSWT_OFF"
}

data class NativeBinding(val values: Map<String, String>) {
    val text: String get() = dataText(values)
    val digest: String get() = sha256(text.toByteArray(Charsets.UTF_8))
    val controllerDigest: String get() = values.getValue("controller_sha256")
    val profileId: String get() = values.getValue("id")

    companion object {
        val legacyKeys = ("schema id qualification model device android sdk fingerprint input_name linux_on linux_off " +
            "raw_on raw_off keylayout layout_on layout_off enter_key exit_key tswt_key ink_key book_key applying_key " +
            "animation_key preset_key preset immediate_key immediate evidence").split(' ').toSet()
        val keys = legacyKeys + setOf("adapter", "adapter_revision", "keylayout_sha256", "systemui_version",
            "launcher_version", "manager_version", "controller_sha256")

        fun parse(text: String): NativeBinding {
            val values = parseData(text)
            require(values.keys == keys && values["schema"] == "2")
            require(values["qualification"] in setOf("maintainer-tested", "experimental"))
            require(values["adapter"] == "tcl-slider-v1" && values["adapter_revision"] == "1")
            for (key in listOf("keylayout_sha256", "controller_sha256")) require(DeviceQualification.validDigest(values.getValue(key)))
            for (key in listOf("systemui_version", "launcher_version", "manager_version", "android", "sdk",
                "linux_on", "linux_off", "enter_key", "exit_key")) require(values.getValue(key).matches(Regex("[1-9][0-9]*")))
            require(values["enter_key"] != values["exit_key"])
            require(values.getValue("enter_key").toInt() <= 32767 && values.getValue("exit_key").toInt() <= 32767)
            val adapter = NativeAdapter.parse(dataText(mapOf(
                "schema" to "1", "id" to "tcl-slider-v1", "revision" to "1",
                "feature" to "vendor.software.support.tcl_switch", "symbol_on" to "KEYCODE_TSWT_ON",
                "symbol_off" to "KEYCODE_TSWT_OFF"
            ) + values.filterKeys { it in setOf("input_name", "linux_on", "linux_off", "raw_on", "raw_off",
                "layout_on", "layout_off", "tswt_key", "ink_key", "book_key", "applying_key", "animation_key",
                "preset_key", "preset", "immediate_key", "immediate", "evidence") }))
            require(adapter.id == values["adapter"])
            require(values.getValue("id").matches(Regex("[a-z0-9]+(?:-[a-z0-9]+)*")))
            require(".." !in values.getValue("keylayout") && values.getValue("keylayout").matches(
                Regex("/(?:system|system_ext|vendor|odm|product)/usr/keylayout/[A-Za-z0-9_.+-]+\\.kl")))
            return NativeBinding(values.toMap())
        }
    }
}

data class SupportAssessment(
    val level: Level,
    val reason: String,
    val binding: NativeBinding? = null,
    val facts: Map<String, String> = emptyMap()
) {
    enum class Level { MAINTAINER_TESTED, EXPERIMENTAL_ELIGIBLE, UNSUPPORTED }
    val eligible: Boolean get() = binding != null && level in setOf(Level.MAINTAINER_TESTED, Level.EXPERIMENTAL_ELIGIBLE)

    /** Only explicitly selected, validated facts can enter a user's report. */
    fun report(appVersion: String, trialPhase: String, qualified: Boolean): String {
        val allowedFacts = setOf("model", "device", "android", "sdk", "fingerprint", "adapter", "adapter_revision",
            "keylayout", "keylayout_sha256", "enter_key", "exit_key", "slider_feature", "raw_input_readable",
            "push_button_protocol", "runtime_enter_name", "runtime_exit_name", "systemui_version", "launcher_version", "manager_version")
        return buildString {
            appendLine("E-Ink Pre-commitment Mode $appVersion")
            appendLine("support=${level.name}")
            appendLine("reason=$reason")
            appendLine("setup=$trialPhase")
            appendLine("local_qualification=$qualified")
            for ((key, value) in facts.toSortedMap()) if (key in allowedFacts) appendLine("$key=$value")
            appendLine("No serials, process tokens, selected-app lists or unrelated settings are included.")
            append("Local setup success is experimental evidence for this phone/build, not universal model support.")
        }
    }
}

data class SetupTrialStatus(val phase: String, val reason: String = "", val elapsed: Long = 0,
                            val trialId: String = "", val bindingDigest: String = "") {
    val active: Boolean get() = phase !in setOf("STOPPED", "PASSED", "QUALIFIED", "ABORTED", "FAILED", "UNKNOWN")
    val passed: Boolean get() = phase in setOf("PASSED", "QUALIFIED")

    companion object {
        private val phases = setOf("STOPPED", "INITIALIZING", "WAIT_NORMAL", "WAIT_PHYSICAL_INK", "WAIT_PHYSICAL_NORMAL", "WAIT_OWNER_CONFIRM",
            "WAIT_EXIT_INK", "EXIT_TEST", "WAIT_EXIT_NORMAL", "ENTER_TEST", "RESTORE_TEST", "PASSED",
            "QUALIFIED", "ABORTING", "ABORTED", "FAILED")

        fun parse(output: String): SetupTrialStatus {
            val parts = output.trim().split(':')
            require(parts.size == 5 && parts[0] in phases)
            require(parts[1].isEmpty() || parts[1].matches(Regex("[A-Z][A-Z0-9_]*")))
            val elapsed = parts[2].toLongOrNull() ?: -1
            require(elapsed >= 0 && elapsed <= 86_400)
            require(parts[3].isEmpty() || parts[3].matches(Regex("[A-Za-z0-9_-]+")))
            require(parts[4].isEmpty() || DeviceQualification.validDigest(parts[4]))
            return SetupTrialStatus(parts[0], parts[1], elapsed, parts[3], parts[4])
        }
    }
}
