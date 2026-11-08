package com.analoganchor.nxtpaperguard

import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import android.view.KeyEvent
import rikka.shizuku.Shizuku
import rikka.shizuku.ShizukuRemoteProcess
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/** One serialized command path for the UI and Shizuku reconnect listener. */
object GuardRuntime {
    enum class Action { STATUS, START, STOP, CANCEL_STOP, SET_DURATION, TEST_INK, TEST_NORMAL }
    data class Result(
        val phase: String,
        val remaining: Long = 0,
        val error: String? = null,
        val physical: String = "UNKNOWN",
        val errorCode: String? = null,
        val sessionStart: Long = 0,
        val deadline: Long = 0,
        val nextDuration: Long = 300,
        val nativeInkState: Int? = null,
        val exitDeadline: Long = 0,
        val exitRemaining: Long = 0
    ) {
        val sessionDuration: Long get() = (deadline - sessionStart).coerceAtLeast(0)
        val exitPending: Boolean get() = exitDeadline > 0
    }

    private const val SCRIPT = "/data/local/tmp/nxtpaper_guard.sh"
    private const val PROFILE = "/data/local/tmp/nxtpaper_guard.profile"
    private const val VERSION = "/data/local/tmp/nxtpaper_guard.version"
    private const val PID = "/data/local/tmp/nxtpaper_guard.pid"
    private const val STATE_FILE = "/data/local/tmp/nxtpaper_guard.state"
    private const val LOCK_DIR = "/data/local/tmp/nxtpaper_guard.lock"
    private val executor = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private var asset: ByteArray? = null
    private var profileAsset: ByteArray? = null
    private var controllerId: String? = null
    private var lastLanguage: String? = null
    private val stopGeneration = AtomicInteger()
    private const val CANCEL_IDENTITY = "cancel_exit_identity"
    private const val CANCEL_DEADLINE = "cancel_exit_deadline"
    private class GuardFailure(val stringId: Int) : IllegalStateException()
    private fun requireGuard(condition: Boolean, stringId: Int) {
        if (!condition) throw GuardFailure(stringId)
    }

    fun desired(context: Context): Boolean = preferences(context).getBoolean("enabled", false)
    fun setDesired(context: Context, enabled: Boolean) {
        if (!enabled) stopGeneration.incrementAndGet()
        preferences(context).edit().putBoolean("enabled", enabled).apply()
        if (!enabled) BootReminder.cancel(context)
    }
    private fun preferences(context: Context) = context.getSharedPreferences("guard", Context.MODE_PRIVATE)

    fun isAuthorized(): Boolean = try {
        Shizuku.pingBinder() && Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED
    } catch (_: Exception) { false }

    fun runAsync(context: Context, action: Action, duration: Long? = null, callback: (Result) -> Unit) {
        val app = context.applicationContext
        // Invalidate already queued START / duration work at the user's tap,
        // before this command reaches the serialized worker.
        val generation = if (action == Action.STOP) stopGeneration.incrementAndGet() else stopGeneration.get()
        executor.execute {
            val rawResult = try {
                if (action == Action.STOP) persistStopIntent(app)
                requireGuard(isAuthorized(), R.string.error_shizuku_not_ready)
                loadController(app)
                val language = if (context.resources.configuration.locales[0].language == "ar") "ar" else "en"
                if (lastLanguage != language) {
                    shell("printf '%s' '$language' > /data/local/tmp/nxtpaper_guard.language")
                    lastLanguage = language
                }
                when (action) {
                    Action.STATUS -> reconcileCancellation(app, status())
                    Action.START -> {
                        // Recheck the preference on this serialized queue: a queued reconnect must
                        // never undo a later explicit Stop from the user.
                        if (generation == stopGeneration.get() && desired(app)) start(app) else status()
                    }
                    Action.STOP -> requestStop(app)
                    Action.CANCEL_STOP -> cancelStop(app)
                    Action.SET_DURATION -> {
                        if (generation != stopGeneration.get()) status() else {
                            requireGuard(duration != null && duration in GuardStatus.durations, R.string.error_duration_invalid)
                            val before = status()
                            requireGuard(before.phase != "UPDATE_REQUIRED", R.string.guard_update_required)
                            if (before.phase == "STOPPED") {
                                requireQualified(app)
                                deployController()
                            }
                            val configured = parse(shell("/system/bin/sh $SCRIPT set-duration $duration"))
                            if (configured.phase == "ERROR" && configured.errorCode?.startsWith("DURATION_") == true) {
                                durationFeedback(context, context.getString(errorResource(configured.errorCode)))
                            } else configured
                        }
                    }
                    Action.TEST_INK, Action.TEST_NORMAL -> {
                        requireGuard(!desired(app) && status().phase == "STOPPED", R.string.error_tests_guard_active)
                        requireQualified(app)
                        val tested = compatibility(if (action == Action.TEST_INK) "test-ink" else "test-normal")
                        requireGuard(tested.commandSent, compatibilityError(tested))
                        status()
                    }
                }
            } catch (e: GuardFailure) {
                if (action in setOf(Action.SET_DURATION, Action.STOP, Action.CANCEL_STOP)) operationFeedback(context, context.getString(e.stringId))
                else Result("ERROR", error = context.getString(e.stringId))
            } catch (e: Exception) {
                Log.e("GuardRuntime", "Guard operation failed: $action", e)
                if (action in setOf(Action.SET_DURATION, Action.STOP, Action.CANCEL_STOP)) operationFeedback(context, context.getString(when (action) {
                    Action.SET_DURATION -> R.string.error_duration_change
                    Action.CANCEL_STOP -> R.string.error_stop_cancel
                    else -> R.string.error_stop_request
                }))
                else Result("ERROR", error = context.getString(R.string.error_guard_contact))
            }
            // An Activity recreated with stale UI may have requested Start while
            // a pending exit already exists. The daemon remains authoritative.
            val authoritativeResult = try {
                if (rawResult.exitPending) persistExitDisabled(app)
                rawResult
            } catch (_: GuardFailure) {
                rawResult.copy(error = context.getString(R.string.error_guard_preferences))
            }
            val localizedResult = if (authoritativeResult.phase == "ERROR" && authoritativeResult.error == null)
                authoritativeResult.copy(error = context.getString(errorResource(authoritativeResult.errorCode))) else authoritativeResult
            // Use the controller's Shizuku settings context. A cloned app's
            // ContentResolver can read an unrelated work-profile value.
            // This display-only snapshot cannot turn a healthy guard into ERROR.
            val nativeInkState = if (isAuthorized()) runCatching {
                parseNativeInkState(shell("settings get secure nxtpaper_ink_style_state", timeoutSeconds = 3))
            }.getOrNull() else null
            val result = localizedResult.copy(nativeInkState = nativeInkState)
            main.post {
                if (action == Action.START && result.error == null && result.phase !in setOf("STOPPED", "UPDATE_REQUIRED", "ERROR")) {
                    BootReminder.cancel(app)
                }
                callback(result)
            }
        }
    }

