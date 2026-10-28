package com.analoganchor.nxtpaperguard

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class GuardCompatibilityTest {
    @Test fun knownProfileReportIsObservationOnly() {
        val report = GuardCompatibility.parse("VERIFIED:t807d-eea-amd9\nfingerprint=known")
        assertEquals(GuardCompatibility.Verdict.VERIFIED, report.verdict)
        assertEquals("t807d-eea-amd9", report.profileId)
        assertFalse(report.commandSent)
    }

    @Test fun firmwarePrivilegeAndCapabilityFailuresRemainDistinct() {
        for (kind in listOf("UNVERIFIED_BUILD", "PRIVILEGE_UNAVAILABLE", "CAPABILITY_MISSING")) {
            val report = GuardCompatibility.parse("$kind:REQUIRED_CHECK_FAILED")
            assertEquals(kind, report.verdict.name)
            assertEquals("REQUIRED_CHECK_FAILED", report.reason)
            assertFalse(report.commandSent)
        }
    }

    @Test fun malformedReportsCannotAuthorizeCommands() {
        for (value in listOf("", "VERIFIED", "VERIFIED:", "VERIFIED:wrong:extra", "VERIFIED:../profile",
            "READY:t807d", "CAPABILITY_MISSING:", "UNVERIFIED_BUILD:lowercase", "garbage\nVERIFIED:t807d")) {
            val report = GuardCompatibility.parse(value, allowCommandSent = true)
            assertEquals(GuardCompatibility.Verdict.CAPABILITY_MISSING, report.verdict)
            assertFalse(report.commandSent)
        }
    }

    @Test fun commandDispatchIsAcceptedOnlyForExplicitModeTestReply() {
        val reply = "COMMAND_SENT:t807d-eea-amd9"
        assertEquals(GuardCompatibility.Verdict.CAPABILITY_MISSING, GuardCompatibility.parse(reply).verdict)
        val accepted = GuardCompatibility.parse(reply, allowCommandSent = true)
        assertTrue(accepted.commandSent)
        assertEquals("COMMAND_SENT", accepted.reason)
    }

    @Test fun controllerIdentityChangesWithEitherSourceOrProfile() {
        val script = "script\n".toByteArray()
        val profile = "profile\n".toByteArray()
        val original = GuardCompatibility.controllerDigest(script, profile)
        assertEquals(64, original.length)
        assertEquals(original, GuardCompatibility.controllerDigest(script, profile))
        assertNotEquals(original, GuardCompatibility.controllerDigest("different".toByteArray(), profile))
        assertNotEquals(original, GuardCompatibility.controllerDigest(script, "different".toByteArray()))
        assertNotEquals(GuardCompatibility.controllerDigest("ab".toByteArray(), "c".toByteArray()),
            GuardCompatibility.controllerDigest("a".toByteArray(), "bc".toByteArray()))
    }

    @Test fun stdinCommandTreatsProfileAsDataAndRejectsOtherActions() {
        val command = GuardCompatibility.command("check-compatibility", "id=trusted\nnote='; input keyevent 343; '")
        assertEquals("NXTPAPER_PROFILE_DATA='id=trusted\nnote='\\''; input keyevent 343; '\\''' /system/bin/sh -s check-compatibility", command)
        assertThrows(IllegalArgumentException::class.java) { GuardCompatibility.command("start", "id=trusted") }
        assertThrows(IllegalArgumentException::class.java) { GuardCompatibility.command("test-ink", "a\u0000b") }
        assertThrows(IllegalArgumentException::class.java) { GuardCompatibility.command("test-normal", "") }
    }

    @Test fun controllerMismatchDoesNotReplaceFirmwareVerdict() {
        val observed = GuardCompatibility.parse("VERIFIED:t807d-eea-amd9")
        val reported = observed.copy(controllerUpdateRequired = true)
        assertEquals(GuardCompatibility.Verdict.VERIFIED, reported.verdict)
        assertTrue(reported.controllerUpdateRequired)
        assertFalse(reported.commandSent)
    }
}
