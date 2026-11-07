package com.analoganchor.nxtpaperguard

/** Observations are injected so the same eligibility rules can be tested off-device. */
object SupportAssessmentEngine {
    private const val AMD9_FINGERPRINT = "TCL/T807D_EEA/Frida:16/BP2A.250605.031.A3/AMD9:user/release-keys"
    data class Observations(
        val identity: Map<String, String>, val manufacturer: String,
        val sliderFeature: Boolean, val telephony: Boolean, val nativeSettings: String,
        val capabilities: String, val inputDump: String, val layoutPath: String,
        val layoutText: String, val layoutDigest: String, val versions: Map<String, String>,
        val keys: RuntimeKeyPair, val readableRawInput: Boolean, val pushButtonProperty: String
    )

    fun assess(adapter: NativeAdapter, registry: List<Map<String, String>>, observations: Observations,
               controllerDigest: String): SupportAssessment {
        val identity = observations.identity
        val facts = identity.filterKeys { it in setOf("model", "device", "android", "sdk", "fingerprint") }.toMutableMap()
        facts["slider_feature"] = observations.sliderFeature.toString()
        facts["raw_input_readable"] = observations.readableRawInput.toString()
        facts["push_button_protocol"] = (observations.pushButtonProperty !in setOf("", "0", "false")).toString()
        facts["runtime_enter_name"] = observations.keys.enterName.takeIf { it.matches(Regex("KEYCODE_[A-Z0-9_]+")) } ?: "UNRESOLVED"
        facts["runtime_exit_name"] = observations.keys.exitName.takeIf { it.matches(Regex("KEYCODE_[A-Z0-9_]+")) } ?: "UNRESOLVED"
        fun unsupported(reason: String) = SupportAssessment(SupportAssessment.Level.UNSUPPORTED, reason, facts = facts)
        if (!DeviceQualification.validDigest(controllerDigest)) return unsupported("CONTROLLER_UNAVAILABLE")
        if (registry.isEmpty() || registry.map { it["id"] }.toSet().size != registry.size ||
            registry.map { it["fingerprint"] }.toSet().size != registry.size) return unsupported("REGISTRY_AMBIGUOUS")
        if (observations.manufacturer.lowercase() != "tcl" || !observations.sliderFeature || !observations.telephony) {
            return unsupported("SLIDER_PROTOCOL_UNAVAILABLE")
        }
        if (!observations.readableRawInput) return unsupported("PHYSICAL_INPUT_UNAVAILABLE")
        if (observations.pushButtonProperty !in setOf("", "0", "false")) return unsupported("PUSH_BUTTON_PROTOCOL_UNSUPPORTED")
        if (identity.keys != setOf("model", "device", "android", "sdk", "fingerprint") ||
            identity.values.any { !it.matches(Regex("[A-Za-z0-9_./:+-]+")) } ||
            identity.getValue("android").toIntOrNull() == null || identity.getValue("sdk").toIntOrNull() == null) {
            return unsupported("IDENTITY_UNAVAILABLE")
        }
        val known = registry.filter { profile -> identity.all { (name, value) -> profile[name] == value } }
        if (known.size > 1) return unsupported("REGISTRY_AMBIGUOUS")
        val reference = known.singleOrNull()
        if (reference != null && observations.keys.resolved &&
            (observations.keys.enter.toString() != reference["enter_key"] || observations.keys.exit.toString() != reference["exit_key"])) {
            return unsupported("SYMBOL_MAPPING_CONFLICT")
        }
        if (reference != null && ((observations.keys.enter > 0 && observations.keys.enter.toString() != reference["enter_key"]) ||
            (observations.keys.exit > 0 && observations.keys.exit.toString() != reference["exit_key"]))) {
            return unsupported("SYMBOL_MAPPING_CONFLICT")
        }
        val reviewedAmd9 = reference != null && reference["id"] == "t807d-eea-amd9" && reference["enter_key"] == "343" &&
            reference["exit_key"] == "344" && identity == mapOf("model" to "T807D", "device" to "Frida",
                "android" to "16", "sdk" to "36", "fingerprint" to AMD9_FINGERPRINT)
        val unavailablePair = observations.keys.enter == 0 && observations.keys.exit == 0 &&
            ((observations.keys.enterName.isEmpty() && observations.keys.exitName.isEmpty()) ||
                (observations.keys.enterName == "KEYCODE_UNKNOWN" && observations.keys.exitName == "KEYCODE_UNKNOWN"))
        // Observed on the reviewed AMD9 handset: forward TSWT lookup returns 343/344,
        // while reverse lookup exposes these exact fingerprint-key aliases. Never extend this exception to other builds.
        val reviewedAliasPair = observations.keys.enter == 343 && observations.keys.exit == 344 &&
            observations.keys.enterName == "KEYCODE_FP_LIFT_UP" && observations.keys.exitName == "KEYCODE_FP_LONGPRESS"
        val keys = when {
            observations.keys.resolved -> observations.keys
            reviewedAmd9 && (unavailablePair || reviewedAliasPair) -> RuntimeKeyPair(343, 344, "KEYCODE_TSWT_ON", "KEYCODE_TSWT_OFF")
            else -> return unsupported("SYMBOL_MAPPING_UNAVAILABLE")
        }
        val device = runCatching { discoverInput(observations.capabilities) }.getOrNull()
            ?: return unsupported("PHYSICAL_INPUT_UNAVAILABLE")
        val activeLayout = runCatching { activeLayout(observations.inputDump, device) }.getOrNull()
            ?: return unsupported("ACTIVE_LAYOUT_UNAVAILABLE")
        if (activeLayout != observations.layoutPath || !validLayoutPath(activeLayout) ||
            !DeviceQualification.validDigest(observations.layoutDigest)) return unsupported("ACTIVE_LAYOUT_UNAVAILABLE")
        if (!validLayout(observations.layoutText)) return unsupported("INPUT_MAPPING_UNSUPPORTED")
        if (!validNative(observations.nativeSettings, adapter)) return unsupported("NATIVE_SETTINGS_UNAVAILABLE")
        val versionNames = setOf("systemui_version", "launcher_version", "manager_version")
        if (observations.versions.keys != versionNames || observations.versions.values.any { !it.matches(Regex("[1-9][0-9]*")) }) {
            return unsupported("NATIVE_COMPONENT_UNAVAILABLE")
        }
        facts.putAll(observations.versions)
        facts["adapter"] = adapter.id
        facts["adapter_revision"] = adapter.revision
        facts["keylayout_sha256"] = observations.layoutDigest
        facts["keylayout"] = activeLayout
        facts["enter_key"] = keys.enter.toString()
        facts["exit_key"] = keys.exit.toString()
        val data = adapter.values.filterKeys { it in NativeBinding.legacyKeys }.toMutableMap()
        data.putAll(identity)
        data.putAll(observations.versions)
        data.putAll(mapOf("schema" to "2", "id" to (reference?.get("id") ?: "tcl-slider-experimental"),
            "qualification" to if (reference != null) "maintainer-tested" else "experimental",
            "adapter" to adapter.id, "adapter_revision" to adapter.revision,
            "keylayout" to activeLayout, "keylayout_sha256" to observations.layoutDigest,
            "enter_key" to keys.enter.toString(), "exit_key" to keys.exit.toString(),
            "controller_sha256" to controllerDigest))
        val binding = runCatching { NativeBinding.parse(dataText(data)) }.getOrNull()
            ?: return unsupported("BINDING_INVALID")
        return SupportAssessment(if (reference != null) SupportAssessment.Level.MAINTAINER_TESTED
            else SupportAssessment.Level.EXPERIMENTAL_ELIGIBLE, "SETUP_REQUIRED", binding, facts)
    }

