package com.analoganchor.nxtpaperguard

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

class SetupGuidanceTest {
    @Test fun missingAccessAndDeniedPermissionGiveDifferentNextSteps() {
        assertEquals(R.string.setup_access_unavailable, SetupGuidance.reasonResource("SHIZUKU_NOT_RUNNING"))
        assertEquals(R.string.setup_access_permission, SetupGuidance.reasonResource("PERMISSION_REQUIRED"))
        assertNotEquals(SetupGuidance.reasonResource("SHIZUKU_UNAVAILABLE"),
            SetupGuidance.reasonResource("SHIZUKU_PERMISSION_REQUIRED"))
    }

    @Test fun failedRestorationAndInterruptedTestHaveRecoveryGuidance() {
        assertEquals(R.string.setup_restore_unconfirmed, SetupGuidance.reasonResource("RESTORATION_FAILED"))
        assertEquals(R.string.setup_restore_unconfirmed, SetupGuidance.reasonResource("FINAL_NORMAL_NOT_CONFIRMED"))
        assertEquals(R.string.setup_trial_interrupted, SetupGuidance.reasonResource("TRIAL_INTERRUPTED"))
        assertEquals(R.string.setup_trial_timeout, SetupGuidance.reasonResource("TEST_TIMED_OUT"))
    }

    @Test fun unrecognizedControlsAndExistingControllerNeedDifferentActions() {
        assertEquals(R.string.setup_mapping_unrecognized, SetupGuidance.reasonResource("SYMBOL_MAPPING_CONFLICT"))
        assertEquals(R.string.setup_push_button, SetupGuidance.reasonResource("PUSH_BUTTON_PROTOCOL_UNSUPPORTED"))
        assertEquals(R.string.setup_controller_attention, SetupGuidance.reasonResource("TRIAL_LOCK_UNRECOGNIZED"))
        assertEquals(R.string.setup_controller_attention, SetupGuidance.reasonResource("CONTROLLER_NOT_STOPPED"))
        assertEquals(R.string.error_preset, SetupGuidance.reasonResource("NATIVE_PRESET_MISMATCH"))
    }

    @Test fun unknownAndUnperformedChecksNeverUseSuccessGuidance() {
        assertEquals(R.string.setup_not_checked, SetupGuidance.reasonResource("NOT_CHECKED"))
        assertEquals(R.string.setup_required, SetupGuidance.reasonResource("SETUP_REQUIRED"))
        assertEquals(R.string.setup_check_unavailable, SetupGuidance.reasonResource("FUTURE_REASON"))
        assertEquals(R.string.setup_check_unavailable, SetupGuidance.reasonResource(""))
        assertEquals(R.string.setup_check_unavailable, SetupGuidance.reasonResource("QUALIFIED\nserial=secret"))
    }
}
