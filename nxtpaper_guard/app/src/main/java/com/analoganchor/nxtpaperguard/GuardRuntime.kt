package com.analoganchor.nxtpaperguard

import android.content.Context
import android.content.pm.PackageManager
import android.os.Handler
import android.os.Looper
import android.util.Log
import rikka.shizuku.Shizuku
import rikka.shizuku.ShizukuRemoteProcess
import java.security.MessageDigest
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/** One serialized command path for the UI and Shizuku reconnect listener. */
object GuardRuntime {
    enum class Action { STATUS, START, STOP, SET_DURATION, TEST_INK, TEST_NORMAL }
    data class Result(
        val phase: String,
        val remaining: Long = 0,
        val error: String? = null,
        val physical: String = "UNKNOWN",
        val errorCode: String? = null,
        val sessionStart: Long = 0,
        val deadline: Long = 0,
        val nextDuration: Long = 300,
        val nativeInkState: Int? = null
    ) {
        val sessionDuration: Long get() = (deadline - sessionStart).coerceAtLeast(0)
    }

    private const val SCRIPT = "/data/local/tmp/nxtpaper_guard.sh"
    private const val VERSION = "/data/local/tmp/nxtpaper_guard.version"
    private const val PID = "/data/local/tmp/nxtpaper_guard.pid"
    private const val STATE_FILE = "/data/local/tmp/nxtpaper_guard.state"
    private const val LOCK_DIR = "/data/local/tmp/nxtpaper_guard.lock"
    private val executor = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private var asset: ByteArray? = null
    private var controllerId: String? = null
    private var lastLanguage: String? = null
    @Volatile private var stopGeneration = 0
    private class GuardFailure(val stringId: Int) : IllegalStateException()
    private fun requireGuard(condition: Boolean, stringId: Int) {
        if (!condition) throw GuardFailure(stringId)
    }

    fun desired(context: Context): Boolean = preferences(context).getBoolean("enabled", false)
    fun setDesired(context: Context, enabled: Boolean) {
        if (!enabled) stopGeneration++
        preferences(context).edit().putBoolean("enabled", enabled).apply()
        if (!enabled) BootReminder.cancel(context)
    }
    private fun preferences(context: Context) = context.getSharedPreferences("guard", Context.MODE_PRIVATE)

    fun isAuthorized(): Boolean = try {
        Shizuku.pingBinder() && Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED
    } catch (_: Exception) { false }

    fun runAsync(context: Context, action: Action, duration: Long? = null, callback: (Result) -> Unit) {
        val app = context.applicationContext
        val generation = stopGeneration
        executor.execute {
            val rawResult = try {
                requireGuard(isAuthorized(), R.string.error_shizuku_not_ready)
                loadController(app)
                val language = if (context.resources.configuration.locales[0].language == "ar") "ar" else "en"
                if (lastLanguage != language) {
                    shell("printf '%s' '$language' > /data/local/tmp/nxtpaper_guard.language")
                    lastLanguage = language
                }
                when (action) {
                    Action.STATUS -> status()
                    Action.START -> {
                        // Recheck the preference on this serialized queue: a queued reconnect must
                        // never undo a later explicit Stop from the user.
                        if (desired(app)) start() else status()
                    }
                    Action.STOP -> stop()
                    Action.SET_DURATION -> {
                        if (generation != stopGeneration) status() else {
                            requireGuard(duration != null && duration in GuardStatus.durations, R.string.error_duration_invalid)
                            val before = status()
                            requireGuard(before.phase != "UPDATE_REQUIRED", R.string.guard_update_required)
                            if (before.phase == "STOPPED") deployController()
                            val configured = parse(shell("/system/bin/sh $SCRIPT set-duration $duration"))
                            if (configured.phase == "ERROR" && configured.errorCode?.startsWith("DURATION_") == true) {
                                durationFeedback(context, context.getString(errorResource(configured.errorCode)))
                            } else configured
                        }
                    }
                    Action.TEST_INK, Action.TEST_NORMAL -> {
                        requireGuard(!desired(app) && status().phase == "STOPPED", R.string.error_tests_guard_active)
                        shell("input keyevent ${if (action == Action.TEST_INK) 343 else 344}")
                        status()
                    }
                }
            } catch (e: GuardFailure) {
                if (action == Action.SET_DURATION) durationFeedback(context, context.getString(e.stringId))
                else Result("ERROR", error = context.getString(e.stringId))
            } catch (e: Exception) {
                Log.e("GuardRuntime", "Guard operation failed: $action", e)
                if (action == Action.SET_DURATION) durationFeedback(context, context.getString(R.string.error_duration_change))
                else Result("ERROR", error = context.getString(R.string.error_guard_contact))
            }
            val localizedResult = if (rawResult.phase == "ERROR" && rawResult.error == null)
                rawResult.copy(error = context.getString(errorResource(rawResult.errorCode))) else rawResult
            // Use the controller's Shizuku settings context. A cloned app's
            // ContentResolver can read an unrelated work-profile value.
            // This display-only snapshot cannot turn a healthy guard into ERROR.
            val nativeInkState = if (isAuthorized()) runCatching {
                parseNativeInkState(shell("settings get secure nxtpaper_ink_style_state", timeoutSeconds = 3))
            }.getOrNull() else null
            val result = localizedResult.copy(nativeInkState = nativeInkState)
            main.post {
                if (action == Action.START && result.error == null && result.phase != "STOPPED") {
                    BootReminder.cancel(app)
                }
                callback(result)
            }
        }
    }