    fun parseRegistry(text: String): Map<String, String> {
        val profile = parseData(text)
        require(profile.keys == NativeBinding.legacyKeys && profile["schema"] == "1" && profile["qualification"] == "verified")
        require(profile.getValue("id").matches(Regex("[a-z0-9]+(?:-[a-z0-9]+)*")))
        return profile
    }

    fun discoverInput(capabilities: String): String {
        val headers = Regex("(?m)^add device [0-9]+: (/dev/input/event[0-9]+)\\s*$").findAll(capabilities).toList()
        val candidates = headers.mapIndexedNotNull { index, header ->
            val block = capabilities.substring(header.range.last + 1, headers.getOrNull(index + 1)?.range?.first ?: capabilities.length)
            if (Regex("(?m)^\\s*name:\\s*\"tswt\"\\s*$").containsMatchIn(block)) header.groupValues[1] to block else null
        }
        require(candidates.size == 1)
        require(listOf("KEY_BRIGHTNESS_MIN", "KEY_BRIGHTNESS_MAX").all { Regex("\\b$it\\b").containsMatchIn(candidates[0].second) })
        return candidates[0].first
    }

    fun activeLayout(inputDump: String, node: String): String {
        val headers = Regex("(?m)^([ \\t]+)[0-9]+: ([^\\r\\n]+)$").findAll(inputDump).toList()
        val matches = headers.mapIndexedNotNull { index, header ->
            if (header.groupValues[2].trim() != "tswt") return@mapIndexedNotNull null
            val block = inputDump.substring(header.range.last + 1, headers.getOrNull(index + 1)?.range?.first ?: inputDump.length)
            val paths = Regex("(?m)^\\s*Path:\\s*(/dev/input/event[0-9]+)\\s*$").findAll(block).toList()
            val layouts = Regex("(?m)^\\s*KeyLayoutFile:\\s*(\\S+)\\s*$").findAll(block).toList()
            require(paths.size == 1 && paths[0].groupValues[1] == node && layouts.size == 1)
            layouts[0].groupValues[1]
        }
        require(matches.size == 1 && validLayoutPath(matches.single()))
        return matches.single()
    }