    /** Independent read-only path: no STATUS reconciliation, preferences, language, or deployment. */
    fun diagnoseAsync(context: Context, callback: (GuardCompatibility.Report, SupportAssessment?, Long?) -> Unit) {
        val app = context.applicationContext
        executor.execute {
            val report = if (!isAuthorized()) {
                GuardCompatibility.Report(GuardCompatibility.Verdict.PRIVILEGE_UNAVAILABLE, "SHIZUKU_UNAVAILABLE")
            } else try {
                loadController(app)
                val assessed = assess(app)
                val observed = GuardCompatibility.Report(
                    if (assessed.eligible) GuardCompatibility.Verdict.VERIFIED else GuardCompatibility.Verdict.CAPABILITY_MISSING,
                    assessed.reason, assessed.binding?.profileId)
                val mismatch = shell("""
                    ${livePidCheck()}
                    if [ "${'$'}live" = 1 ] &&
                        { [ "${'$'}live_known" != 1 ] || [ "${'$'}(cat $VERSION 2>/dev/null)" != '$controllerId' ]; }; then
                        printf 'UPDATE_REQUIRED'
                    fi
                """.trimIndent(), timeoutSeconds = 5) == "UPDATE_REQUIRED"
                observed.copy(controllerUpdateRequired = mismatch)
            } catch (_: Exception) {
                GuardCompatibility.Report(GuardCompatibility.Verdict.CAPABILITY_MISSING, "PROBE_UNAVAILABLE")
            }
            val assessment = latestAssessment
            val observedAt = latestAssessmentObservedAt
            main.post { callback(report, assessment, observedAt) }
        }
    }

    private fun compatibility(action: String = "check-compatibility"): GuardCompatibility.Report {
        val profile = requireNotNull(profileAsset).toString(Charsets.UTF_8)
        val output = shell(GuardCompatibility.command(action, profile), requireNotNull(asset), timeoutSeconds = 20)
        return GuardCompatibility.parse(output, allowCommandSent = action != "check-compatibility")
    }

    private fun compatibilityError(report: GuardCompatibility.Report): Int = when {
        report.verdict == GuardCompatibility.Verdict.PRIVILEGE_UNAVAILABLE -> R.string.error_privilege
        report.verdict == GuardCompatibility.Verdict.UNVERIFIED_BUILD -> R.string.error_firmware
        report.reason == "NATIVE_PRESET_MISMATCH" -> R.string.error_preset
        report.reason in setOf("LIVE_CONTROLLER_PRESENT", "CONTROLLER_NOT_STOPPED") -> R.string.error_tests_guard_active
        else -> R.string.error_compatibility
    }

    private fun operationFeedback(context: Context, message: String): Result {
        // Transaction failures must never replace a healthy daemon's phase.
        val actual = runCatching { if (isAuthorized()) status() else null }.getOrNull()
        return when {
            actual == null -> Result("ERROR", error = message)
            actual.phase == "ERROR" -> actual.copy(error = context.getString(errorResource(actual.errorCode)))
            else -> actual.copy(error = message)
        }
    }

