package com.analoganchor.nxtpaperguard

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GuardExitPolicyTest {
    private val identity = "123:100:boot-one"

    @Test fun lostCancelAcknowledgementRetriesOnlyTheOriginalLiveRequest() {
        assertEquals(GuardExitPolicy.CancelRecovery.RETRY,
            GuardExitPolicy.cancelRecovery("COMMITTED", 500, identity, identity, 500))
        assertEquals(GuardExitPolicy.CancelRecovery.CLEAR,
            GuardExitPolicy.cancelRecovery("COMMITTED", 700, identity, identity, 500))
    }

    @Test fun appDeathAfterShellCancellationCanFinishThePreferenceUpdate() {
        for (phase in listOf("STARTING", "COMMITTED")) {
            assertEquals(GuardExitPolicy.CancelRecovery.CONFIRM,
                GuardExitPolicy.cancelRecovery(phase, 0, identity, identity, 500))
        }
    }

    @Test fun completedRestorationMissingProcessAndNewDaemonCannotResumeTheOldIntent() {
        for (phase in listOf("RESTORING", "STOPPED", "ERROR", "EXTENDED", "IDLE", "UPDATE_REQUIRED")) {
            assertEquals(GuardExitPolicy.CancelRecovery.CLEAR,
                GuardExitPolicy.cancelRecovery(phase, 0, identity, identity, 500))
        }
        for (other in listOf(null, "123:101:boot-one", "123:100:boot-two", "124:100:boot-one")) {
            assertEquals(GuardExitPolicy.CancelRecovery.CLEAR,
                GuardExitPolicy.cancelRecovery("COMMITTED", 0, identity, other, 500))
        }
    }

    @Test fun pendingStartResultAndZeroCountdownCannotConfirmContinuation() {
        for (phase in listOf("STARTING", "COMMITTED")) {
            assertFalse(GuardExitPolicy.continuationConfirmed(phase, 500))
            assertTrue(GuardExitPolicy.continuationConfirmed(phase, 0))
        }
        assertFalse(GuardExitPolicy.continuationConfirmed("RESTORING", 0))
        assertFalse(GuardExitPolicy.continuationConfirmed("STOPPED", 0))
    }

    @Test fun lostStopAcknowledgementCanBeConfirmedFromActualControllerState() {
        assertTrue(GuardExitPolicy.stopAcknowledged("STARTING", 500))
        assertTrue(GuardExitPolicy.stopAcknowledged("COMMITTED", 500))
        assertTrue(GuardExitPolicy.stopAcknowledged("RESTORING", 0))
        assertTrue(GuardExitPolicy.stopAcknowledged("STOPPED", 0))
        assertFalse(GuardExitPolicy.stopAcknowledged("COMMITTED", 0))
        assertFalse(GuardExitPolicy.stopAcknowledged("EXTENDED", 0))
        assertFalse(GuardExitPolicy.stopAcknowledged("ERROR", 500))
    }

    @Test fun lostStopAcknowledgementCannotUseNaturalRestorationAsProofOfStopping() {
        assertTrue(GuardExitPolicy.stopAcknowledged("RESTORING", 0))
        assertFalse(GuardExitPolicy.stopConfirmedFromStatus("RESTORING", 0))
        assertTrue(GuardExitPolicy.stopConfirmedFromStatus("COMMITTED", 500))
        assertTrue(GuardExitPolicy.stopConfirmedFromStatus("STARTING", 500))
        assertTrue(GuardExitPolicy.stopConfirmedFromStatus("STOPPED", 0))
        assertFalse(GuardExitPolicy.stopConfirmedFromStatus("IDLE", 0))
    }
}
