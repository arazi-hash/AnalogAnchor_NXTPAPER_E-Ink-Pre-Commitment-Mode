package com.analoganchor.nxtpaperguard

import org.junit.Assert.*
import org.junit.Test

class SetupGuidePolicyTest {
    private val key = SetupGuidePolicy.acknowledgementKey("AMD9", "a".repeat(64))

    @Test fun ignoringRemindsOnNextVisitButNotEveryPoll() {
        val policy = SetupGuidePolicy()
        assertTrue(policy.shouldShow(true, false, key, null))
        policy.shown()
        repeat(5) { assertFalse(policy.shouldShow(true, false, key, null)) }
        policy.beginVisit()
        assertTrue(policy.shouldShow(true, false, key, null))
    }

    @Test fun acknowledgementSuppressesOnlyTheCurrentBinding() {
        val policy = SetupGuidePolicy()
        assertFalse(policy.shouldShow(true, false, key, key))
        policy.beginVisit()
        val changed = SetupGuidePolicy.acknowledgementKey("AMD9", "b".repeat(64))
        assertTrue(policy.shouldShow(true, false, changed, key))
        assertTrue(policy.shouldShow(true, false, SetupGuidePolicy.acknowledgementKey("AMD10", null), key))
    }

    @Test fun activeWorkBlocksTheGuideWithoutConsumingItsVisit() {
        val policy = SetupGuidePolicy()
        assertFalse(policy.shouldShow(true, true, key, null))
        assertTrue(policy.shouldShow(true, false, key, null))
        assertFalse(policy.shouldShow(false, false, key, null))
    }

    @Test fun recreationKeepsAnAlreadyShownGuideFromAppearingAgain() {
        val original = SetupGuidePolicy()
        original.shown()
        val recreated = SetupGuidePolicy(original.handledThisVisit)
        assertFalse(recreated.shouldShow(true, false, key, null))
        recreated.beginVisit()
        assertTrue(recreated.shouldShow(true, false, key, null))
    }

    @Test fun configurationRestoresTheVisitButBackgroundAndProcessDeathBeginAnother() {
        assertTrue(SetupGuidePolicy.restoreHandled(true, "process-a:0", "process-a:0"))
        assertFalse(SetupGuidePolicy.restoreHandled(true, "process-a:0", "process-a:1"))
        assertFalse(SetupGuidePolicy.restoreHandled(true, "process-a:0", "process-b:0"))
        assertFalse(SetupGuidePolicy.restoreHandled(false, "process-a:0", "process-a:0"))
    }

    @Test fun unavailableBindingUsesBuildIdentityUntilFreshChecksExist() {
        assertEquals("build:AMD9", SetupGuidePolicy.acknowledgementKey("AMD9", null))
        assertEquals("build:AMD9", SetupGuidePolicy.acknowledgementKey("AMD9", "malformed"))
        assertNotEquals(SetupGuidePolicy.acknowledgementKey("AMD9", null), key)
    }
}
