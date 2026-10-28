package com.analoganchor.nxtpaperguard

import java.security.MessageDigest

/** Compatibility is an observation, never a cached authorization to send a key. */
object GuardCompatibility {
    enum class Verdict { VERIFIED, UNVERIFIED_BUILD, CAPABILITY_MISSING, PRIVILEGE_UNAVAILABLE }

    data class Report(
        val verdict: Verdict,
        val reason: String,
        val profileId: String? = null,
        val commandSent: Boolean = false,
        val controllerUpdateRequired: Boolean = false
    )

    private val profileId = Regex("[a-z0-9]+(?:-[a-z0-9]+)*")
    private val reasonCode = Regex("[A-Z][A-Z0-9_]*")

    fun parse(output: String, allowCommandSent: Boolean = false): Report {
        val first = output.lineSequence().firstOrNull()?.trim().orEmpty()
        val parts = first.split(':', limit = 2)
        if (parts.size != 2) return invalidReport()
        val (kind, detail) = parts
        if (kind == "VERIFIED" || (kind == "COMMAND_SENT" && allowCommandSent)) {
            if (!profileId.matches(detail)) return invalidReport()
            return Report(Verdict.VERIFIED, kind, detail, commandSent = kind == "COMMAND_SENT")
        }
        val verdict = runCatching { Verdict.valueOf(kind) }.getOrNull()
        if (verdict == null || verdict == Verdict.VERIFIED || !reasonCode.matches(detail)) return invalidReport()
        return Report(verdict, detail)
    }

    fun command(action: String, profile: String): String {
        require(action in setOf("check-compatibility", "test-ink", "test-normal"))
        require(profile.isNotBlank() && '\u0000' !in profile && profile.length <= 16_384)
        // The shell parses this data strictly. Quoting still treats every byte as data.
        val quoted = "'" + profile.replace("'", "'\\''") + "'"
        return "NXTPAPER_PROFILE_DATA=$quoted /system/bin/sh -s $action"
    }

    fun controllerDigest(controller: ByteArray, profile: ByteArray): String {
        val hash = MessageDigest.getInstance("SHA-256")
        hash.update(controller)
        hash.update(0.toByte())
        hash.update(profile)
        return hash.digest().joinToString("") { "%02x".format(it.toInt() and 0xff) }
    }

    private fun invalidReport() = Report(Verdict.CAPABILITY_MISSING, "INVALID_COMPATIBILITY_REPORT")
}