    private fun durationFeedback(context: Context, message: String): Result = operationFeedback(context, message)

    // KTX edit returns Unit; these writes must inspect commit's success before
    // a controller command or acknowledgement can change the saved intent.
    @SuppressLint("UseKtx")
    private fun persistExitDisabled(context: Context) {
        if (desired(context)) {
            stopGeneration.incrementAndGet()
            requireGuard(preferences(context).edit().putBoolean("enabled", false).commit(), R.string.error_guard_preferences)
        }
        BootReminder.cancel(context)
    }

    @SuppressLint("UseKtx")
    private fun persistStopIntent(context: Context) {
        // This preference controls future automatic restart, not live enforcement.
        // Save before sending; an app death after the shell acknowledges cannot
        // accidentally restart the guard after its delayed stop completes.
        requireGuard(preferences(context).edit().putBoolean("enabled", false)
            .remove(CANCEL_IDENTITY).remove(CANCEL_DEADLINE).commit(), R.string.error_guard_preferences)
        BootReminder.cancel(context)
    }

    @SuppressLint("UseKtx")
    private fun clearCancellation(context: Context, enabled: Boolean) {
        requireGuard(preferences(context).edit().putBoolean("enabled", enabled)
            .remove(CANCEL_IDENTITY).remove(CANCEL_DEADLINE).commit(), R.string.error_guard_preferences)
    }

    private fun liveControllerIdentity(): String? {
        val identity = shell("""
            ${livePidCheck()}
            if [ "${'$'}live" = 1 ] && [ "${'$'}live_known" = 1 ]; then printf '%s' "${'$'}record"; fi
        """.trimIndent()).trim()
        return identity.takeIf { it.matches(Regex("[0-9]+:[0-9]+:[a-zA-Z0-9-]+")) }
    }

    private fun reconcileCancellation(context: Context, current: Result): Result {
        val saved = preferences(context)
        val identity = saved.getString(CANCEL_IDENTITY, null) ?: return current
        val savedDeadline = saved.getLong(CANCEL_DEADLINE, 0)
        return when (GuardExitPolicy.cancelRecovery(current.phase, current.exitDeadline, identity,
            liveControllerIdentity(), savedDeadline)) {
            GuardExitPolicy.CancelRecovery.CLEAR -> {
                clearCancellation(context, enabled = false)
                current
            }
            GuardExitPolicy.CancelRecovery.CONFIRM -> {
                clearCancellation(context, enabled = true)
                current
            }
            GuardExitPolicy.CancelRecovery.RETRY -> finishCancellation(context, identity)
        }
    }

    private fun loadController(context: Context) {
        if (asset != null && profileAsset != null) return
        val bytes = context.assets.open("nxtpaper_guard.sh").use { it.readBytes() }
        val profile = context.assets.open("nxtpaper_firmware.properties").use { it.readBytes() }
        asset = bytes
        profileAsset = profile
        controllerId = "${BuildConfig.VERSION_NAME}:${sha256(bytes)}"
    }

    enum class SetupAction { CHECK, STATUS, START, CONFIRM_NATIVE, ABORT, QUALIFY, RECOVER }
    data class SetupSnapshot(val assessment: SupportAssessment? = null,
        val trial: SetupTrialStatus = SetupTrialStatus("STOPPED"), val qualified: Boolean = false,
        val controllerPresent: Boolean = false, val error: String? = null,
        val errorReason: String? = null, val observedAt: Long? = null, val assessmentObservedAt: Long? = null)
    private const val SETUP_SCRIPT = "/data/local/tmp/nxtpaper_setup.sh"
    private var latestAssessment: SupportAssessment? = null
    private var latestAssessmentObservedAt: Long? = null

