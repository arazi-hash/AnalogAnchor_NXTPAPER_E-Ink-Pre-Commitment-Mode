package com.analoganchor.nxtpaperguard

import com.analoganchor.nxtpaperguard.GuardRuntime.SetupAction
import org.junit.Assert.*
import org.junit.Test

class SetupCommandQueueTest {
    @Test fun consentConfirmedWhileStatusRunsStillStartsTheTrial() {
        val queue = SetupCommandQueue()
        assertEquals(SetupAction.STATUS, queue.request(SetupAction.STATUS))
        assertFalse(queue.ownerWorkPending)
        assertNull(queue.request(SetupAction.START))
        assertTrue(queue.ownerWorkPending)
        repeat(5) { assertNull(queue.request(SetupAction.STATUS)) }
        assertEquals(SetupAction.START, queue.finished())
        assertNull(queue.finished())
        assertFalse(queue.ownerWorkPending)
    }

    @Test fun nativeAndNormalConfirmationsSurvivePassiveChecks() {
        for (ownerAction in listOf(SetupAction.CONFIRM_NATIVE, SetupAction.QUALIFY, SetupAction.RECOVER)) {
            val queue = SetupCommandQueue()
            assertEquals(SetupAction.CHECK, queue.request(SetupAction.CHECK))
            assertNull(queue.request(ownerAction))
            assertEquals(ownerAction, queue.finished())
            assertNull(queue.finished())
        }
    }

    @Test fun cancelTakesPriorityAndInvalidatesQueuedStartOrQualification() {
        for (queuedAction in listOf(SetupAction.START, SetupAction.QUALIFY)) {
            val queue = SetupCommandQueue()
            queue.request(SetupAction.STATUS)
            queue.request(queuedAction)
            queue.request(SetupAction.ABORT)
            assertTrue(queue.cancelling)
            queue.request(SetupAction.START) // A stale consent dialog cannot restart a cancelled test.
            assertEquals(SetupAction.ABORT, queue.finished())
            assertTrue(queue.cancelling)
            assertNull(queue.finished())
            assertFalse(queue.cancelling)
        }
    }

    @Test fun repeatedPollsCoalesceButResumeCheckIsRetained() {
        val queue = SetupCommandQueue()
        queue.request(SetupAction.STATUS)
        repeat(10) { queue.request(SetupAction.CHECK) }
        assertEquals(SetupAction.CHECK, queue.finished())
        assertNull(queue.finished())
    }
}
