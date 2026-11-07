#!/system/bin/sh
# Bounded qualification trial. This process outlives the activity; never starts a
# commitment, and never handles a commitment's Stop request.
NXTPAPER_GUARD_SOURCE_ONLY=1
CONTROLLER_SCRIPT_PATH=${NXTPAPER_CONTROLLER_SCRIPT:-/data/local/tmp/nxtpaper_guard.sh}
. "$CONTROLLER_SCRIPT_PATH" || exit 1
NXTPAPER_SETUP_RUNNING=1
GUARD_PID_FILE=$PID_FILE
GUARD_LOCK_DIR=$LOCK_DIR
GUARD_SCRIPT_PATH=$SCRIPT_PATH
BASE=/data/local/tmp/nxtpaper_setup
SCRIPT_PATH=/data/local/tmp/nxtpaper_setup.sh
PID_FILE=$BASE.pid
STATE_FILE=$BASE.state
LOG_FILE=$BASE.log
LOCK_DIR=$BASE.lock
PHYSICAL_FILE=$LOCK_DIR/physical
GETEVENT_PID_FILE=$LOCK_DIR/getevent.pid
READER_PID_FILE=$LOCK_DIR/reader.pid
WRITER_PID_FILE=$LOCK_DIR/writer.pid
MONITOR_ERROR_FILE=$LOCK_DIR/monitor.error
REQUEST_FILE=$BASE.request
ABORT_FILE=$BASE.abort
STATE_TIME_FILE=$BASE.state-time
PHYSICAL_TIMEOUT=120
TRIAL_TOTAL_TIMEOUT=900

setup_init() {
    guard_init
    PHASE=WAIT_NORMAL
    REASON=
    TRIAL_ID=$$-$NOW-1
    TRIAL_STARTED=$NOW
    PHASE_AT=$NOW
    SOFTWARE_SENT=0
    CANCELLED=0
    REQUESTED_FAILURE=
    ISSUED=0
    CONFIRM_SEQ=0
    SETUP_OWN_LOCK=0
}

setup_publish() {
    setup_elapsed=$((NOW - TRIAL_STARTED))
    [ "$setup_elapsed" -ge 0 ] || return 1
    printf '%s:%s:%s:%s:%s\n' "$PHASE" "$REASON" "$setup_elapsed" "$TRIAL_ID" "$PROFILE_BINDING_SHA" > "$STATE_FILE.tmp" &&
        mv "$STATE_FILE.tmp" "$STATE_FILE" || return 1
    printf '%s\n' "$NOW" > "$STATE_TIME_FILE"
}

setup_reply() {
    printf '%s:%s:%s:%s:%s\n' "$1" "$2" "${3:-0}" "${4:-}" "${5:-}"
}

setup_live() {
    guard_live_pid
}

setup_status() {
    if setup_live; then
        guard_clock || { setup_reply FAILED CLOCK_UNAVAILABLE; return; }
        if [ -r "$STATE_TIME_FILE" ] && [ -r "$STATE_FILE" ]; then
            read -r setup_state_at < "$STATE_TIME_FILE"
            case "$setup_state_at" in ''|*[!0-9]*) setup_state_at=0 ;; esac
            if [ "$NOW" -ge "$setup_state_at" ] && [ $((NOW - setup_state_at)) -le 15 ]; then
                cat "$STATE_FILE"; return
            fi
        fi
        setup_reply FAILED TRIAL_UNRESPONSIVE; return
    fi
    if [ -e "$PID_FILE" ] || [ -d "$LOCK_DIR" ]; then
        setup_reply FAILED TRIAL_IDENTITY_UNAVAILABLE; return
    fi
    if [ -r "$STATE_FILE" ]; then
        IFS=: read -r old_phase old_reason old_elapsed old_trial old_binding < "$STATE_FILE"
        case "$old_phase" in
          QUALIFIED|FAILED|ABORTED) cat "$STATE_FILE"; return ;;
          *) setup_reply FAILED TRIAL_INTERRUPTED "$old_elapsed" "$old_trial" "$old_binding"; return ;;
        esac
    fi
    setup_reply STOPPED ''
}

