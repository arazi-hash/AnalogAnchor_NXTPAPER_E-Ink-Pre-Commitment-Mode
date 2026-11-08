package com.analoganchor.nxtpaperguard

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.ColorStateList
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
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
import androidx.core.net.toUri
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
    private var setupInFlight = false
    private val setupCommands = SetupCommandQueue()
    private var setupSnapshot = GuardRuntime.SetupSnapshot()
    private lateinit var setupGuidePolicy: SetupGuidePolicy
    private var setupGuideDialog: AlertDialog? = null
    private var setupDetailsExpanded = false
    private var setupWasQualified: Boolean? = null
    private var nextResumeStartsVisit = false

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
            if (GuardRuntime.isAuthorized() && !setupInFlight && !diagnosisInFlight) {
                runSetup(if (setupSnapshot.assessment == null) GuardRuntime.SetupAction.CHECK else GuardRuntime.SetupAction.STATUS)
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
        setupGuidePolicy = SetupGuidePolicy(SetupGuidePolicy.restoreHandled(
            savedInstanceState?.getBoolean("setup_guide_handled") ?: false,
            savedInstanceState?.getString("setup_guide_visit"), guideVisitToken()))
        setupDetailsExpanded = savedInstanceState?.getBoolean("setup_details_expanded") ?: false

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

        var versionTapCount = 0
        var lastVersionTapTime = 0L
        findViewById<TextView>(R.id.tvVersion).apply {
            text = getString(R.string.version_label, BuildConfig.VERSION_NAME)
            setOnClickListener {
                val now = SystemClock.uptimeMillis()
                if (now - lastVersionTapTime < 800) {
                    versionTapCount++
                    if (versionTapCount >= 5) {
                        versionTapCount = 0
                        val tests = findViewById<View>(R.id.layoutTests)
                        val show = tests.visibility != View.VISIBLE
                        tests.visibility = if (show) View.VISIBLE else View.GONE
                        Toast.makeText(
                            this@MainActivity,
                            if (show) R.string.diagnostics_unlocked else R.string.hide_mode_tests,
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                } else {
                    versionTapCount = 1
                }
                lastVersionTapTime = now
            }
        }
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
        findViewById<Button>(R.id.btnSetup).setOnClickListener { advanceSetup() }
        findViewById<Button>(R.id.btnCancelSetup).setOnClickListener { runSetup(GuardRuntime.SetupAction.ABORT) }
        findViewById<Button>(R.id.btnRecoverAfterRestart).setOnClickListener {
            AlertDialog.Builder(this).setTitle(R.string.setup_recover).setMessage(R.string.setup_recover_explanation)
                .setPositiveButton(R.string.setup_recover) { _, _ -> runSetup(GuardRuntime.SetupAction.RECOVER) }
                .setNegativeButton(R.string.btn_close, null).show()
        }
        findViewById<Button>(R.id.btnCompatibilityReport).setOnClickListener { showReport() }
        findViewById<Button>(R.id.btnToggleSetupDetails).setOnClickListener {
            setupDetailsExpanded = !setupDetailsExpanded
            refreshSetup(GuardRuntime.isAuthorized())
        }
        findViewById<Button>(R.id.btnReadSetupGuide).setOnClickListener { showSetupGuide() }
        findViewById<Button>(R.id.btnWebsite).setOnClickListener {
            val language = if (resources.configuration.locales[0].language == "ar") "ar" else "en"
            val website = "https://${getString(R.string.website_url)}/?lang=$language"
            val intent = Intent(Intent.ACTION_VIEW, website.toUri()).apply {
                addCategory(Intent.CATEGORY_BROWSABLE)
            }
            try {
                startActivity(intent)
            } catch (e: ActivityNotFoundException) {
                Toast.makeText(this, R.string.website_url, Toast.LENGTH_SHORT).show()
            }
        }

        Shizuku.addRequestPermissionResultListener(permissionListener)
        Shizuku.addBinderDeadListener(binderDeadListener)
        Shizuku.addBinderReceivedListenerSticky(binderReceivedListener)
    }

    override fun onResume() {
        super.onResume()
        if (nextResumeStartsVisit) {
            setupGuidePolicy.beginVisit()
            nextResumeStartsVisit = false
        }
        visible = true
        if (GuardRuntime.isAuthorized()) runSetup(GuardRuntime.SetupAction.CHECK)
        mainHandler.removeCallbacks(poll)
        poll.run()
    }

    override fun onPause() {
        visible = false
        mainHandler.removeCallbacks(poll)
        super.onPause()
    }

    override fun onStop() {
        if (!isChangingConfigurations) {
            nextResumeStartsVisit = true
            setupGuidePolicy.beginVisit()
            guideVisitGeneration++
        }
        setupGuideDialog?.dismiss()
        super.onStop()
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putBoolean("setup_guide_handled", setupGuidePolicy.handledThisVisit)
        outState.putString("setup_guide_visit", guideVisitToken())
        outState.putBoolean("setup_details_expanded", setupDetailsExpanded)
        super.onSaveInstanceState(outState)
    }

    override fun onDestroy() {
        setupGuideDialog?.dismiss()
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
            (stopping && currentAction !in setOf(GuardRuntime.Action.STOP, GuardRuntime.Action.CANCEL_STOP))) &&
            (stopping || setupSnapshot.qualified) && !setupSnapshot.trial.active
        btnCancelResume.setText(if (exitPending) R.string.btn_continue_commitment else R.string.btn_cancel_resume)
        btnCancelResume.visibility = if (exitPending || (authorized && wanted && !active &&
            lastResult.phase != "UPDATE_REQUIRED")) View.VISIBLE else View.GONE
        btnCancelResume.isEnabled = (!actionInFlight || currentAction == GuardRuntime.Action.STATUS) &&
            (!exitPending || lastResult.exitRemaining > 0)
        findViewById<View>(R.id.tvExitPolicy).visibility = if (exitPending || lastResult.phase == "RESTORING") View.GONE else View.VISIBLE
        findViewById<Button>(R.id.btnLanguage).isEnabled = !actionInFlight || currentAction == GuardRuntime.Action.STATUS
        refreshDurationControls(authorized)
        val testsAllowed = authorized && setupSnapshot.qualified && !setupSnapshot.trial.active && hasStatusResult && !wanted && lastResult.phase == "STOPPED" &&
            (!actionInFlight || currentAction == GuardRuntime.Action.STATUS)
        btnTestInk.isEnabled = testsAllowed
        btnTestNormal.isEnabled = testsAllowed
        findViewById<Button>(R.id.btnCheckCompatibility).apply {
            isEnabled = !diagnosisInFlight
            setText(if (diagnosisInFlight) R.string.compatibility_checking else R.string.btn_check_compatibility)
        }
        refreshSetup(authorized)
    }

    private fun runSetup(action: GuardRuntime.SetupAction) {
        val next = setupCommands.request(action) ?: return
        dispatchSetup(next)
    }

    private fun dispatchSetup(action: GuardRuntime.SetupAction) {
        setupInFlight = true
        if (!isFinishing && !isDestroyed) refreshSetup(GuardRuntime.isAuthorized())
        GuardRuntime.setupAsync(this, action) { snapshot ->
            setupSnapshot = snapshot
            setupInFlight = false
            val next = setupCommands.finished()
            // Owner intent outlives the Activity just as the independent trial does.
            if (next != null) dispatchSetup(next)
            else if (!isFinishing && !isDestroyed) refreshConnectionAndHardware()
        }
    }

    private fun advanceSetup() {
        val trial = setupSnapshot.trial
        when {
            trial.phase == "WAIT_OWNER_CONFIRM" -> AlertDialog.Builder(this)
                .setTitle(R.string.setup_native_confirm_title).setMessage(R.string.setup_native_confirm)
                .setPositiveButton(R.string.setup_confirm_native) { _, _ -> runSetup(GuardRuntime.SetupAction.CONFIRM_NATIVE) }
                .setNegativeButton(R.string.btn_close, null).show()
            trial.phase == "PASSED" -> AlertDialog.Builder(this)
                .setTitle(R.string.setup_restored_title).setMessage(R.string.setup_restored_confirm)
                .setPositiveButton(R.string.setup_confirm_normal) { _, _ -> runSetup(GuardRuntime.SetupAction.QUALIFY) }
                .setNegativeButton(R.string.btn_close, null).show()
            setupSnapshot.assessment?.eligible == true && !setupSnapshot.qualified -> AlertDialog.Builder(this)
                .setTitle(R.string.setup_title).setMessage(R.string.setup_consent)
                .setPositiveButton(R.string.setup_begin) { _, _ -> runSetup(GuardRuntime.SetupAction.START) }
                .setNegativeButton(R.string.btn_close, null).show()
            else -> runSetup(GuardRuntime.SetupAction.CHECK)
        }
    }

    private fun refreshSetup(authorized: Boolean) {
        val snapshot = setupSnapshot
        val phase = snapshot.trial.phase
        val ownerBusy = setupCommands.ownerWorkPending
        val trialNeedsAttention = snapshot.trial.active || phase == "PASSED"
        if (snapshot.assessment != null) {
            if (snapshot.qualified && setupWasQualified != true) setupDetailsExpanded = false
            setupWasQualified = snapshot.qualified
        }
        if (trialNeedsAttention) setupDetailsExpanded = true
        findViewById<View>(R.id.layoutSetupDetails).visibility = if (setupDetailsExpanded) View.VISIBLE else View.GONE
        findViewById<TextView>(R.id.tvSetupSummary).setText(when {
            !authorized -> R.string.setup_summary_connect
            trialNeedsAttention -> R.string.setup_summary_testing
            snapshot.qualified -> R.string.setup_summary_ready
            phase in setOf("FAILED", "UNKNOWN") || snapshot.error != null -> R.string.setup_summary_attention
            snapshot.assessment?.level == SupportAssessment.Level.UNSUPPORTED -> R.string.setup_summary_attention
            snapshot.assessment?.level == SupportAssessment.Level.EXPERIMENTAL_ELIGIBLE -> R.string.setup_summary_experimental
            snapshot.assessment == null -> R.string.setup_summary_checking
            else -> R.string.setup_summary_required
        })
        findViewById<Button>(R.id.btnToggleSetupDetails).apply {
            setText(if (trialNeedsAttention) R.string.setup_summary_testing else if (setupDetailsExpanded) R.string.setup_hide_details else R.string.setup_show_details)
            isEnabled = !trialNeedsAttention
        }
        findViewById<TextView>(R.id.tvSetupStatus).text = getString(when {
            !authorized -> SetupGuidance.reasonResource(if (reportAccess() == CompatibilityReport.Access.PERMISSION_REQUIRED)
                "SHIZUKU_PERMISSION_REQUIRED" else "SHIZUKU_NOT_RUNNING")
            lastResult.phase == "UPDATE_REQUIRED" -> R.string.setup_busy
            snapshot.controllerPresent -> R.string.setup_busy
            snapshot.errorReason != null -> SetupGuidance.reasonResource(snapshot.errorReason)
            phase in setOf("FAILED", "UNKNOWN", "ABORTED") -> SetupGuidance.reasonResource(snapshot.trial.reason.ifEmpty {
                if (phase == "ABORTED") "CANCELLED" else "SETUP_INCOMPLETE"
            })
            snapshot.qualified -> R.string.setup_complete
            snapshot.assessment?.level == SupportAssessment.Level.MAINTAINER_TESTED -> R.string.setup_tested
            snapshot.assessment?.level == SupportAssessment.Level.EXPERIMENTAL_ELIGIBLE -> R.string.setup_experimental
            snapshot.assessment != null -> SetupGuidance.reasonResource(snapshot.assessment.reason)
            else -> R.string.setup_required
        })
        findViewById<TextView>(R.id.tvSetupInstructions).setText(when (phase) {
            "INITIALIZING" -> R.string.setup_initializing
            "WAIT_NORMAL" -> R.string.setup_wait_normal
            "WAIT_PHYSICAL_INK" -> R.string.setup_wait_ink
            "WAIT_PHYSICAL_NORMAL" -> R.string.setup_wait_return
            "WAIT_OWNER_CONFIRM" -> R.string.setup_owner_step
            "WAIT_EXIT_INK" -> R.string.setup_wait_exit_ink
            "EXIT_TEST" -> R.string.setup_exit_test
            "WAIT_EXIT_NORMAL" -> R.string.setup_wait_exit_normal
            "ENTER_TEST", "RESTORE_TEST" -> R.string.setup_software_test
            "PASSED" -> R.string.setup_passed
            "ABORTING" -> R.string.setup_aborting
            "ABORTED" -> R.string.setup_aborted
            "FAILED", "UNKNOWN" -> R.string.setup_failed
            "QUALIFIED" -> if (snapshot.qualified) R.string.setup_complete_detail else R.string.setup_intro
            else -> if (snapshot.qualified) R.string.setup_complete_detail else R.string.setup_intro
        })
        findViewById<Button>(R.id.btnSetup).apply {
            setText(when {
                ownerBusy -> R.string.compatibility_checking
                phase == "WAIT_OWNER_CONFIRM" -> R.string.setup_confirm_native
                phase == "PASSED" -> R.string.setup_confirm_normal
                snapshot.assessment?.eligible == true && !snapshot.qualified -> R.string.setup_begin
                else -> R.string.setup_check
            })
            isEnabled = authorized && !ownerBusy && (!actionInFlight || currentAction == GuardRuntime.Action.STATUS) && !snapshot.controllerPresent &&
                lastResult.phase != "UPDATE_REQUIRED" && (!snapshot.trial.active || phase == "WAIT_OWNER_CONFIRM")
        }
        findViewById<Button>(R.id.btnCancelSetup).apply {
            visibility = if (snapshot.trial.active || phase == "PASSED") View.VISIBLE else View.GONE
            isEnabled = authorized && !setupCommands.cancelling && phase != "ABORTING"
        }
        findViewById<Button>(R.id.btnCompatibilityReport).isEnabled = true
        findViewById<Button>(R.id.btnRecoverAfterRestart).apply {
            visibility = if ((snapshot.controllerPresent && !isGuardActive()) || lastResult.phase == "UPDATE_REQUIRED") View.VISIBLE else View.GONE
            isEnabled = authorized && !ownerBusy && (!actionInFlight || currentAction == GuardRuntime.Action.STATUS)
        }
        findViewById<Button>(R.id.btnReadSetupGuide).isEnabled = !guideIsBlocked()
        maybeShowSetupGuide(authorized)
    }

    private fun setupGuideKey(): String = SetupGuidePolicy.acknowledgementKey(
        Build.FINGERPRINT, setupSnapshot.assessment?.binding?.digest)

    private fun guideVisitToken(): String = "$GUIDE_PROCESS_TOKEN:$guideVisitGeneration"

    private fun guideIsBlocked(): Boolean = setupCommands.ownerWorkPending || diagnosisInFlight ||
        (actionInFlight && currentAction != GuardRuntime.Action.STATUS) ||
        setupSnapshot.trial.active || setupSnapshot.trial.phase == "PASSED" ||
        setupSnapshot.controllerPresent || isGuardActive() || GuardRuntime.desired(this) || lastResult.phase == "UPDATE_REQUIRED"

    private fun maybeShowSetupGuide(authorized: Boolean) {
        if (!visible || isFinishing || isDestroyed) return
        val blocked = guideIsBlocked()
        if (blocked) { setupGuideDialog?.dismiss(); return }
        if (!hasWindowFocus()) return
        if (authorized && (setupSnapshot.assessment == null || !hasStatusResult)) return
        val acknowledged = getSharedPreferences("setup_guide", MODE_PRIVATE).getString("acknowledged_key", null)
        if (setupGuideDialog?.isShowing != true && setupGuidePolicy.shouldShow(!setupSnapshot.qualified, blocked, setupGuideKey(), acknowledged)) {
            showSetupGuide()
        }
    }

    private fun showSetupGuide() {
        if (isFinishing || isDestroyed || setupGuideDialog?.isShowing == true || guideIsBlocked()) return
        val key = setupGuideKey()
        setupGuidePolicy.shown()
        fun acknowledge() {
            getSharedPreferences("setup_guide", MODE_PRIVATE).edit().putString("acknowledged_key", key).apply()
        }
        setupGuideDialog = AlertDialog.Builder(this)
            .setTitle(R.string.setup_title)
            .setMessage(findViewById<TextView>(R.id.tvSetupStatus).text.toString() + "\n\n" +
                getString(if (setupSnapshot.qualified) R.string.setup_complete_detail else R.string.setup_popup_message))
            .setPositiveButton(if (GuardRuntime.isAuthorized()) R.string.setup_open_details else R.string.setup_connect_action) { _, _ ->
                acknowledge()
                setupDetailsExpanded = true
                refreshSetup(GuardRuntime.isAuthorized())
                if (!GuardRuntime.isAuthorized()) requestShizukuPermission()
            }
            .setNeutralButton(R.string.setup_got_it) { _, _ ->
                acknowledge()
                setupDetailsExpanded = false
                refreshSetup(GuardRuntime.isAuthorized())
            }
            .setNegativeButton(R.string.setup_later, null)
            .create().also { dialog ->
                dialog.setOnDismissListener { setupGuideDialog = null }
                dialog.show()
            }
    }

    private fun showReport(assessment: SupportAssessment? = setupSnapshot.assessment,
                           assessmentObservedAt: Long? = setupSnapshot.assessmentObservedAt,
                           observationError: String? = setupSnapshot.errorReason) {
        val snapshot = setupSnapshot
        val now = SystemClock.elapsedRealtime()
        val report = CompatibilityReport(
            appVersion = BuildConfig.VERSION_NAME, appVersionCode = BuildConfig.VERSION_CODE,
            deviceFacts = mapOf("model" to Build.MODEL, "device" to Build.DEVICE,
                "android" to Build.VERSION.RELEASE, "sdk" to Build.VERSION.SDK_INT.toString(),
                "fingerprint" to Build.FINGERPRINT, "build_display" to Build.DISPLAY,
                "security_patch" to Build.VERSION.SECURITY_PATCH),
            access = reportAccess(), assessment = assessment,
            trial = snapshot.trial.takeIf { snapshot.observedAt != null }, qualified = snapshot.qualified,
            controllerPresent = snapshot.controllerPresent.takeIf { snapshot.observedAt != null && snapshot.error == null },
            assessmentAgeSeconds = assessmentObservedAt?.let { (now - it).coerceAtLeast(0) / 1000 },
            setupAgeSeconds = snapshot.observedAt?.let { (now - it).coerceAtLeast(0) / 1000 },
            observationError = observationError
        ).render()
        val content = layoutInflater.inflate(R.layout.dialog_compatibility_report, null)
        content.findViewById<TextView>(R.id.tvReportContent).text = report
        content.findViewById<Button>(R.id.btnCopyReport).setOnClickListener {
            val copied = runCatching {
                getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText(getString(R.string.setup_report), report))
            }.isSuccess
            Toast.makeText(this, if (copied) R.string.report_copied else R.string.report_copy_failed, Toast.LENGTH_SHORT).show()
        }
        content.findViewById<Button>(R.id.btnShareReport).setOnClickListener {
            try {
                val send = Intent(Intent.ACTION_SEND).setType("text/plain")
                    .putExtra(Intent.EXTRA_TEXT, report).putExtra(Intent.EXTRA_SUBJECT, getString(R.string.setup_report))
                startActivity(Intent.createChooser(send, getString(R.string.setup_share)))
            } catch (_: ActivityNotFoundException) {
                Toast.makeText(this, R.string.report_no_share, Toast.LENGTH_LONG).show()
            } catch (_: SecurityException) {
                Toast.makeText(this, R.string.report_no_share, Toast.LENGTH_LONG).show()
            }
        }
        content.findViewById<Button>(R.id.btnOpenReportForm).setOnClickListener {
            try {
                startActivity(Intent(Intent.ACTION_VIEW, CompatibilityReport.ISSUE_FORM_URL.toUri()))
            } catch (_: ActivityNotFoundException) {
                Toast.makeText(this, R.string.report_no_browser, Toast.LENGTH_LONG).show()
            } catch (_: SecurityException) {
                Toast.makeText(this, R.string.report_no_browser, Toast.LENGTH_LONG).show()
            }
        }
        AlertDialog.Builder(this).setTitle(R.string.setup_report).setView(content)
            .setNegativeButton(R.string.btn_close, null).show()
    }

    private fun reportAccess(): CompatibilityReport.Access = try {
        when {
            !Shizuku.pingBinder() -> CompatibilityReport.Access.NOT_RUNNING
            Shizuku.checkSelfPermission() != PackageManager.PERMISSION_GRANTED -> CompatibilityReport.Access.PERMISSION_REQUIRED
            else -> CompatibilityReport.Access.AUTHORIZED
        }
    } catch (_: Exception) { CompatibilityReport.Access.NOT_RUNNING }

    private fun showCompatibility() {
        if (diagnosisInFlight) return
        diagnosisInFlight = true
        refreshConnectionAndHardware()
        GuardRuntime.diagnoseAsync(this) { report, assessment, assessmentObservedAt ->
            if (isFinishing || isDestroyed) return@diagnoseAsync
            diagnosisInFlight = false
            refreshConnectionAndHardware()
            val message = getString(when {
                report.controllerUpdateRequired -> R.string.setup_busy
                report.verdict == GuardCompatibility.Verdict.VERIFIED -> R.string.compatibility_verified
                report.verdict == GuardCompatibility.Verdict.PRIVILEGE_UNAVAILABLE -> SetupGuidance.reasonResource(
                    if (reportAccess() == CompatibilityReport.Access.PERMISSION_REQUIRED) "SHIZUKU_PERMISSION_REQUIRED" else "SHIZUKU_NOT_RUNNING")
                else -> SetupGuidance.reasonResource(report.reason)
            })
            AlertDialog.Builder(this)
                .setTitle(R.string.compatibility_title)
                .setMessage(message)
                .setNeutralButton(R.string.setup_report) { _, _ ->
                    val error = when {
                        report.controllerUpdateRequired -> "LIVE_CONTROLLER_PRESENT"
                        report.verdict != GuardCompatibility.Verdict.VERIFIED -> report.reason
                        else -> null
                    }
                    showReport(assessment, assessmentObservedAt, error)
                }
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
            button.isEnabled = authorized && hasStatusResult && !locked && !setupSnapshot.trial.active &&
                (setupSnapshot.qualified || isGuardActive()) && (!actionInFlight || currentAction == GuardRuntime.Action.STATUS)
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
        private val GUIDE_PROCESS_TOKEN = java.util.UUID.randomUUID().toString()
        private var guideVisitGeneration = 0L
        private const val SHIZUKU_PERMISSION_REQUEST = 1001
        private const val SHIZUKU_PACKAGE = "moe.shizuku.privileged.api"
        private val VERIFIED_PHASES = setOf(
            "INITIALIZING", "COMMITTED", "EXTENDED", "STARTING", "RESTORING", "IDLE", "WAIT_OFF", "WAIT_SWITCH", "STOPPED"
        )
    }
}
