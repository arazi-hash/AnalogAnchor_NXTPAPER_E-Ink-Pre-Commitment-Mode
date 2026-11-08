package com.analoganchor.nxtpaperguard

import java.net.URI
import org.junit.Assert.*
import org.junit.Test

class CompatibilityReportTest {
    private val identity = linkedMapOf(
        "model" to "T807D", "device" to "Frida", "android" to "16", "sdk" to "36",
        "fingerprint" to "TCL/T807D_EEA/Frida:16/BP2A.250605.031.A3/AMD9:user/release-keys",
        "build_display" to "v9.0.AMD9", "security_patch" to "2026-10-01"
    )

    private fun report(access: CompatibilityReport.Access = CompatibilityReport.Access.AUTHORIZED) =
        CompatibilityReport("1.0.6-beta.2", 8, identity, access)

    private fun fields(rendered: String): Map<String, String> = rendered.lineSequence()
        .filter { '=' in it }
        .associate { line -> line.substringBefore('=') to line.substringAfter('=') }

    @Test fun unavailableShizukuStillIncludesBasicDeviceIdentityAndUnperformedChecks() {
        val output = fields(report(CompatibilityReport.Access.NOT_RUNNING).render())
        assertEquals("T807D", output["app_model"])
        assertEquals("v9.0.AMD9", output["app_build_display"])
        assertEquals("2026-10-01", output["app_security_patch"])
        assertEquals("APP_PROCESS", output["device_identity_source"])
        assertEquals("UNAVAILABLE", output["shizuku_connection"])
        assertEquals("NOT_CHECKED", output["shizuku_authorization"])
        assertEquals("SHIZUKU_NOT_RUNNING", output["reason"])
        assertEquals("NOT_CHECKED", output["assessment_observation"])
        assertEquals("NOT_CHECKED", output["support"])
        assertEquals("NOT_CHECKED", output["setup"])
        assertEquals("NOT_CHECKED", output["last_local_qualification"])
        assertEquals("NOT_CHECKED", output["last_controller_present"])
    }

    @Test fun connectedShizukuWithDeniedPermissionIsDistinctFromUnavailable() {
        val output = fields(report(CompatibilityReport.Access.PERMISSION_REQUIRED).render())
        assertEquals("CONNECTED", output["shizuku_connection"])
        assertEquals("REQUIRED", output["shizuku_authorization"])
        assertEquals("SHIZUKU_PERMISSION_REQUIRED", output["reason"])
        assertEquals("NOT_CHECKED", output["assessment_observation"])
        assertEquals("NOT_CHECKED", output["setup_observation"])
    }

    @Test fun failedAndInProgressTrialsRetainTheirStageWithoutClaimingQualification() {
        val failed = report().copy(trial = SetupTrialStatus("FAILED", "RESTORATION_FAILED"))
        val failedFields = fields(failed.render())
        assertEquals("FAILED", failedFields["setup"])
        assertEquals("RESTORATION_FAILED", failedFields["setup_reason"])
        assertEquals("INCOMPLETE", failedFields["last_local_qualification"])

        val active = report().copy(trial = SetupTrialStatus("WAIT_OWNER_CONFIRM"))
        val activeFields = fields(active.render())
        assertEquals("WAIT_OWNER_CONFIRM", activeFields["setup"])
        assertEquals("NONE", activeFields["setup_reason"])
        assertEquals("INCOMPLETE", activeFields["last_local_qualification"])
    }

    @Test fun passedAutomaticTestStillNeedsTheRecordedLocalQualification() {
        val automatic = report().copy(trial = SetupTrialStatus("PASSED"))
        assertEquals("INCOMPLETE", fields(automatic.render())["last_local_qualification"])
        val confirmed = automatic.copy(trial = SetupTrialStatus("QUALIFIED"), qualified = true)
        assertEquals("PASSED", fields(confirmed.render())["last_local_qualification"])
        assertEquals("NOT_CHECKED", fields(confirmed.copy(trial = null).render())["last_local_qualification"])
    }

    @Test fun cachedSuccessAfterAccessLossIsHistoricalAndHasSeparateObservationAges() {
        val snapshot = report(CompatibilityReport.Access.NOT_RUNNING).copy(
            assessment = SupportAssessment(SupportAssessment.Level.MAINTAINER_TESTED, "SETUP_REQUIRED"),
            trial = SetupTrialStatus("QUALIFIED"), qualified = true, controllerPresent = true,
            assessmentAgeSeconds = 125, setupAgeSeconds = 3, observationError = "SHIZUKU_NOT_RUNNING"
        )
        val rendered = snapshot.render()
        val output = fields(rendered)
        assertEquals("UNAVAILABLE", output["shizuku_connection"])
        assertEquals("CACHED", output["assessment_observation"])
        assertEquals("125", output["assessment_age_seconds"])
        assertEquals("CACHED", output["setup_observation"])
        assertEquals("3", output["setup_age_seconds"])
        assertEquals("PASSED", output["last_local_qualification"])
        assertEquals("true", output["last_controller_present"])
        assertEquals("SHIZUKU_NOT_RUNNING", output["observation_error"])
        assertTrue(rendered.contains("not current protection"))
        assertFalse(output.containsKey("protection_active"))
        assertEquals("UNKNOWN", fields(snapshot.copy(assessmentAgeSeconds = -1, setupAgeSeconds = null).render())["assessment_age_seconds"])
        assertEquals("UNKNOWN", fields(snapshot.copy(assessmentAgeSeconds = -1, setupAgeSeconds = null).render())["setup_age_seconds"])
    }