    /** Shares the controller queue; all trial progress itself belongs to the independent shell process. */
    fun setupAsync(context: Context, action: SetupAction, callback: (SetupSnapshot) -> Unit) {
        val app = context.applicationContext
        executor.execute {
            val result = try {
                requireGuard(isAuthorized(), R.string.error_shizuku_not_ready)
                loadController(app)
                if (action == SetupAction.START) requireGuard(preferences(app).edit()
                    .remove("qualification_binding").remove("qualification_controller").commit(), R.string.error_guard_preferences)
                var assessment = if (action in setOf(SetupAction.ABORT, SetupAction.RECOVER)) latestAssessment ?: SupportAssessment(SupportAssessment.Level.UNSUPPORTED, "NOT_CHECKED")
                    else if (action == SetupAction.STATUS && latestAssessment != null) latestAssessment!!
                    else assess(app).also { latestAssessment = it }
                var occupied = controllerPresent()
                when (action) {
                    SetupAction.RECOVER -> {
                        // Execute only this APK's implementation. The installed canonical script may belong to an unknown version.
                        var recovered = runCatching { parse(shell("/system/bin/sh -s reset-stale", requireNotNull(asset))) }.getOrNull()
                        if (recovered?.phase != "STOPPED" && knownSetupScript(app) && trialStatus(app).phase == "FAILED") {
                            val trialReset = runCatching {
                                SetupTrialStatus.parse(shell("/system/bin/sh $SETUP_SCRIPT reset-stale"))
                            }.getOrNull()
                            if (trialReset?.phase == "STOPPED") recovered = runCatching {
                                parse(shell("/system/bin/sh -s reset-stale", requireNotNull(asset)))
                            }.getOrNull()
                        }
                        requireGuard(recovered?.phase == "STOPPED", R.string.setup_recovery_refused)
                        occupied = controllerPresent()
                        requireGuard(!occupied, R.string.setup_recovery_refused)
                        assessment = assess(app).also { latestAssessment = it }
                    }
                    SetupAction.START -> {
                        requireGuard(assessment.eligible, R.string.setup_unsupported)
                        val previous = trialStatus(app)
                        requireGuard(!previous.active && previous.phase != "UNKNOWN", R.string.setup_busy)
                        if (previous.phase == "FAILED" && knownSetupScript(app)) {
                            val reset = SetupTrialStatus.parse(shell("/system/bin/sh $SETUP_SCRIPT reset-stale"))
                            requireGuard(reset.phase == "STOPPED", R.string.setup_busy)
                            occupied = controllerPresent()
                        }
                        requireGuard(!occupied && !desired(app), R.string.setup_busy)
                        val binding = requireNotNull(assessment.binding)
                        profileAsset = binding.text.toByteArray(Charsets.UTF_8)
                        deployFiles(mapOf(PROFILE to requireNotNull(profileAsset), SCRIPT to requireNotNull(asset),
                            SETUP_SCRIPT to app.assets.open("nxtpaper_setup.sh").use { it.readBytes() }))
                        shell("printf '%s' '$controllerId' > $VERSION")
                        shell("nohup /system/bin/sh $SETUP_SCRIPT start > /data/local/tmp/nxtpaper_setup.start.log 2>&1 < /dev/null &")
                        Thread.sleep(600)
                    }
                    SetupAction.CONFIRM_NATIVE -> {
                        requireGuard(!occupied, R.string.setup_busy)
                        requireGuard(trialStatus(app).phase == "WAIT_OWNER_CONFIRM", R.string.setup_incomplete)
                        shell("/system/bin/sh $SETUP_SCRIPT confirm-native")
                    }
                    SetupAction.ABORT -> {
                        // Abort uses the frozen, already recognised trial implementation, even if fresh checks fail.
                        requireGuard(knownSetupScript(app), R.string.setup_incomplete)
                        shell("/system/bin/sh $SETUP_SCRIPT abort", timeoutSeconds = 55)
                    }
                    SetupAction.QUALIFY -> {
                        requireGuard(assessment.eligible && !occupied, R.string.setup_incomplete)
                        val before = trialStatus(app)
                        val binding = requireNotNull(assessment.binding)
                        requireGuard(before.phase == "PASSED" && before.bindingDigest == binding.digest, R.string.setup_incomplete)
                        val qualified = SetupTrialStatus.parse(shell("/system/bin/sh $SETUP_SCRIPT qualify"))
                        requireGuard(qualified.phase == "QUALIFIED" && qualified.bindingDigest == binding.digest && centralQualified(binding), R.string.setup_incomplete)
                        requireGuard(preferences(app).edit().putString("qualification_binding", binding.digest)
                            .putString("qualification_controller", binding.controllerDigest).commit(), R.string.error_guard_preferences)
                    }
                    SetupAction.CHECK, SetupAction.STATUS -> Unit
                }
                val binding = assessment.binding
                val qualified = binding != null && localQualified(app, binding) && centralQualified(binding)
                if (action != SetupAction.STATUS && !qualified) preferences(app).edit()
                    .remove("qualification_binding").remove("qualification_controller").apply()
                SetupSnapshot(assessment, trialStatus(app), qualified, occupied)
            } catch (e: GuardFailure) {
                SetupSnapshot(latestAssessment, runCatching { trialStatus(app) }.getOrDefault(SetupTrialStatus("UNKNOWN")),
                    error = context.getString(e.stringId), errorReason = when (e.stringId) {
                        R.string.error_shizuku_not_ready -> "SHIZUKU_UNAVAILABLE"
                        R.string.setup_busy -> "LIVE_CONTROLLER_PRESENT"
                        R.string.setup_recovery_refused -> "RECOVERY_REFUSED"
                        else -> "SETUP_INCOMPLETE"
                    })
            } catch (e: Exception) {
                Log.w("GuardRuntime", "Setup observation unavailable", e)
                val failed = SupportAssessment(SupportAssessment.Level.UNSUPPORTED, "PROBE_UNAVAILABLE", facts = latestAssessment?.facts.orEmpty())
                latestAssessment = failed
                SetupSnapshot(failed, SetupTrialStatus("UNKNOWN"), error = context.getString(R.string.setup_incomplete),
                    errorReason = "PROBE_UNAVAILABLE")
            }
            val observed = result.copy(observedAt = if (result.error == null) SystemClock.elapsedRealtime() else null,
                assessmentObservedAt = latestAssessmentObservedAt)
            main.post { callback(observed) }
        }
    }