    private fun durationFeedback(context: Context, message: String): Result {
        // Configuration failures must never replace a healthy daemon's phase.
        val actual = runCatching { if (isAuthorized()) status() else null }.getOrNull()
        return when {
            actual == null -> Result("ERROR", error = message)
            actual.phase == "ERROR" -> actual.copy(error = context.getString(errorResource(actual.errorCode)))
            else -> actual.copy(error = message)
        }
    }

    private fun loadController(context: Context) {
        if (asset != null) return
        val bytes = context.assets.open("nxtpaper_guard.sh").use { it.readBytes() }
        asset = bytes
        val digest = MessageDigest.getInstance("SHA-256").digest(bytes)
            .joinToString("") { "%02x".format(it.toInt() and 0xff) }
        controllerId = "${BuildConfig.VERSION_NAME}:$digest"
    }

    private fun status(): Result {
        // Old controllers ignore command-line arguments; do not run their script for status.
        val output = shell("""
            if [ "${'$'}(cat $VERSION 2>/dev/null)" = '$controllerId' ] && [ -f $SCRIPT ]; then
                /system/bin/sh $SCRIPT status
            else
                ${livePidCheck()}
                if [ "${'$'}live" = 1 ]; then
                    echo 'UPDATE_REQUIRED:0:0:0:0:UNKNOWN'
                else
                    echo 'STOPPED:0:0:0:0:UNKNOWN'
                fi
            fi
        """.trimIndent())
        return parse(output)
    }

    private fun start(): Result {
        val previous = status()
        if (previous.phase == "INITIALIZING") return awaitReady()
        if (previous.phase !in setOf("STOPPED", "UPDATE_REQUIRED", "ERROR")) {
            return previous
        }
        if (previous.phase == "UPDATE_REQUIRED") stopLegacy(restore = false)
        if (previous.phase == "ERROR") {
            val live = shell("${livePidCheck()}\nprintf '%s' \"${'$'}live\"")
            if (live == "1") {
                val stopped = parse(shell("/system/bin/sh $SCRIPT stop", timeoutSeconds = 60))
                requireGuard(stopped.phase == "STOPPED", R.string.error_stop_before_retry)
            } else {
                shell("rm -f $STATE_FILE $PID /data/local/tmp/nxtpaper_guard.start.log; rm -rf /data/local/tmp/nxtpaper_guard.lock")
            }
        }
        deployController()
        shell("nohup /system/bin/sh $SCRIPT > /data/local/tmp/nxtpaper_guard.start.log 2>&1 < /dev/null &")
        return awaitReady()
    }