setup_request() {
    setup_live || { setup_status; return 1; }
    IFS=: read -r request_phase request_reason request_elapsed request_trial request_binding < "$STATE_FILE" || return 1
    case "$request_trial" in ''|*[!0-9-]*) setup_reply FAILED TRIAL_STATE_INVALID; return 1 ;; esac
    if [ "$1" = abort ]; then
        printf '%s\n' "$request_trial" > "$ABORT_FILE.tmp" && mv "$ABORT_FILE.tmp" "$ABORT_FILE" || return 1
    else
        case "$1:$request_phase" in confirm-native:WAIT_OWNER_CONFIRM|qualify:PASSED) ;;
          *) setup_status; return 1 ;;
        esac
        printf '%s:%s\n' "$request_trial" "$1" > "$REQUEST_FILE.tmp" && mv "$REQUEST_FILE.tmp" "$REQUEST_FILE" || return 1
    fi
    # The activity needs the acknowledged result, not just a queued request.
    # The independent runner still owns every transition and qualification.
    request_wait=0
    if [ "$1" = abort ]; then request_bound=$((TRANSITION_TIMEOUT + 5)); else request_bound=5; fi
    while [ "$request_wait" -le "$request_bound" ]; do
        if [ -r "$STATE_FILE" ]; then
            IFS=: read -r request_now_phase request_now_reason request_now_elapsed request_now_trial request_now_binding < "$STATE_FILE"
            [ "$request_now_trial" = "$request_trial" ] || break
            case "$1:$request_now_phase" in
              abort:ABORTED|abort:FAILED|qualify:QUALIFIED|qualify:FAILED) break ;;
              confirm-native:WAIT_OWNER_CONFIRM|qualify:PASSED|abort:*) ;;
              confirm-native:*) break ;;
            esac
        fi
        setup_live || break
        sleep 1
        request_wait=$((request_wait + 1))
    done
    setup_status
}

setup_phase() {
    PHASE=$1
    PHASE_AT=$NOW
    ISSUED=0
}

setup_issue() {
    # Fresh identity, layout, native component and privilege checks precede
    # every injected key. Qualification is deliberately not needed for trials.
    case "$1" in "$PROFILE_ENTER_KEY"|"$PROFILE_EXIT_KEY") ;; *) ERROR_CODE=INVALID_NATIVE_COMMAND; return 1 ;; esac
    guard_command_gate || return $?
    guard_clock || { ERROR_CODE=CLOCK_UNAVAILABLE; return 1; }
    # Compatibility probes can be slow. They cannot extend a transition or
    # permit a queued Cancel to be followed by a new entry command.
    [ $((NOW - PHASE_AT)) -lt "$TRANSITION_TIMEOUT" ] || { ERROR_CODE=TRANSITION_TIMED_OUT; return 1; }
    if [ "$PHASE" != ABORTING ] && [ -r "$ABORT_FILE" ]; then
        read -r issue_abort_trial < "$ABORT_FILE"
        if [ "$issue_abort_trial" = "$TRIAL_ID" ]; then setup_restore CANCELLED 1; return 2; fi
    fi
    if timeout 5 input keyevent "$1" >/dev/null 2>&1; then :
    else
        issue_result=$?
        if [ "$issue_result" = 124 ] || [ "$issue_result" = 137 ]; then ERROR_CODE=NATIVE_COMMAND_TIMEOUT
        else ERROR_CODE=NATIVE_COMMAND_DENIED; fi
        return 1
    fi
    SOFTWARE_SENT=1
    ISSUED=1
    NATIVE_SIGNATURE=
    STABLE=0
}

setup_restore() {
    REQUESTED_FAILURE=$1
    CANCELLED=${2:-0}
    setup_phase ABORTING
}

setup_finish_qualification() {
    [ "$PHASE" = PASSED ] && [ "$PHYSICAL" = OFF ] && guard_is_normal || return 1
    guard_command_gate || return 1
    guard_clock && guard_physical_read || return 1
    [ "$PHYSICAL" = OFF ] && guard_is_normal || return 1
    [ $((NOW - PHASE_AT)) -lt "$PHYSICAL_TIMEOUT" ] || return 1
    if [ -r "$ABORT_FILE" ]; then
        read -r qualify_abort_trial < "$ABORT_FILE"
        [ "$qualify_abort_trial" != "$TRIAL_ID" ] || return 1
    fi
    qualification_tmp=$QUALIFICATION_FILE.tmp.$$
    umask 077
    printf 'schema=1\nbinding_sha256=%s\ncontroller_sha256=%s\ntrial_id=%s\nowner_confirmed=1\nresult=passed\n' \
        "$PROFILE_BINDING_SHA" "$PROFILE_CONTROLLER_SHA" "$TRIAL_ID" > "$qualification_tmp" &&
        mv "$qualification_tmp" "$QUALIFICATION_FILE" || return 1
    setup_phase QUALIFIED
}