    private fun localQualified(context: Context, binding: NativeBinding): Boolean {
        val saved = preferences(context)
        return DeviceQualification(saved.getString("qualification_binding", "").orEmpty(),
            saved.getString("qualification_controller", "").orEmpty(), true).matches(binding.digest, binding.controllerDigest)
    }

    private fun centralQualified(binding: NativeBinding): Boolean {
        val text = shell("cat /data/local/tmp/nxtpaper_guard.qualification 2>/dev/null || true")
        val record = runCatching { parseData(text) }.getOrNull() ?: return false
        return record.keys == setOf("schema", "binding_sha256", "controller_sha256", "trial_id", "owner_confirmed", "result") &&
            record["schema"] == "1" && record["binding_sha256"] == binding.digest &&
            record["controller_sha256"] == binding.controllerDigest && record["owner_confirmed"] == "1" &&
            record["result"] == "passed" && record["trial_id"]?.matches(Regex("[A-Za-z0-9_-]+")) == true
    }

    private fun requireQualified(context: Context) {
        val assessment = assess(context).also { latestAssessment = it }
        val binding = assessment.binding
        val valid = binding != null && assessment.eligible && localQualified(context, binding) && centralQualified(binding)
        if (!valid) preferences(context).edit().remove("qualification_binding").remove("qualification_controller").apply()
        requireGuard(valid, R.string.setup_required)
        profileAsset = requireNotNull(binding).text.toByteArray(Charsets.UTF_8)
    }

    private fun controllerPresent(): Boolean = shell("""
        ${livePidCheck()}
        if [ "${'$'}live" = 1 ] || [ -d $LOCK_DIR ] || [ -d /data/local/tmp/nxtpaper_guard.operation.lock ]; then printf busy; fi
    """.trimIndent()).isNotEmpty()

    private fun knownSetupScript(context: Context): Boolean {
        val expected = sha256(context.assets.open("nxtpaper_setup.sh").use { it.readBytes() })
        return shell("sha256sum $SETUP_SCRIPT 2>/dev/null | cut -d ' ' -f 1 || true") == expected &&
            shell("sha256sum $SCRIPT 2>/dev/null | cut -d ' ' -f 1 || true") == sha256(requireNotNull(asset))
    }

    private fun trialStatus(context: Context): SetupTrialStatus {
        if (knownSetupScript(context)) return SetupTrialStatus.parse(shell("/system/bin/sh $SETUP_SCRIPT status"))
        val evidence = shell("if [ -e /data/local/tmp/nxtpaper_setup.pid ] || [ -d /data/local/tmp/nxtpaper_setup.lock ]; then printf busy; fi")
        return SetupTrialStatus(if (evidence.isEmpty()) "STOPPED" else "UNKNOWN")
    }

    private fun assess(context: Context): SupportAssessment {
        val adapter = NativeAdapter.parse(context.assets.open("compatibility/adapters/tcl-slider-v1.properties").bufferedReader().use { it.readText() })
        val registry = requireNotNull(context.assets.list("compatibility/profiles")).filter { it.endsWith(".properties") }.map {
            SupportAssessmentEngine.parseRegistry(context.assets.open("compatibility/profiles/$it").bufferedReader().use { reader -> reader.readText() })
        }
        val identity = mapOf("model" to "ro.product.model", "device" to "ro.product.device", "android" to "ro.build.version.release",
            "sdk" to "ro.build.version.sdk", "fingerprint" to "ro.build.fingerprint").mapValues { shell("getprop ${it.value}") }
        val features = shell("pm list features", outputLimit = 65536).lineSequence().toSet()
        val caps = shell("getevent -lp", outputLimit = 524288)
        val input = shell("dumpsys input", outputLimit = 524288)
        val node = runCatching { SupportAssessmentEngine.discoverInput(caps) }.getOrDefault("")
        val readableRawInput = node.isNotEmpty() && shell("if [ -r '$node' ]; then printf readable; fi") == "readable"
        val layout = runCatching { SupportAssessmentEngine.activeLayout(input, node) }.getOrDefault("")
        val layoutText = if (layout.isNotEmpty()) shell("cat '$layout'", outputLimit = 262144) else ""
        val layoutDigest = if (layout.isNotEmpty()) shell("sha256sum '$layout' | cut -d ' ' -f 1") else ""
        val settings = adapter.values.filterKeys { it.endsWith("_key") }.values.joinToString("\n") { key ->
            "$key=" + shell("settings get secure $key")
        }
        val versions = mapOf("systemui_version" to "com.android.systemui", "launcher_version" to "com.tcl.android.launcher",
            "manager_version" to "com.tct.onetouchbooster").mapValues { (_, pkg) ->
            shell("dumpsys package $pkg | sed -n 's/^.*versionCode=\\([0-9][0-9]*\\).*$/\\1/p' | head -n 1")
        }
        val keys = runCatching {
            val on = KeyEvent.keyCodeFromString("KEYCODE_TSWT_ON")
            val off = KeyEvent.keyCodeFromString("KEYCODE_TSWT_OFF")
            RuntimeKeyPair(on, off, KeyEvent.keyCodeToString(on), KeyEvent.keyCodeToString(off))
        }.getOrDefault(RuntimeKeyPair(0, 0, "", ""))
        return SupportAssessmentEngine.assess(adapter, registry, SupportAssessmentEngine.Observations(identity,
            shell("getprop ro.product.manufacturer"), features.any { it == "feature:vendor.software.support.tcl_switch" ||
                it.startsWith("feature:vendor.software.support.tcl_switch=") }, features.any { it == "feature:android.hardware.telephony" ||
                it.startsWith("feature:android.hardware.telephony=") }, settings, caps, input, layout, layoutText, layoutDigest, versions, keys,
            readableRawInput, shell("getprop sys.tct.support_ui_switch_button")), sha256(requireNotNull(asset))).also {
                latestAssessment = it
                latestAssessmentObservedAt = SystemClock.elapsedRealtime()
            }
    }

