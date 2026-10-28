package com.analoganchor.nxtpaperguard

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.ColorStateList
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.view.View
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.content.ContextCompat
import androidx.core.os.LocaleListCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import com.google.android.material.button.MaterialButton
import rikka.shizuku.Shizuku
import java.text.NumberFormat

class MainActivity : AppCompatActivity() {
    private lateinit var tvShizukuStatus: TextView
    private lateinit var tvHardwareState: TextView
    private lateinit var tvServiceStatus: TextView
    private lateinit var tvCommitmentRemaining: TextView
    private lateinit var tvGuardError: TextView
    private lateinit var btnGrantShizuku: Button
    private lateinit var btnOpenShizuku: Button
    private lateinit var btnToggleService: Button
    private lateinit var btnCancelResume: Button
    private lateinit var btnTestInk: Button
    private lateinit var btnTestNormal: Button
    private lateinit var durationButtons: Map<Long, MaterialButton>

    private val mainHandler = Handler(Looper.getMainLooper())
    private var visible = false
    private var actionInFlight = false
    private var currentAction: GuardRuntime.Action? = null
    private var lastResult = GuardRuntime.Result("STOPPED")
    private var actionError: String? = null
    private var actionSequence = 0
    private var hasStatusResult = false
    private var diagnosisInFlight = false