setup_tick() {
    # Physical proof accepts genuine ordered edges; native desired state alone
    # cannot stand in for the switch position (including TSWT=-1 after boot).
    if [ -r "$ABORT_FILE" ]; then
        read -r request_abort_trial < "$ABORT_FILE"
        if [ "$request_abort_trial" = "$TRIAL_ID" ] && [ "$PHASE" != ABORTING ]; then
            setup_restore CANCELLED 1
        fi
    fi
    if [ -r "$REQUEST_FILE" ]; then
        IFS=: read -r request_trial request_action < "$REQUEST_FILE"
        rm -f "$REQUEST_FILE"
        if [ "$request_trial" = "$TRIAL_ID" ]; then
            case "$request_action:$PHASE" in
              confirm-native:WAIT_OWNER_CONFIRM) CONFIRM_SEQ=$RAW_SEQ; setup_phase WAIT_EXIT_INK ;;
              qualify:PASSED)
                setup_finish_qualification || { setup_restore FINAL_NORMAL_NOT_CONFIRMED; } ;;
            esac
        fi
    fi
    case "$PHASE" in
      WAIT_NORMAL)
        if [ "$PHYSICAL" = OFF ] && [ "$OFF_SEQ" -gt 0 ] && guard_is_normal; then
            NORMAL_SEQ=$RAW_SEQ; setup_phase WAIT_PHYSICAL_INK
        fi ;;
      WAIT_PHYSICAL_INK)
        if [ "$PHYSICAL" = ON ] && [ "$ON_SEQ" -gt "$NORMAL_SEQ" ] && guard_is_ink; then
            INK_SEQ=$RAW_SEQ; setup_phase WAIT_PHYSICAL_NORMAL
        fi ;;
      WAIT_PHYSICAL_NORMAL)
        if [ "$PHYSICAL" = OFF ] && [ "$OFF_SEQ" -gt "$INK_SEQ" ] && guard_is_normal; then
            setup_phase WAIT_OWNER_CONFIRM
        fi ;;
      WAIT_OWNER_CONFIRM) ;;
      WAIT_EXIT_INK)
        if [ "$PHYSICAL" = ON ] && [ "$ON_SEQ" -gt "$CONFIRM_SEQ" ] && guard_is_ink; then
            EXIT_INK_SEQ=$RAW_SEQ; setup_phase EXIT_TEST
        fi ;;
      EXIT_TEST)
        [ "$PHYSICAL" = ON ] || { setup_restore PHYSICAL_SWITCH_MOVED; return; }
        if [ "$ISSUED" = 0 ]; then setup_issue "$PROFILE_EXIT_KEY" || return $?;
        elif guard_is_normal; then setup_phase WAIT_EXIT_NORMAL; fi ;;
      WAIT_EXIT_NORMAL)
        if [ "$PHYSICAL" = OFF ] && [ "$OFF_SEQ" -gt "$EXIT_INK_SEQ" ] && guard_is_normal; then
            setup_phase ENTER_TEST
        fi ;;
      ENTER_TEST)
        [ "$PHYSICAL" = OFF ] || { setup_restore PHYSICAL_SWITCH_MOVED; return; }
        if [ "$ISSUED" = 0 ]; then setup_issue "$PROFILE_ENTER_KEY" || return $?;
        elif guard_is_ink; then setup_phase RESTORE_TEST; fi ;;
      RESTORE_TEST)
        [ "$PHYSICAL" = OFF ] || { setup_restore PHYSICAL_SWITCH_MOVED; return; }
        if [ "$ISSUED" = 0 ]; then setup_issue "$PROFILE_EXIT_KEY" || return $?;
        elif guard_is_normal; then setup_phase PASSED; fi ;;
      PASSED)
        if [ "$PHYSICAL" != OFF ] || ! guard_is_normal; then setup_restore FINAL_NORMAL_NOT_CONFIRMED; fi ;;
      ABORTING)
        if guard_is_normal; then
            if [ "$CANCELLED" = 1 ]; then setup_phase ABORTED; REASON=$REQUESTED_FAILURE
            else setup_phase FAILED; REASON=$REQUESTED_FAILURE; fi
        elif [ "$ISSUED" = 0 ] && [ "$TSWT" != -1 ] && [ "$APPLYING" = 0 ] && [ "$ANIMATION" = 0 ]; then
            setup_issue "$PROFILE_EXIT_KEY" || return $?
        fi ;;
    esac
    case "$PHASE" in
      EXIT_TEST|ENTER_TEST|RESTORE_TEST|ABORTING) setup_bound=$TRANSITION_TIMEOUT ;;
      QUALIFIED|FAILED|ABORTED) return 0 ;;
      *) setup_bound=$PHYSICAL_TIMEOUT ;;
    esac
    if [ $((NOW - PHASE_AT)) -ge "$setup_bound" ] || [ $((NOW - TRIAL_STARTED)) -ge "$TRIAL_TOTAL_TIMEOUT" ]; then
        if [ "$PHASE" = ABORTING ]; then setup_phase FAILED; REASON=RESTORATION_FAILED
        else setup_restore TEST_TIMED_OUT; fi
    fi
}