    /** Hold the same shell mutex used by both controllers while replacing stopped files. */
    private fun deployFiles(files: Map<String, ByteArray>) {
        val writes = files.entries.joinToString("\n") { (path, bytes) ->
            val encoded = android.util.Base64.encodeToString(bytes, android.util.Base64.NO_WRAP)
            val mode = if (path == PROFILE) "600" else "700"
            "printf '%s' '$encoded' | base64 -d > $path.pending && chmod $mode $path.pending && mv $path.pending $path || exit 1"
        }
        shell("""
            mkdir /data/local/tmp/nxtpaper_guard.operation.lock || exit 1
            trap 'rm -f /data/local/tmp/nxtpaper_guard.operation.lock/boot; rmdir /data/local/tmp/nxtpaper_guard.operation.lock' EXIT
            operation_boot=${'$'}(cat /proc/sys/kernel/random/boot_id) || exit 1
            case "${'$'}operation_boot" in ''|*[!a-zA-Z0-9-]*) exit 1 ;; esac
            printf '%s\n' "${'$'}operation_boot" > /data/local/tmp/nxtpaper_guard.operation.lock/boot || exit 1
            ${livePidCheck()}
            [ "${'$'}live" = 0 ] && [ ! -d $LOCK_DIR ] && [ ! -e /data/local/tmp/nxtpaper_setup.pid ] && [ ! -d /data/local/tmp/nxtpaper_setup.lock ] || exit 1
            $writes
        """.trimIndent(), timeoutSeconds = 20)
    }

    private fun status(): Result {
        // Old controllers ignore command-line arguments; do not run their script for status.
        val output = shell("""
            ${livePidCheck()}
            if [ "${'$'}(cat $VERSION 2>/dev/null)" = '$controllerId' ] && [ -f $SCRIPT ] &&
                { [ "${'$'}live" = 0 ] || [ "${'$'}live_known" = 1 ]; }; then
                /system/bin/sh $SCRIPT status
            else
                if [ "${'$'}live" = 1 ]; then
                    echo 'UPDATE_REQUIRED:0:0:0:0:UNKNOWN'
                else
                    echo 'STOPPED:0:0:0:0:UNKNOWN'
                fi
            fi
        """.trimIndent())
        return parse(output)
    }

    private fun start(context: Context): Result {
        val previous = status()
        if (previous.phase == "INITIALIZING") return awaitReady()
        if (previous.phase !in setOf("STOPPED", "UPDATE_REQUIRED", "ERROR")) {
            return previous
        }
        // Never terminate an unknown live controller to update it: it may own
        // an active commitment. Finish/stop that version before upgrading.
        if (previous.phase == "UPDATE_REQUIRED") return previous
        if (previous.phase == "ERROR") {
            val live = shell("${livePidCheck()}\nprintf '%s' \"${'$'}live\"")
            requireGuard(live != "1", R.string.error_stop_before_retry)
        }
        requireQualified(context)
        val checked = compatibility()
        requireGuard(checked.verdict == GuardCompatibility.Verdict.VERIFIED, compatibilityError(checked))
        deployController()
        shell("nohup /system/bin/sh $SCRIPT > /data/local/tmp/nxtpaper_guard.start.log 2>&1 < /dev/null &")
        return awaitReady()
    }

    private fun deployController() {
        // Recheck at deployment, not just the earlier UI/status sample. Never replace a live daemon.
        requireGuard(shell("${livePidCheck()}\nprintf '%s' \"${'$'}live\"") != "1", R.string.error_stop_before_retry)
        requireGuard(shell("if [ -e /data/local/tmp/nxtpaper_setup.pid ] || [ -d /data/local/tmp/nxtpaper_setup.lock ]; then printf busy; fi").isEmpty(), R.string.setup_busy)
        deployFiles(mapOf(PROFILE to requireNotNull(profileAsset), SCRIPT to requireNotNull(asset)))
        shell("printf '%s' '$controllerId' > $VERSION")
    }