    private val notificationPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        Toast.makeText(
            this,
            if (granted) R.string.reminders_enabled else R.string.reminders_skipped,
            Toast.LENGTH_SHORT
        ).show()
    }

    private val poll = object : Runnable {
        override fun run() {
            if (!visible) return
            refreshConnectionAndHardware()
            if (GuardRuntime.isAuthorized() && !actionInFlight && !diagnosisInFlight) {
                runAction(GuardRuntime.Action.STATUS)
            }
            mainHandler.postDelayed(this, 2_000)
        }
    }

    private val permissionListener = Shizuku.OnRequestPermissionResultListener { code, grant ->
        if (code == SHIZUKU_PERMISSION_REQUEST) {
            runOnUiThread {
                refreshConnectionAndHardware()
                if (grant == PackageManager.PERMISSION_GRANTED && !actionInFlight) {
                    runAction(
                        if (GuardRuntime.desired(this)) GuardRuntime.Action.START
                        else GuardRuntime.Action.STATUS
                    )
                }
            }
        }
    }

    private val binderReceivedListener = Shizuku.OnBinderReceivedListener {
        runOnUiThread {
            if (::tvShizukuStatus.isInitialized) {
                refreshConnectionAndHardware()
                if (visible && GuardRuntime.isAuthorized() && !actionInFlight) {
                    runAction(GuardRuntime.Action.STATUS)
                }
            }
        }
    }

    private val binderDeadListener = Shizuku.OnBinderDeadListener {
        runOnUiThread {
            lastResult = GuardRuntime.Result("DISCONNECTED")
            hasStatusResult = false
            if (::tvShizukuStatus.isInitialized) refreshConnectionAndHardware()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        WindowCompat.getInsetsController(window, window.decorView).apply {
            isAppearanceLightStatusBars = false
            isAppearanceLightNavigationBars = false
        }
        setContentView(R.layout.activity_main)
        applySafeInsets()

        tvShizukuStatus = findViewById(R.id.tvShizukuStatus)
        tvHardwareState = findViewById(R.id.tvHardwareState)
        tvServiceStatus = findViewById(R.id.tvServiceStatus)
        tvCommitmentRemaining = findViewById(R.id.tvCommitmentRemaining)
        tvGuardError = findViewById(R.id.tvGuardError)
        btnGrantShizuku = findViewById(R.id.btnGrantShizuku)
        btnOpenShizuku = findViewById(R.id.btnOpenShizuku)
        btnToggleService = findViewById(R.id.btnToggleService)
        btnCancelResume = findViewById(R.id.btnCancelResume)
        btnTestInk = findViewById(R.id.btnTestInk)
        btnTestNormal = findViewById(R.id.btnTestNormal)
        durationButtons = mapOf(
            300L to findViewById(R.id.btnDurationDefault),
            7200L to findViewById(R.id.btnDurationTwo),
            14400L to findViewById(R.id.btnDurationFour),
            21600L to findViewById(R.id.btnDurationSix),
            43200L to findViewById(R.id.btnDurationTwelve)
        )
        for ((duration, button) in durationButtons) {
            button.text = if (duration == 300L) {
                getString(R.string.duration_default, localizedNumber(5))
            } else durationLabel(duration)
            button.setOnClickListener { runAction(GuardRuntime.Action.SET_DURATION, duration) }
        }

        findViewById<TextView>(R.id.tvVersion).text = getString(R.string.version_label, BuildConfig.VERSION_NAME)
        btnOpenShizuku.setOnClickListener { openShizuku() }
        configureLanguageSelector()
        findViewById<Button>(R.id.btnShizukuHelp).setOnClickListener { showShizukuHelp() }
        findViewById<Button>(R.id.btnGuardHelp).setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle(R.string.guard_help_title)
                .setMessage(getString(R.string.guard_help_message, durationLabel(commitmentDuration())))
                .setPositiveButton(R.string.btn_close, null)
                .show()
        }
        findViewById<Button>(R.id.btnHardwareHelp).setOnClickListener {
            showExplanation(R.string.hardware_help_title, R.string.hardware_help_message)
        }
        btnGrantShizuku.setOnClickListener { requestShizukuPermission() }
        btnToggleService.setOnClickListener {
            if (isGuardActive() || (!GuardRuntime.isAuthorized() && GuardRuntime.desired(this))) {
                stopGuard()
            } else {
                GuardRuntime.setDesired(this, true)
                runAction(GuardRuntime.Action.START)
                offerRestartReminders()
            }
        }
        btnCancelResume.setOnClickListener {
            if (lastResult.exitPending) runAction(GuardRuntime.Action.CANCEL_STOP)
            else stopGuard()
        }
        btnTestInk.setOnClickListener { runAction(GuardRuntime.Action.TEST_INK) }
        btnTestNormal.setOnClickListener { runAction(GuardRuntime.Action.TEST_NORMAL) }
        findViewById<Button>(R.id.btnCheckCompatibility).setOnClickListener { showCompatibility() }
        findViewById<Button>(R.id.btnToggleTests).setOnClickListener { button ->
            val tests = findViewById<View>(R.id.layoutTests)
            val show = tests.visibility != View.VISIBLE
            tests.visibility = if (show) View.VISIBLE else View.GONE
            (button as Button).setText(if (show) R.string.hide_mode_tests else R.string.show_mode_tests)
        }

        Shizuku.addRequestPermissionResultListener(permissionListener)
        Shizuku.addBinderDeadListener(binderDeadListener)
        Shizuku.addBinderReceivedListenerSticky(binderReceivedListener)
    }

    override fun onResume() {
        super.onResume()
        visible = true
        mainHandler.removeCallbacks(poll)
        poll.run()
    }

    override fun onPause() {
        visible = false
        mainHandler.removeCallbacks(poll)
        super.onPause()
    }

    override fun onDestroy() {
        Shizuku.removeRequestPermissionResultListener(permissionListener)
        Shizuku.removeBinderReceivedListener(binderReceivedListener)
        Shizuku.removeBinderDeadListener(binderDeadListener)
        mainHandler.removeCallbacks(poll)
        super.onDestroy()
    }

    private fun applySafeInsets() {
        val root = findViewById<View>(R.id.guardRoot)
        val initialLeft = root.paddingLeft
        val initialTop = root.paddingTop
        val initialRight = root.paddingRight
        val initialBottom = root.paddingBottom
        ViewCompat.setOnApplyWindowInsetsListener(root) { view, insets ->
            val safe = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout())
            view.setPadding(
                initialLeft + safe.left,
                initialTop + safe.top,
                initialRight + safe.right,
                initialBottom + safe.bottom
            )
            insets
        }
        ViewCompat.requestApplyInsets(root)
    }

    private fun requestShizukuPermission() {
        try {
            if (Shizuku.pingBinder()) Shizuku.requestPermission(SHIZUKU_PERMISSION_REQUEST)
            else openShizuku()
        } catch (e: Exception) {
            actionError = getString(R.string.permission_error)
            refreshConnectionAndHardware()
        }
    }

    private fun stopGuard() {
        runAction(GuardRuntime.Action.STOP)
    }

    private fun runAction(action: GuardRuntime.Action, duration: Long? = null) {
        // Status polling must not swallow a user's tap. Its queued result is
        // superseded by actionSequence while the serialized runtime finishes it.
        if (actionInFlight && currentAction != GuardRuntime.Action.STATUS && action != GuardRuntime.Action.STOP) return
        if (action == GuardRuntime.Action.STOP && currentAction == GuardRuntime.Action.STOP) return
        val sequence = ++actionSequence
        actionInFlight = true
        currentAction = action
        refreshConnectionAndHardware()
        GuardRuntime.runAsync(this, action, duration) { result ->
            if (isFinishing || isDestroyed || sequence != actionSequence) return@runAsync
            actionInFlight = false
            currentAction = null
            lastResult = result
            hasStatusResult = true
            if (action == GuardRuntime.Action.SET_DURATION && result.error != null) {
                Toast.makeText(this, result.error, Toast.LENGTH_LONG).show()
            }
            if (result.error == null && result.phase in VERIFIED_PHASES) {
                // A verified healthy controller or a verified Stop clears old operation errors.
                actionError = null
            } else if (action !in setOf(GuardRuntime.Action.STATUS, GuardRuntime.Action.SET_DURATION) && result.error != null) {
                actionError = result.error
            }
            refreshConnectionAndHardware()
        }
    }

    private fun isGuardActive(): Boolean = GuardRuntime.isAuthorized() && lastResult.phase in setOf(
        "INITIALIZING", "COMMITTED", "EXTENDED", "STARTING", "RESTORING", "IDLE", "WAIT_OFF", "WAIT_SWITCH"
    )

    private fun refreshConnectionAndHardware() {
        val connected = try { Shizuku.pingBinder() } catch (_: Exception) { false }
        val authorized = connected && GuardRuntime.isAuthorized()
        tvShizukuStatus.setText(
            when {
                !connected -> R.string.shizuku_not_running
                !authorized -> R.string.shizuku_permission_needed
                else -> R.string.shizuku_authorized
            }
        )
        tvShizukuStatus.setTextColor(ContextCompat.getColor(this, if (authorized) R.color.accent_green else R.color.accent_red))
        btnGrantShizuku.visibility = if (connected && !authorized) View.VISIBLE else View.GONE
        btnOpenShizuku.visibility = if (authorized) View.GONE else View.VISIBLE
        val inkState = if (authorized) lastResult.nativeInkState else null
        val physical = if (authorized) lastResult.physical else "UNKNOWN"
        val physicalText = getString(when (physical) {
            "ON" -> R.string.switch_ink
            "OFF" -> R.string.switch_normal
            else -> R.string.state_unknown
        })
        val modeText = getString(when (inkState) {
            2 -> R.string.mode_max_ink
            1 -> R.string.mode_ink_paper
            0 -> R.string.mode_color
            else -> R.string.state_unknown
        })
        tvHardwareState.text = getString(R.string.hardware_state, physicalText, modeText)

        val active = isGuardActive()
        val wanted = GuardRuntime.desired(this)
        val exitPending = authorized && lastResult.exitPending
        tvServiceStatus.text = when {
            currentAction == GuardRuntime.Action.START -> getString(R.string.guard_starting)
            currentAction == GuardRuntime.Action.STOP && !exitPending -> getString(R.string.guard_requesting_stop)
            currentAction == GuardRuntime.Action.CANCEL_STOP -> getString(R.string.guard_cancelling_stop)
            !authorized -> getString(if (wanted) R.string.guard_waiting_shizuku else R.string.guard_unverified)
            lastResult.phase == "RESTORING" -> getString(R.string.guard_restoring)
            exitPending -> getString(R.string.guard_stop_countdown,
                formatCountdown(lastResult.exitRemaining, resources.configuration.locales[0]))
            lastResult.phase == "COMMITTED" -> {
                val remaining = lastResult.remaining.coerceAtLeast(0)
                getString(R.string.guard_committed, formatCountdown(remaining, resources.configuration.locales[0]))
            }
            lastResult.phase == "EXTENDED" -> getString(R.string.guard_extended)
            lastResult.phase == "STARTING" -> getString(R.string.guard_entering_ink)
            lastResult.phase == "INITIALIZING" -> getString(R.string.guard_starting)
            lastResult.phase == "IDLE" -> getString(R.string.guard_ready)
            lastResult.phase == "WAIT_OFF" -> getString(R.string.guard_wait_off)
            lastResult.phase == "WAIT_SWITCH" -> getString(R.string.guard_wait_switch)
            lastResult.phase == "UPDATE_REQUIRED" -> getString(R.string.guard_update_required)
            lastResult.phase == "ERROR" -> getString(R.string.guard_error)
            currentAction == GuardRuntime.Action.STATUS -> getString(R.string.guard_checking)
            else -> getString(if (wanted) R.string.guard_stopped_retry else R.string.guard_stopped)
        }
        tvServiceStatus.textSize = if (exitPending || lastResult.phase == "COMMITTED") 28f else 18f
        tvServiceStatus.setTextColor(ContextCompat.getColor(this, when {
            exitPending -> R.color.accent_gold
            active -> R.color.accent_green
            else -> R.color.gray_text
        }))
        tvCommitmentRemaining.visibility = if (exitPending) View.VISIBLE else View.GONE
        tvCommitmentRemaining.text = if (lastResult.phase == "COMMITTED") {
            getString(R.string.guard_commitment_remaining,
                formatCountdown(lastResult.remaining, resources.configuration.locales[0]))
        } else getString(R.string.guard_entering_ink)
        val error = lastResult.error ?: actionError
        tvGuardError.text = error
        tvGuardError.visibility = if (error.isNullOrBlank()) View.GONE else View.VISIBLE
        val stopping = active || (!authorized && wanted)
        btnToggleService.setText(when {
            exitPending -> R.string.btn_stop_pending
            stopping -> R.string.btn_stop_service
            wanted -> R.string.btn_retry_service
            else -> R.string.btn_start_service
        })
        btnToggleService.backgroundTintList = ContextCompat.getColorStateList(this, if (stopping) R.color.accent_red else R.color.accent_blue)
        btnToggleService.setTextColor(ContextCompat.getColor(this, if (stopping) R.color.white else R.color.gray_dark))
        btnToggleService.isEnabled = (hasStatusResult || stopping) && !exitPending && lastResult.phase != "RESTORING" &&
            (authorized || wanted) && (!actionInFlight || currentAction == GuardRuntime.Action.STATUS ||
            (stopping && currentAction !in setOf(GuardRuntime.Action.STOP, GuardRuntime.Action.CANCEL_STOP)))
        btnCancelResume.setText(if (exitPending) R.string.btn_continue_commitment else R.string.btn_cancel_resume)
        btnCancelResume.visibility = if (exitPending || (authorized && wanted && !active &&
            lastResult.phase != "UPDATE_REQUIRED")) View.VISIBLE else View.GONE
        btnCancelResume.isEnabled = (!actionInFlight || currentAction == GuardRuntime.Action.STATUS) &&
            (!exitPending || lastResult.exitRemaining > 0)
        findViewById<View>(R.id.tvExitPolicy).visibility = if (exitPending || lastResult.phase == "RESTORING") View.GONE else View.VISIBLE
        findViewById<Button>(R.id.btnLanguage).isEnabled = !actionInFlight || currentAction == GuardRuntime.Action.STATUS
        refreshDurationControls(authorized)
        val testsAllowed = authorized && hasStatusResult && !wanted && lastResult.phase == "STOPPED" &&
            (!actionInFlight || currentAction == GuardRuntime.Action.STATUS)
        btnTestInk.isEnabled = testsAllowed
        btnTestNormal.isEnabled = testsAllowed
        findViewById<Button>(R.id.btnCheckCompatibility).apply {
            isEnabled = !diagnosisInFlight
            setText(if (diagnosisInFlight) R.string.compatibility_checking else R.string.btn_check_compatibility)
        }
    }

    private fun showCompatibility() {
        if (diagnosisInFlight) return
        diagnosisInFlight = true
        refreshConnectionAndHardware()
        GuardRuntime.diagnoseAsync(this) { report ->
            if (isFinishing || isDestroyed) return@diagnoseAsync
            diagnosisInFlight = false
            refreshConnectionAndHardware()
            val message = getString(when (report.verdict) {
                GuardCompatibility.Verdict.VERIFIED -> R.string.compatibility_verified
                GuardCompatibility.Verdict.UNVERIFIED_BUILD -> R.string.compatibility_unverified
                GuardCompatibility.Verdict.PRIVILEGE_UNAVAILABLE -> R.string.compatibility_privilege
                GuardCompatibility.Verdict.CAPABILITY_MISSING -> if (report.reason == "NATIVE_PRESET_MISMATCH") {
                    R.string.error_preset
                } else R.string.compatibility_missing
            }) + if (report.controllerUpdateRequired) "\n\n" + getString(R.string.compatibility_controller_update) else ""
            AlertDialog.Builder(this)
                .setTitle(R.string.compatibility_title)
                .setMessage(message)
                .setPositiveButton(R.string.btn_close, null)
                .show()
        }
    }

    private fun openShizuku() {
        val launch = packageManager.getLaunchIntentForPackage(SHIZUKU_PACKAGE)
        if (launch == null) {
            Toast.makeText(this, R.string.shizuku_missing, Toast.LENGTH_LONG).show()
        } else {
            startActivity(launch)
        }
    }

    private fun showShizukuHelp() {
        AlertDialog.Builder(this)
            .setTitle(R.string.shizuku_help_title)
            .setMessage(R.string.shizuku_help_message)
            .setPositiveButton(R.string.btn_open_shizuku) { _, _ -> openShizuku() }
            .setNeutralButton(R.string.btn_restart_help) { _, _ -> showRecoveryHelp() }
            .setNegativeButton(R.string.btn_close, null)
            .show()
    }

    private fun showRecoveryHelp() {
        AlertDialog.Builder(this)
            .setTitle(R.string.restart_help_title)
            .setMessage(R.string.restart_help_message)
            .setPositiveButton(R.string.btn_open_shizuku) { _, _ -> openShizuku() }
            .setNeutralButton(R.string.btn_developer_settings) { _, _ ->
                try {
                    startActivity(Intent(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS))
                } catch (_: Exception) {
                    Toast.makeText(this, R.string.developer_settings_unavailable, Toast.LENGTH_LONG).show()
                }
            }
            .setNegativeButton(R.string.btn_close, null)
            .show()
    }

    private fun showExplanation(title: Int, message: Int) {
        AlertDialog.Builder(this)
            .setTitle(title)
            .setMessage(message)
            .setPositiveButton(R.string.btn_close, null)
            .show()
    }

    private fun configureLanguageSelector() {
        val arabic = resources.configuration.locales[0].language == "ar"
        findViewById<Button>(R.id.btnLanguage).apply {
            setText(if (arabic) R.string.language_english else R.string.language_arabic)
            setOnClickListener { setLanguage(if (arabic) "en" else "ar") }
        }
    }

    private fun commitmentDuration(): Long = lastResult.sessionDuration.takeIf { it > 0 } ?: lastResult.nextDuration

    private fun localizedNumber(value: Long): String =
        NumberFormat.getIntegerInstance(resources.configuration.locales[0]).format(value)

    private fun durationLabel(duration: Long): String = if (duration < 3600) {
        getString(R.string.duration_minutes, localizedNumber(duration / 60))
    } else {
        val hours = (duration / 3600).toInt()
        resources.getQuantityString(R.plurals.duration_hours, hours, localizedNumber(hours.toLong()))
    }

    private fun refreshDurationControls(authorized: Boolean) {
        val locked = lastResult.phase !in setOf("STOPPED", "WAIT_SWITCH", "WAIT_OFF", "IDLE")
        findViewById<Button>(R.id.btnGuardHelp).isEnabled = lastResult.phase !in setOf("STARTING", "INITIALIZING")
        findViewById<TextView>(R.id.tvCommitmentTitle).text = if (lastResult.phase in setOf("STARTING", "INITIALIZING")) {
            getString(R.string.guard_card_title)
        } else getString(R.string.commitment_duration, durationLabel(commitmentDuration()))
        findViewById<TextView>(R.id.tvDurationNote).setText(if (locked) R.string.duration_locked else R.string.duration_next_session)
        val displayedDuration = when (lastResult.phase) {
            "STARTING", "INITIALIZING" -> null
            "COMMITTED", "EXTENDED", "RESTORING" -> lastResult.sessionDuration.takeIf { it > 0 }
            else -> lastResult.nextDuration
        }
        for ((duration, button) in durationButtons) {
            val selected = displayedDuration == duration
            button.isSelected = selected
            button.isEnabled = authorized && hasStatusResult && !locked && (!actionInFlight || currentAction == GuardRuntime.Action.STATUS)
            val border = if (selected) R.color.accent_gold else R.color.gray_border
            button.strokeColor = ContextCompat.getColorStateList(this, border)
            button.strokeWidth = if (selected) 2 * resources.displayMetrics.density.toInt().coerceAtLeast(1) else 1
            button.backgroundTintList = ColorStateList.valueOf(ContextCompat.getColor(this, if (selected) R.color.duration_selected else R.color.gray_card))
            button.setTextColor(ContextCompat.getColor(this, if (selected) R.color.accent_gold else R.color.accent_blue))
        }
    }

    private fun setLanguage(language: String) {
        // AppCompat stores the explicit choice and recreates only this Activity.
        // GuardRuntime and the existing reading session continue untouched.
        AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(language))
    }

    private fun offerRestartReminders() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) return
        val preferences = getSharedPreferences("guard_ui", MODE_PRIVATE)
        if (preferences.getBoolean("reminder_offer_shown", false)) return
        preferences.edit().putBoolean("reminder_offer_shown", true).apply()
        AlertDialog.Builder(this)
            .setTitle(R.string.reminder_title)
            .setMessage(R.string.reminder_explanation)
            .setPositiveButton(R.string.allow_reminders) { _, _ ->
                notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
            .setNegativeButton(R.string.skip_reminders, null)
            .show()
    }

    companion object {
        private const val SHIZUKU_PERMISSION_REQUEST = 1001
        private const val SHIZUKU_PACKAGE = "moe.shizuku.privileged.api"
        private val VERIFIED_PHASES = setOf(
            "INITIALIZING", "COMMITTED", "EXTENDED", "STARTING", "RESTORING", "IDLE", "WAIT_OFF", "WAIT_SWITCH", "STOPPED"
        )
    }
}