setup_cleanup() {
    guard_operation_release
    [ "${SETUP_OWN_LOCK:-0}" = 1 ] || return 0
    # These files belong to this identity only; never touch the guard's files.
    guard_monitor_cleanup
    [ -z "${READER_PID:-}" ] || wait "$READER_PID" 2>/dev/null
    rm -f "$PHYSICAL_FILE" "$PHYSICAL_FILE.tmp" "$GETEVENT_PID_FILE" "$GETEVENT_PID_FILE.tmp" \
        "$READER_PID_FILE" "$READER_PID_FILE.tmp" "$WRITER_PID_FILE" "$WRITER_PID_FILE.tmp" "$MONITOR_ERROR_FILE"
    rmdir "$LOCK_DIR" 2>/dev/null
    rm -f "$PID_FILE" "$REQUEST_FILE" "$ABORT_FILE"
    SETUP_OWN_LOCK=0
}

setup_handle_result() {
    case "$1" in 0|2) return 0 ;; esac
    if [ "$PHASE" = ABORTING ] || [ -n "$REQUESTED_FAILURE" ]; then
        setup_phase FAILED
        REASON=${ERROR_CODE:-RESTORATION_FAILED}
    else
        # A failed injection may already have reached Android. Keep this runner
        # alive for the bounded fresh-gated restoration path; never qualify it.
        setup_restore "${ERROR_CODE:-NATIVE_COMMAND_FAILED}"
    fi
}

setup_reset_stale() {
    # Explicit retry only: a valid previous-boot token proves this trial cannot
    # still be restoring Normal. Same-boot and malformed identities survive.
    reset_boot=$(guard_duration_boot) || { setup_reply FAILED BOOT_ID_UNAVAILABLE; return 1; }
    case "$reset_boot" in ''|*[!a-zA-Z0-9-]*) setup_reply FAILED BOOT_ID_UNAVAILABLE; return 1 ;; esac
    guard_operation_recover_previous_boot || { setup_reply FAILED OPERATION_BUSY; return 1; }
    guard_operation_acquire || { setup_reply FAILED OPERATION_BUSY; return 1; }
    if [ -e "$GUARD_PID_FILE" ] || [ -d "$GUARD_LOCK_DIR" ]; then
        guard_operation_release; setup_reply FAILED CONTROLLER_NOT_STOPPED; return 1
    fi
    if [ ! -e "$PID_FILE" ] && [ ! -d "$LOCK_DIR" ]; then
        guard_operation_release; setup_reply STOPPED ''; return 0
    fi
    reset_record=$(cat "$PID_FILE" 2>/dev/null)
    if ! printf '%s\n' "$reset_record" | grep -Eq '^[1-9][0-9]*:[0-9]+:[a-zA-Z0-9-]+$'; then
        guard_operation_release; setup_reply FAILED TRIAL_IDENTITY_UNAVAILABLE; return 1
    fi
    reset_old_boot=${reset_record##*:}
    if [ "$reset_old_boot" = "$reset_boot" ]; then
        guard_operation_release; setup_reply FAILED TRIAL_IDENTITY_UNAVAILABLE; return 1
    fi
    rm -f "$PHYSICAL_FILE" "$PHYSICAL_FILE.tmp" "$GETEVENT_PID_FILE" "$GETEVENT_PID_FILE.tmp" \
        "$READER_PID_FILE" "$READER_PID_FILE.tmp" "$WRITER_PID_FILE" "$WRITER_PID_FILE.tmp" "$MONITOR_ERROR_FILE"
    if [ -d "$LOCK_DIR" ] && ! rmdir "$LOCK_DIR" 2>/dev/null; then
        guard_operation_release; setup_reply FAILED TRIAL_LOCK_UNRECOGNIZED; return 1
    fi
    rm -f "$PID_FILE" "$REQUEST_FILE" "$ABORT_FILE"
    guard_operation_release
    setup_reply STOPPED ''
}