    private fun awaitReady(): Result {
        repeat(15) {
            Thread.sleep(1000)
            val current = status()
            if (current.phase == "ERROR") return current
            if (current.phase !in setOf("STOPPED", "UPDATE_REQUIRED", "INITIALIZING")) return current
        }
        throw GuardFailure(R.string.error_guard_start_timeout)
    }

    private fun requestStop(context: Context): Result {
        requireGuard(status().phase != "UPDATE_REQUIRED", R.string.guard_update_required)
        val marker = shell("cat $VERSION 2>/dev/null || true").trim()
        if (marker != controllerId) {
            // No matching live controller: leave its diagnostic files intact.
            return Result("STOPPED")
        }
        val result = parse(shell("/system/bin/sh $SCRIPT request-stop", timeoutSeconds = 12))
        if (result.phase == "ERROR" && result.errorCode?.startsWith("STOP_") == true) {
            val actual = operationFeedback(context, context.getString(R.string.error_stop_request))
            return if (GuardExitPolicy.stopConfirmedFromStatus(actual.phase, actual.exitDeadline)) actual.copy(error = null) else actual
        }
        if (result.phase != "ERROR" && !GuardExitPolicy.stopAcknowledged(result.phase, result.exitDeadline)) {
            return operationFeedback(context, context.getString(R.string.error_stop_request))
        }
        // The daemon owns restoration and all live PID/lock/state cleanup.
        // A pending acknowledgement is success; no 300-second shell wait.
        return result
    }

    @SuppressLint("UseKtx") // Check the durable cancellation journal write.
    private fun cancelStop(context: Context): Result {
        val before = status()
        requireGuard(before.phase != "UPDATE_REQUIRED", R.string.guard_update_required)
        if (before.phase !in setOf("STARTING", "COMMITTED")) {
            return if (before.phase in setOf("RESTORING", "STOPPED")) before
                else before.copy(error = context.getString(R.string.error_stop_cancel))
        }
        val identity = liveControllerIdentity()
        requireGuard(identity != null, R.string.error_stop_cancel)
        if (before.exitPending) {
            // Persist a narrowly scoped intent before sending. If the app dies
            // after cancellation, a status/reconnect can finish its preference
            // update only for this exact daemon and pending deadline.
            requireGuard(preferences(context).edit().putBoolean("enabled", false)
                .putString(CANCEL_IDENTITY, identity).putLong(CANCEL_DEADLINE, before.exitDeadline)
                .commit(), R.string.error_guard_preferences)
        }
        return finishCancellation(context, identity)
    }

    private fun finishCancellation(context: Context, expectedIdentity: String?): Result {
        val result = parse(shell("/system/bin/sh $SCRIPT cancel-stop", timeoutSeconds = 12))
        val actual = if (result.phase == "ERROR" && result.errorCode?.startsWith("STOP_") == true) {
            operationFeedback(context, context.getString(R.string.error_stop_cancel))
        } else result
        if (GuardExitPolicy.continuationConfirmed(actual.phase, actual.exitDeadline) &&
            expectedIdentity != null && liveControllerIdentity() == expectedIdentity) {
            clearCancellation(context, enabled = true)
            return actual.copy(error = null)
        }
        if (actual.phase !in setOf("STARTING", "COMMITTED") || !actual.exitPending) {
            clearCancellation(context, enabled = false)
        }
        if (actual.phase in setOf("RESTORING", "STOPPED")) return actual.copy(error = null)
        return actual.copy(error = actual.error ?: context.getString(R.string.error_stop_cancel))
    }

    private fun livePidCheck() = """
        live=0
        live_known=0
        record=${'$'}(cat $PID 2>/dev/null)
        pid=${'$'}{record%%:*}
        if [ -e $PID ]; then
            # Existing evidence is possibly live until absence is established.
            # Denied process inspection must never authorize replacement.
            live=1
            case "${'$'}pid" in
                ''|*[!0-9]*) ;;
                *)
                    rest=${'$'}{record#*:}
                    saved_start=${'$'}{rest%%:*}
                    saved_boot=${'$'}{rest#*:}
                    token_valid=0
                    printf '%s\n' "${'$'}record" | grep -Eq '^[0-9]+:[0-9]+:[a-zA-Z0-9-]+$' && token_valid=1
                    actual_boot=${'$'}(cat /proc/sys/kernel/random/boot_id 2>/dev/null)
                    if [ "${'$'}token_valid" = 1 ] && [ -n "${'$'}actual_boot" ] &&
                        [ -n "${'$'}saved_boot" ] && [ "${'$'}saved_boot" != "${'$'}actual_boot" ]; then
                        live=0
                    elif ! kill -0 "${'$'}pid" 2>/dev/null && [ ! -d /proc/${'$'}pid ] && [ -d /proc/1 ]; then
                        live=0
                    else
                        actual_start=${'$'}(sed 's/^.*) //' /proc/${'$'}pid/stat 2>/dev/null | cut -d ' ' -f 20)
                        actual_command=${'$'}(tr '\000' '\n' < /proc/${'$'}pid/cmdline 2>/dev/null)
                        if [ -n "${'$'}actual_start" ] && [ -n "${'$'}actual_command" ]; then
                            if ! printf '%s\n' "${'$'}actual_command" | grep -Fx '$SCRIPT' >/dev/null; then
                                live=0
                            elif [ "${'$'}token_valid" = 1 ] && [ -n "${'$'}saved_start" ] &&
                                [ -n "${'$'}actual_boot" ]; then
                                if [ "${'$'}saved_start" = "${'$'}actual_start" ] && [ "${'$'}saved_boot" = "${'$'}actual_boot" ]; then
                                    live_known=1
                                else live=0; fi
                            fi
                        fi
                    fi ;;
            esac
        fi
    """.trimIndent()