    private fun validLayoutPath(path: String): Boolean = ".." !in path &&
        path.matches(Regex("/(?:system|system_ext|vendor|odm|product)/usr/keylayout/[A-Za-z0-9_.+-]+\\.kl"))

    private fun validLayout(text: String): Boolean {
        val mappings = linkedMapOf<String, String>()
        for (line in text.lineSequence()) {
            val fields = line.substringBefore('#').trim().split(Regex("\\s+"))
            if (fields.size >= 3 && fields[0] == "key" && fields[2] in setOf("TSWT_ON", "TSWT_OFF") && fields[1] !in setOf("592", "593")) return false
            if (fields.size >= 3 && fields[0] == "key" && fields[1] in setOf("592", "593")) {
                if (fields.size != 3) return false
                if (fields[1] in mappings) return false
                mappings[fields[1]] = fields[2]
            }
        }
        return mappings == mapOf("592" to "TSWT_ON", "593" to "TSWT_OFF")
    }

    private fun validNative(text: String, adapter: NativeAdapter): Boolean {
        val names = listOf("tswt", "ink", "book", "applying", "animation", "preset", "immediate")
        val keys = names.associateWith { adapter.values.getValue(it + "_key") }
        val values = linkedMapOf<String, String>()
        for (line in text.lineSequence()) {
            val parts = line.split('=', limit = 2)
            if (parts[0] in keys.values) {
                if (parts.size != 2 || parts[0] in values) return false
                values[parts[0]] = parts[1]
            }
        }
        if (values.keys != keys.values.toSet()) return false
        val allowed = mapOf("tswt" to setOf("-1", "0", "1"), "ink" to setOf("0", "1", "2"),
            "book" to setOf("0", "1"), "applying" to setOf("0", "1"), "animation" to setOf("0", "1"),
            "preset" to setOf(adapter.values.getValue("preset")), "immediate" to setOf(adapter.values.getValue("immediate")))
        return names.all { values[keys.getValue(it)] in allowed.getValue(it) }
    }
}
