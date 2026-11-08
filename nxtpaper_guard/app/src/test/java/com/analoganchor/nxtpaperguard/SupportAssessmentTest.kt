package com.analoganchor.nxtpaperguard

import org.junit.Assert.*
import org.junit.Test

class SupportAssessmentTest {
    private val adapterText = """
        schema=1
        id=tcl-slider-v1
        revision=1
        feature=vendor.software.support.tcl_switch
        input_name=tswt
        symbol_on=KEYCODE_TSWT_ON
        symbol_off=KEYCODE_TSWT_OFF
        linux_on=592
        linux_off=593
        raw_on=KEY_BRIGHTNESS_MIN
        raw_off=KEY_BRIGHTNESS_MAX
        layout_on=TSWT_ON
        layout_off=TSWT_OFF
        tswt_key=TSWT_state
        ink_key=nxtpaper_ink_style_state
        book_key=nxtpaper_book_style_state
        applying_key=nxtpaper_is_applying_theme
        animation_key=nxtpaper_animation_state
        preset_key=tct_nxtpaper_mode_select
        preset=3
        immediate_key=tct_nxtpaper_switch_imm
        immediate=1
        evidence=FINDINGS.md
    """.trimIndent() + "\n"
    private val adapter = NativeAdapter.parse(adapterText)
    private val fingerprint = "TCL/T807D_EEA/Frida:16/BP2A.250605.031.A3/AMD9:user/release-keys"
    private val layout = "/system/usr/keylayout/Generic.kl"
    private val identity = mapOf("model" to "T807D", "device" to "Frida", "android" to "16", "sdk" to "36", "fingerprint" to fingerprint)
    private val registry = listOf(adapter.values.filterKeys { it in NativeBinding.legacyKeys } + identity + mapOf(
        "schema" to "1", "id" to "t807d-eea-amd9", "qualification" to "verified", "keylayout" to layout,
        "enter_key" to "343", "exit_key" to "344"))
    private fun observations() = SupportAssessmentEngine.Observations(identity, "TCL", true, true,
        "TSWT_state=0\nnxtpaper_ink_style_state=0\nnxtpaper_book_style_state=0\nnxtpaper_is_applying_theme=0\nnxtpaper_animation_state=0\ntct_nxtpaper_mode_select=3\ntct_nxtpaper_switch_imm=1\n",
        "add device 1: /dev/input/event2\n  name: \"tswt\"\n  events: KEY_BRIGHTNESS_MIN KEY_BRIGHTNESS_MAX\n",
        "    2: tswt\n      Path: /dev/input/event2\n      KeyLayoutFile: $layout\n",
        layout, "key 592 TSWT_ON\nkey 593 TSWT_OFF\n", "a".repeat(64),
        mapOf("systemui_version" to "36", "launcher_version" to "101", "manager_version" to "102"),
        RuntimeKeyPair(343, 344, "KEYCODE_TSWT_ON", "KEYCODE_TSWT_OFF"), true, "")
    private fun assess(observations: SupportAssessmentEngine.Observations = observations()) =
        SupportAssessmentEngine.assess(adapter, registry, observations, "b".repeat(64))

    @Test fun reviewedBuildStillRequiresLocalSetup() {
        val result = assess()
        assertEquals(SupportAssessment.Level.MAINTAINER_TESTED, result.level)
        assertEquals("SETUP_REQUIRED", result.reason)
        assertNotNull(result.binding)
    }

    @Test fun unknownBuildUsesResolvedSymbolsWithoutPinnedNumbers() {
        val unknown = observations().copy(identity = identity + ("fingerprint" to fingerprint.replace("AMD9", "AMD10")),
            keys = RuntimeKeyPair(501, 502, "KEYCODE_TSWT_ON", "KEYCODE_TSWT_OFF"))
        val result = assess(unknown)
        assertEquals(SupportAssessment.Level.EXPERIMENTAL_ELIGIBLE, result.level)
        assertEquals("501", result.binding!!.values["enter_key"])
        assertFalse(assess(unknown.copy(keys = RuntimeKeyPair(0, 0, "KEYCODE_UNKNOWN", "KEYCODE_UNKNOWN"))).eligible)
    }

    @Test fun reviewedBuildRejectsConflictingResolvedSymbols() {
        assertFalse(assess(observations().copy(keys = RuntimeKeyPair(501, 502, "KEYCODE_TSWT_ON", "KEYCODE_TSWT_OFF"))).eligible)
        assertFalse(assess(observations().copy(keys = RuntimeKeyPair(501, 0, "KEYCODE_TSWT_ON", "KEYCODE_UNKNOWN"))).eligible)
        assertTrue(assess(observations().copy(keys = RuntimeKeyPair(0, 0, "", ""))).eligible)
        assertTrue(assess(observations().copy(keys = RuntimeKeyPair(0, 0, "KEYCODE_UNKNOWN", "KEYCODE_UNKNOWN"))).eligible)
        assertFalse(assess(observations().copy(keys = RuntimeKeyPair(0, 0, "INVALID", "KEYCODE_UNKNOWN"))).eligible)
        assertFalse(assess(observations().copy(keys = RuntimeKeyPair(343, 344, "343", "344"))).eligible)
    }