    @Test fun bothFactSourcesExcludePrivateAndUnrecognizedFields() {
        val privateFacts = mapOf(
            "serial" to "private-serial", "account" to "private-account", "selected_apps" to "private-app-list",
            "process_token" to "private-token", "raw_dump" to "private-dump", "unrelated_setting" to "private-setting"
        )
        val snapshot = report().copy(
            deviceFacts = identity + privateFacts,
            assessment = SupportAssessment(SupportAssessment.Level.UNSUPPORTED, "INPUT_MAPPING_UNSUPPORTED",
                facts = mapOf("model" to "shell-model", "keylayout" to "/system/usr/keylayout/Generic.kl",
                    "runtime_enter_name" to "KEYCODE_TSWT_ON") + privateFacts),
            trial = SetupTrialStatus("FAILED", "TEST_TIMED_OUT", trialId = "private-trial", bindingDigest = "private-binding")
        )
        val rendered = snapshot.render()
        for (value in privateFacts.values + listOf("private-trial", "private-binding")) assertFalse(rendered.contains(value))
        val output = fields(rendered)
        assertEquals("T807D", output["app_model"])
        assertEquals("shell-model", output["model"])
        assertEquals("/system/usr/keylayout/Generic.kl", output["keylayout"])
        assertEquals("KEYCODE_TSWT_ON", output["runtime_enter_name"])
    }

    @Test fun malformedTextCannotInjectNewLinesOrImpersonateAResult() {
        val snapshot = report().copy(
            appVersion = "beta\nqualified=true",
            deviceFacts = identity + mapOf("model" to "T807D\nserial=hidden", "build_display" to "A".repeat(513),
                "fingerprint" to "TCL\u0000private", "device" to "Frida\u202Ehidden"),
            assessment = SupportAssessment(SupportAssessment.Level.UNSUPPORTED, "SETUP_REQUIRED\nqualified=true",
                facts = mapOf("launcher_version" to "12\r\nserial=private", "runtime_exit_name" to "A".repeat(513))),
            trial = SetupTrialStatus("QUALIFIED\nserial=private", "A".repeat(97)),
            observationError = "FAILED\u0000private"
        )
        val rendered = snapshot.render()
        val output = fields(rendered)
        assertTrue(rendered.startsWith("NXTPAPER_E-Ink-Pre-Commitment-Mode OMITTED_INVALID_VALUE\n"))
        for (key in listOf("app_model", "app_build_display", "app_fingerprint", "app_device", "launcher_version", "runtime_exit_name")) {
            assertEquals(key, "OMITTED_INVALID_VALUE", output[key])
        }
        for (key in listOf("reason", "setup", "setup_reason", "observation_error")) assertEquals(key, "UNKNOWN", output[key])
        assertFalse(rendered.contains("serial="))
        assertFalse(rendered.contains("qualified=true"))
        assertFalse(rendered.contains('\u0000'))
        assertFalse(rendered.contains('\u202E'))
        assertFalse(rendered.contains("A".repeat(513)))
    }

    @Test fun browserDestinationContainsOnlyTheFormChoice() {
        val uri = URI(CompatibilityReport.ISSUE_FORM_URL)
        assertEquals("https", uri.scheme)
        assertEquals("github.com", uri.host)
        assertEquals("/arazi-hash/AnalogAnchor_NXTPAPER_E-Ink-Pre-Commitment-Mode/issues/new", uri.path)
        assertEquals("template=compatibility.yml", uri.rawQuery)
        assertNull(uri.fragment)
        assertFalse(CompatibilityReport.ISSUE_FORM_URL.contains(identity.getValue("model")))
        assertFalse(CompatibilityReport.ISSUE_FORM_URL.contains("body="))
    }

    @Test fun renderingIsDeterministicAndLeavesTheObservedObjectsIntact() {
        val deviceFacts = identity.toMutableMap()
        val assessmentFacts = linkedMapOf("model" to "T807D", "launcher_version" to "100", "enter_key" to "343")
        val assessment = SupportAssessment(SupportAssessment.Level.UNSUPPORTED, "SYMBOL_MAPPING_CONFLICT", facts = assessmentFacts)
        val trial = SetupTrialStatus("FAILED", "TEST_TIMED_OUT", 120, "trial-identity", "binding-digest")
        val originalDevice = deviceFacts.toMap()
        val originalAssessment = assessment.copy(facts = assessmentFacts.toMap())
        val originalTrial = trial.copy()
        val snapshot = report().copy(deviceFacts = deviceFacts, assessment = assessment, trial = trial)
        val rendered = snapshot.render()
        assertEquals(rendered, snapshot.render())
        assertEquals(rendered, snapshot.copy(
            deviceFacts = deviceFacts.entries.reversed().associate { it.toPair() },
            assessment = assessment.copy(facts = assessmentFacts.entries.reversed().associate { it.toPair() })
        ).render())
        assertSame(assessment, snapshot.assessment)
        assertSame(trial, snapshot.trial)
        assertEquals(originalDevice, deviceFacts)
        assertEquals(originalAssessment, assessment)
        assertEquals(originalTrial, trial)
        assertFalse(assessment.eligible)
    }
}
