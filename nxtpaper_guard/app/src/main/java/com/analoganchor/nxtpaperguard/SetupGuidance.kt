package com.analoganchor.nxtpaperguard

/** Presentation only. These explanations never grant device qualification. */
object SetupGuidance {
    fun reasonResource(reason: String): Int = when (reason) {
        "SHIZUKU_UNAVAILABLE", "SHIZUKU_NOT_RUNNING" -> R.string.setup_access_unavailable
        "SHIZUKU_PERMISSION_REQUIRED", "PERMISSION_REQUIRED", "AUTHORIZATION_REQUIRED" -> R.string.setup_access_permission
        "NOT_CHECKED" -> R.string.setup_not_checked
        "SETUP_REQUIRED" -> R.string.setup_required
        "VERIFIED", "COMMAND_SENT" -> R.string.compatibility_verified
        "SLIDER_PROTOCOL_UNAVAILABLE" -> R.string.setup_slider_unrecognized
        "PUSH_BUTTON_PROTOCOL_UNSUPPORTED" -> R.string.setup_push_button
        "PHYSICAL_INPUT_UNAVAILABLE", "PHYSICAL_MONITOR_FAILED", "PHYSICAL_STATE_INVALID" -> R.string.setup_input_unavailable
        "ACTIVE_LAYOUT_UNAVAILABLE" -> R.string.setup_layout_unavailable
        "SYMBOL_MAPPING_CONFLICT", "SYMBOL_MAPPING_UNAVAILABLE", "INPUT_MAPPING_UNSUPPORTED" -> R.string.setup_mapping_unrecognized
        "NATIVE_PRESET_MISMATCH" -> R.string.error_preset
        "NATIVE_SETTINGS_UNAVAILABLE" -> R.string.setup_native_settings
        "NATIVE_COMPONENT_UNAVAILABLE" -> R.string.setup_native_components
        "LIVE_CONTROLLER_PRESENT", "CONTROLLER_NOT_STOPPED", "OPERATION_BUSY", "OPERATION_LOCK_FAILED",
        "TRIAL_IDENTITY_UNAVAILABLE", "TRIAL_LOCK_UNRECOGNIZED" -> R.string.setup_controller_attention
        "RECOVERY_REFUSED" -> R.string.setup_recovery_refused
        "TEST_TIMED_OUT", "TRANSITION_TIMED_OUT", "NATIVE_COMMAND_TIMEOUT" -> R.string.setup_trial_timeout
        "TRIAL_INTERRUPTED", "TRIAL_UNRESPONSIVE", "TRIAL_STATE_INVALID", "SETUP_INCOMPLETE" -> R.string.setup_trial_interrupted
        "PHYSICAL_SWITCH_MOVED" -> R.string.setup_switch_moved
        "RESTORATION_FAILED", "FINAL_NORMAL_NOT_CONFIRMED", "NATIVE_STATE_READ_FAILED" -> R.string.setup_restore_unconfirmed
        "NATIVE_COMMAND_FAILED" -> R.string.setup_native_command_failed
        "CANCELLED" -> R.string.setup_aborted
        "IDENTITY_UNAVAILABLE", "PROBE_UNAVAILABLE", "INVALID_COMPATIBILITY_REPORT", "CONTROLLER_UNAVAILABLE",
        "REGISTRY_AMBIGUOUS", "BINDING_INVALID", "CLOCK_UNAVAILABLE", "BOOT_ID_UNAVAILABLE",
        "PROCESS_IDENTITY_UNAVAILABLE", "STATE_WRITE_FAILED", "PID_WRITE_FAILED",
        "REQUIRED_TOOL_UNAVAILABLE_TIMEOUT", "INVALID_ACTION" -> R.string.setup_check_unavailable
        else -> R.string.setup_check_unavailable
    }
}