    @Test fun observedAmd9FingerprintAliasesAreAcceptedOnlyOnExactReviewedBuild() {
        val actualPhoneKeys = RuntimeKeyPair(343, 344, "KEYCODE_FP_LIFT_UP", "KEYCODE_FP_LONGPRESS")
        val observed = observations().copy(keys = actualPhoneKeys)
        val reviewed = assess(observed)
        assertTrue(reviewed.eligible)
        assertEquals("343", reviewed.binding!!.values["enter_key"])
        assertEquals("344", reviewed.binding!!.values["exit_key"])
        assertEquals("KEYCODE_FP_LIFT_UP", reviewed.facts["runtime_enter_name"])
        assertFalse(assess(observed.copy(identity = identity + ("fingerprint" to fingerprint.replace("AMD9", "AMD10")))).eligible)
        assertFalse(assess(observed.copy(keys = actualPhoneKeys.copy(exitName = "KEYCODE_OTHER"))).eligible)
        assertFalse(assess(observed.copy(keys = actualPhoneKeys.copy(enterName = "KEYCODE_FP_LONGPRESS", exitName = "KEYCODE_FP_LIFT_UP"))).eligible)
    }

    @Test fun unreadableAmbiguousOrDifferentControlsFailClosed() {
        assertFalse(assess(observations().copy(sliderFeature = false)).eligible)
        assertFalse(assess(observations().copy(telephony = false)).eligible)
        assertFalse(assess(observations().copy(readableRawInput = false)).eligible)
        assertFalse(assess(observations().copy(pushButtonProperty = "1")).eligible)
        assertFalse(assess(observations().copy(pushButtonProperty = "true")).eligible)
        assertTrue(assess(observations().copy(pushButtonProperty = "0")).eligible)
        assertFalse(assess(observations().copy(capabilities = "")).eligible)
        assertFalse(assess(observations().copy(inputDump = observations().inputDump + observations().inputDump)).eligible)
        assertFalse(assess(observations().copy(layoutText = observations().layoutText + "key 700 TSWT_ON\n")).eligible)
        assertFalse(assess(observations().copy(layoutText = observations().layoutText + "key 592 TSWT_ON\n")).eligible)
        assertFalse(assess(observations().copy(layoutText = "key 592 TSWT_ON WAKE\nkey 593 TSWT_OFF\n")).eligible)
        assertFalse(assess(observations().copy(nativeSettings = observations().nativeSettings.replace("mode_select=3", "mode_select=2"))).eligible)
        assertFalse(assess(observations().copy(versions = emptyMap())).eligible)
    }

    @Test fun qualificationTracksRelevantChangesButNotEventNodeRenumbering() {
        val first = assess().binding!!
        val saved = DeviceQualification(first.digest, first.controllerDigest, true)
        assertTrue(saved.matches(first.digest, first.controllerDigest))
        val changed = assess(observations().copy(versions = observations().versions + ("launcher_version" to "103"))).binding!!
        assertFalse(saved.matches(changed.digest, changed.controllerDigest))
        val nodeChanged = assess(observations().copy(capabilities = observations().capabilities.replace("event2", "event8"),
            inputDump = observations().inputDump.replace("event2", "event8"))).binding!!
        assertEquals(first.digest, nodeChanged.digest)
    }

    @Test fun interruptedAndFailedTrialsCannotCompleteSetup() {
        assertFalse(DeviceQualification.canComplete(false, true, true, true))
        assertFalse(DeviceQualification.canComplete(true, false, true, true))
        assertFalse(DeviceQualification.canComplete(true, true, false, true))
        assertFalse(DeviceQualification.canComplete(true, true, true, false))
        assertTrue(DeviceQualification.canComplete(true, true, true, true))
        assertFalse(SetupTrialStatus.parse("FAILED:RESTORE_TIMEOUT:45:trial_1:${"a".repeat(64)}").passed)
        assertTrue(SetupTrialStatus.parse("WAIT_OWNER_CONFIRM::10:trial_1:${"a".repeat(64)}").active)
    }

    @Test fun reportContainsOnlyExplicitPublicFacts() {
        val result = assess().copy(facts = assess().facts + mapOf("serial" to "secret-serial", "selected_apps" to "private.apps", "process_token" to "private-token"))
        val report = CompatibilityReport("1.0.6-beta.2", 8, emptyMap(), CompatibilityReport.Access.AUTHORIZED,
            assessment = result, trial = SetupTrialStatus("FAILED", "RESTORE_TIMEOUT")).render()
        assertFalse(report.contains("secret-serial"))
        assertFalse(report.contains("private.apps"))
        assertFalse(report.contains("private-token"))
        assertTrue(report.contains("launcher_version=101"))
    }
}