    private fun deployController() {
        // Write the asset through stdin. Shell cannot read the app's private files.
        shell("cat > $SCRIPT.pending && chmod 700 $SCRIPT.pending && mv $SCRIPT.pending $SCRIPT", asset)
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

    private fun stop(): Result {
        if (status().phase == "UPDATE_REQUIRED") {
            stopLegacy(restore = true)
            shell("rm -f $STATE_FILE $PID; rm -rf /data/local/tmp/nxtpaper_guard.lock")
            return Result("STOPPED")
        }
        val marker = shell("cat $VERSION 2>/dev/null || true").trim()
        if (marker != controllerId) {
            shell("rm -f $STATE_FILE $PID; rm -rf /data/local/tmp/nxtpaper_guard.lock")
            return Result("STOPPED")
        }
        val result = parse(shell("/system/bin/sh $SCRIPT stop", timeoutSeconds = 60))
        requireGuard(result.phase == "STOPPED", R.string.error_guard_restore_wait)
        shell("rm -f $STATE_FILE $PID; rm -rf /data/local/tmp/nxtpaper_guard.lock")
        return result
    }

    private fun livePidCheck() = """
        live=0
        record=${'$'}(cat $PID 2>/dev/null)
        pid=${'$'}{record%%:*}
        case "${'$'}pid" in
            ''|*[!0-9]*) ;;
            *)
                if kill -0 "${'$'}pid" 2>/dev/null; then
                    if tr '\000' '\n' < /proc/${'$'}pid/cmdline 2>/dev/null | grep -Fx '$SCRIPT' >/dev/null; then
                        live=1
                        case "${'$'}record" in
                            *:*)
                                rest=${'$'}{record#*:}
                                saved_start=${'$'}{rest%%:*}
                                saved_boot=${'$'}{rest#*:}
                                actual_start=${'$'}(sed 's/^.*) //' /proc/${'$'}pid/stat 2>/dev/null | cut -d ' ' -f 20)
                                actual_boot=${'$'}(cat /proc/sys/kernel/random/boot_id 2>/dev/null)
                                [ "${'$'}saved_start" = "${'$'}actual_start" ] && [ "${'$'}saved_boot" = "${'$'}actual_boot" ] || live=0 ;;
                        esac
                    fi
                fi ;;
        esac
    """.trimIndent()

    private fun stopLegacy(restore: Boolean) {
        shell("""
            ${livePidCheck()}
            if [ "${'$'}live" = 1 ]; then
                kill -TERM "${'$'}pid" || exit 1
                attempts=0
                while kill -0 "${'$'}pid" 2>/dev/null; do
                    attempts=${'$'}((attempts + 1))
                    [ "${'$'}attempts" -lt 55 ] || exit 1
                    sleep 1
                done
            fi
            ${if (restore) "input keyevent 344" else ":"}
        """.trimIndent(), timeoutSeconds = 60)
    }

    private fun parse(output: String): Result {
        val parsed = try { GuardStatus.parse(output) }
        catch (_: IllegalArgumentException) { throw GuardFailure(R.string.error_guard_status_invalid) }
        return Result(
            parsed.phase, remaining = parsed.remaining, physical = parsed.physical,
            errorCode = parsed.errorCode, sessionStart = parsed.sessionStart,
            deadline = parsed.deadline, nextDuration = parsed.nextDuration
        )
    }

    private fun errorResource(code: String?): Int = when {
        code == "UNSUPPORTED_FIRMWARE" -> R.string.error_firmware
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
        else -> R.string.error_guard_paused
    }

    // The pinned Shizuku 13.1.5 exposes this legacy bridge. All process work stays
    // off the main thread and is bounded; callers never report success from nohup alone.
    private fun shell(command: String, stdin: ByteArray? = null, timeoutSeconds: Long = 35): String {
        val method = Shizuku::class.java.getDeclaredMethod(
            "newProcess", Array<String>::class.java, Array<String>::class.java, String::class.java
        ).apply { isAccessible = true }
        val process = method.invoke(null, arrayOf("/system/bin/sh", "-c", command), null, null) as ShizukuRemoteProcess
        val stdout = StringBuilder()
        val stderr = StringBuilder()
        val outReader = Thread { runCatching { process.inputStream.bufferedReader().use { reader ->
            reader.forEachLine { if (stdout.length < 8192) stdout.appendLine(it) }
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