setup_main() {
    case "${1:-status}" in
      status) setup_status; return ;;
      abort|confirm-native|qualify) setup_request "$1"; return ;;
      reset-stale) setup_reset_stale; return ;;
      start) ;;
      *) setup_reply FAILED INVALID_ACTION; return 2 ;;
    esac
    guard_clock || { setup_reply FAILED CLOCK_UNAVAILABLE; return 1; }
    setup_init
    guard_operation_acquire || { setup_reply FAILED OPERATION_BUSY; return 1; }
    if [ -e "$GUARD_PID_FILE" ] || [ -d "$GUARD_LOCK_DIR" ]; then
        guard_operation_release; setup_reply FAILED CONTROLLER_NOT_STOPPED; return 1
    fi
    if [ -e "$PID_FILE" ] || ! mkdir "$LOCK_DIR" 2>/dev/null; then
        guard_operation_release; setup_status; return 1
    fi
    SETUP_OWN_LOCK=1
    # The owner has begun a new trial and controller absence is established.
    # An unsuccessful attempt must not leave an earlier ticket unlocked.
    rm -f "$QUALIFICATION_FILE"
    # Remove only stale requests, before publishing this trial's live identity.
    # Requests arriving during preflight belong to this trial and must survive.
    rm -f "$REQUEST_FILE" "$ABORT_FILE"
    trap 'setup_restore CANCELLED 1' TERM INT
    trap '' HUP
    # Publish our startup identity before probes, keeping observation honest
    # while the monitor is being prepared.
    setup_phase INITIALIZING
    if guard_process_identity "$$" &&
        printf '%s:%s:%s\n' "$$" "$process_started" "$process_boot" > "$PID_FILE"; then
        setup_publish || ERROR_CODE=STATE_WRITE_FAILED
    else ERROR_CODE=PROCESS_IDENTITY_UNAVAILABLE; fi
    # Read-only preflight completes before input observation or any key command.
    if [ -n "$ERROR_CODE" ]; then :
    elif ! command -v timeout >/dev/null 2>&1; then ERROR_CODE=REQUIRED_TOOL_UNAVAILABLE_TIMEOUT
    elif ! guard_compatibility_check; then ERROR_CODE=$COMPAT_REASON
    elif [ "$PROFILE_SCHEMA" != 2 ]; then ERROR_CODE=RUNTIME_BINDING_REQUIRED
    else
        setup_script_hash=$(sha256sum "$CONTROLLER_SCRIPT_PATH" 2>/dev/null)
        [ "${setup_script_hash%% *}" = "$PROFILE_CONTROLLER_SHA" ] || ERROR_CODE=CONTROLLER_CHANGED
    fi
    guard_operation_release
    if [ -z "$ERROR_CODE" ]; then guard_start_monitor || ERROR_CODE=PHYSICAL_MONITOR_FAILED; fi
    if [ -n "$ERROR_CODE" ]; then
        PHASE=FAILED; REASON=$ERROR_CODE; setup_publish; setup_cleanup; setup_status; return 1
    fi
    guard_clock || { setup_cleanup; return 1; }
    [ "$PHASE" = ABORTING ] || setup_phase WAIT_NORMAL
    setup_publish || { setup_cleanup; return 1; }
    while :; do
        guard_clock || { PHASE=FAILED; REASON=CLOCK_UNAVAILABLE; break; }
        if ! guard_monitor_alive; then
            [ "$PHASE" = ABORTING ] || setup_restore PHYSICAL_MONITOR_FAILED
        elif ! guard_physical_read; then
            [ "$PHASE" = ABORTING ] || setup_restore PHYSICAL_STATE_INVALID
        fi
        guard_native_read || { PHASE=FAILED; REASON=NATIVE_STATE_READ_FAILED; break; }
        guard_stability
        setup_tick
        setup_handle_result "$?"
        setup_publish || break
        case "$PHASE" in QUALIFIED|FAILED|ABORTED) break ;; esac
        sleep 1
    done
    setup_publish
    setup_cleanup
    setup_status
}

if [ "${NXTPAPER_SETUP_SOURCE_ONLY:-0}" != 1 ]; then setup_main "$@"; fi
