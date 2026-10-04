package com.analoganchor.nxtpaperguard

import java.text.NumberFormat
import java.util.Locale

/** The controller owns both the current deadline and the next one-session choice. */
data class GuardStatus(
    val phase: String,
    val remaining: Long,
    val sessionStart: Long,
    val deadline: Long,
    val physical: String,
    val errorCode: String?,
    val nextDuration: Long
) {
    val sessionDuration: Long get() = (deadline - sessionStart).coerceAtLeast(0)

    companion object {
        val durations = setOf(300L, 7200L, 14400L, 21600L, 43200L)
        private val phases = setOf(
            "INITIALIZING", "WAIT_SWITCH", "IDLE", "STARTING", "COMMITTED", "EXTENDED",
            "RESTORING", "WAIT_OFF", "STOPPED", "UPDATE_REQUIRED", "ERROR"
        )

        fun parse(output: String): GuardStatus {
            val line = output.lineSequence().lastOrNull { it.substringBefore(':') in phases }
                ?: throw IllegalArgumentException("Missing controller status")
            val parts = line.trim().split(':')
            require(parts.size >= 6)
            val numbers = parts.slice(1..4).map { it.toLongOrNull() ?: -1 }
            require(numbers.all { it >= 0 })
            if (parts[0] in setOf("COMMITTED", "EXTENDED")) require(numbers[2] >= numbers[1])
            require(parts[5] in setOf("UNKNOWN", "OFF", "ON"))
            val next = if (parts.size < 8) 300L else parts[7].toLongOrNull() ?: -1L
            require(next in durations)
            return GuardStatus(
                parts[0], numbers[0], numbers[1], numbers[2], parts[5],
                if (parts[0] == "ERROR") parts.getOrNull(6)?.takeIf { it.isNotBlank() } else null,
                next
            )
        }
    }
}

fun formatCountdown(seconds: Long, locale: Locale): String {
    val remaining = seconds.coerceAtLeast(0)
    val formatter = NumberFormat.getIntegerInstance(locale).apply {
        minimumIntegerDigits = 2
        isGroupingUsed = false
    }
    val units = if (remaining >= 3600) {
        listOf(remaining / 3600, (remaining / 60) % 60, remaining % 60)
    } else {
        listOf(remaining / 60, remaining % 60)
    }
    return units.joinToString(":") { formatter.format(it) }
}
