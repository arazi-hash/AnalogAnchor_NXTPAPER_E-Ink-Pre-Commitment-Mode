package com.analoganchor.nxtpaperguard

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import java.text.NumberFormat
import java.util.Locale

class GuardStatusTest {
    @Test fun consumedLongChoiceKeepsActiveDurationIndependentFromNextDefault() {
        val status = GuardStatus.parse("COMMITTED:7190:100:7300:110:OFF::300")
        assertEquals(7200L, status.sessionDuration)
        assertEquals(300L, status.nextDuration)
        assertEquals(7190L, status.remaining)
    }

    @Test fun stoppedStatusRetainsAuthoritativePendingChoice() {
        val status = GuardStatus.parse("STOPPED:0:0:0:100:UNKNOWN::43200")
        assertEquals(43200L, status.nextDuration)
        assertEquals(0L, status.sessionDuration)
    }

    @Test fun legacyStatusDefaultsNextDurationOnlyWhenFieldIsAbsent() {
        assertEquals(300L, GuardStatus.parse("IDLE:0:0:0:10:OFF:").nextDuration)
        assertThrows(IllegalArgumentException::class.java) {
            GuardStatus.parse("IDLE:0:0:0:10:OFF::oops")
        }
    }

    @Test fun durationRejectionCodeAndNextChoiceRemainReadable() {
        val status = GuardStatus.parse("ERROR:0:0:0:100:UNKNOWN:DURATION_BUSY:300")
        assertEquals("DURATION_BUSY", status.errorCode)
        assertEquals(300L, status.nextDuration)
    }

    @Test fun malformedControllerStatusAndUnsupportedDurationAreRejected() {
        for (output in listOf(
            "COMMITTED:300:10:310:20:FAKE::300",
            "COMMITTED:-1:10:310:20:ON::300",
            "COMMITTED:10:310:10:20:ON::300",
            "EXTENDED:0:310:10:320:ON::300",
            "IDLE:0:0:0:10:OFF::",
            "IDLE:0:0:0:10:OFF::900",
            "not a controller status"
        )) assertThrows(IllegalArgumentException::class.java) { GuardStatus.parse(output) }
    }

    @Test fun countdownChangesBetweenHoursAndMinutesWithoutLosingTime() {
        assertEquals("12:00:00", formatCountdown(43200, Locale.ENGLISH))
        assertEquals("01:00:00", formatCountdown(3600, Locale.ENGLISH))
        assertEquals("59:59", formatCountdown(3599, Locale.ENGLISH))
        assertEquals("05:00", formatCountdown(300, Locale.ENGLISH))
        assertEquals("00:00", formatCountdown(-1, Locale.ENGLISH))
    }

    @Test fun arabicCountdownUsesLocaleDigits() {
        val locale = Locale.forLanguageTag("ar")
        val number = NumberFormat.getIntegerInstance(locale).apply {
            minimumIntegerDigits = 2
            isGroupingUsed = false
        }
        assertEquals(listOf(2, 4, 6).joinToString(":") { number.format(it) }, formatCountdown(7446, locale))
    }
}