    private fun parse(output: String): Result {
        val parsed = try { GuardStatus.parse(output) }
        catch (_: IllegalArgumentException) { throw GuardFailure(R.string.error_guard_status_invalid) }
        return Result(
            parsed.phase, remaining = parsed.remaining, physical = parsed.physical,
            errorCode = parsed.errorCode, sessionStart = parsed.sessionStart,
            deadline = parsed.deadline, nextDuration = parsed.nextDuration,
            exitDeadline = parsed.exitDeadline, exitRemaining = parsed.exitRemaining
        )
    }

    private fun errorResource(code: String?): Int = when {
        code == "UNSUPPORTED_FIRMWARE" -> R.string.error_firmware
        code?.startsWith("PROFILE_") == true || code == "INVALID_FIRMWARE_PROFILE" -> R.string.error_firmware
        code?.startsWith("COMPATIBILITY_") == true -> R.string.error_compatibility
        code in setOf("PHYSICAL_SWITCH_CHANGED", "INVALID_NATIVE_COMMAND") -> R.string.error_compatibility
        code == "CONTROLLER_IDENTITY_UNAVAILABLE" -> R.string.error_compatibility
        code in setOf("INVALID_NATIVE_SETTINGS_OR_PRESET", "NATIVE_PRESET_MISMATCH") -> R.string.error_preset
        code == "NATIVE_STATE_READ_FAILED" -> R.string.error_native_state
        code == "SHELL_PRIVILEGE_REQUIRED" -> R.string.error_privilege
        code?.startsWith("REQUIRED_TOOL_UNAVAILABLE") == true -> R.string.error_tools
        code in setOf("PHYSICAL_SWITCH_UNAVAILABLE", "PHYSICAL_MONITOR_FAILED", "PHYSICAL_STATE_INVALID") -> R.string.error_switch_monitor
        code == "DAEMON_UNRESPONSIVE" -> R.string.error_unresponsive
        code in setOf("STOP_TIMEOUT", "NORMAL_RESTORE_TIMEOUT") -> R.string.error_restore_timeout
        code in setOf("INPUT_FIFO_FAILED", "INPUT_PIPE_FAILED", "MONITOR_START_FAILED") -> R.string.error_monitor_start
        code == "DURATION_BUSY" -> R.string.error_duration_busy
        code == "DURATION_INVALID" -> R.string.error_duration_invalid
        code?.startsWith("DURATION_") == true -> R.string.error_duration_change
        code?.startsWith("STOP_") == true -> R.string.error_stop_request
        else -> R.string.error_guard_paused
    }

    // The pinned Shizuku 13.1.5 exposes this legacy bridge. All process work stays
    // off the main thread and is bounded; callers never report success from nohup alone.
    private fun shell(command: String, stdin: ByteArray? = null, timeoutSeconds: Long = 35, outputLimit: Int = 8192): String {
        val method = Shizuku::class.java.getDeclaredMethod(
            "newProcess", Array<String>::class.java, Array<String>::class.java, String::class.java
        ).apply { isAccessible = true }
        val process = method.invoke(null, arrayOf("/system/bin/sh", "-c", command), null, null) as ShizukuRemoteProcess
        val stdout = StringBuilder()
        val stderr = StringBuilder()
        val outReader = Thread { runCatching { process.inputStream.bufferedReader().use { reader ->
            reader.forEachLine { if (stdout.length < outputLimit) stdout.appendLine(it) }
        } } }
        val errReader = Thread { runCatching { process.errorStream.bufferedReader().use { reader ->
            reader.forEachLine { if (stderr.length < 8192) stderr.appendLine(it) }
        } } }
        outReader.isDaemon = true
        errReader.isDaemon = true
        outReader.start()
        errReader.start()
        try {
            process.outputStream.use { stream -> if (stdin != null) stream.write(stdin) }
            requireGuard(process.waitForTimeout(timeoutSeconds, TimeUnit.SECONDS), R.string.error_command_timeout)
            outReader.join(1000)
            errReader.join(1000)
            if (process.exitValue() != 0) {
                Log.w("GuardRuntime", "Shell command failed: ${stderr.toString().trim().take(300)}")
                throw GuardFailure(R.string.error_command_failed)
            }
            return stdout.toString().trim()
        } finally {
            runCatching { process.destroy() }
        }
    }
}
