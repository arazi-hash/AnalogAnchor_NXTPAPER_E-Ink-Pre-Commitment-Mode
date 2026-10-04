#!/system/bin/sh
# UID 2000 controller for the verified TCL T807D firmware. No root required.
# TSWT_state is the FRAMEWORK desired mode; injected keys change it. Only the
# separate tswt kernel input stream supplies the physical slider position.

BASE=/data/local/tmp/nxtpaper_guard
SCRIPT_PATH=/data/local/tmp/nxtpaper_guard.sh
PID_FILE=$BASE.pid
STATE_FILE=$BASE.state
LOG_FILE=$BASE.log
LANGUAGE_FILE=$BASE.language
LOCK_DIR=$BASE.lock
PHYSICAL_FILE=$LOCK_DIR/physical
GETEVENT_PID_FILE=$LOCK_DIR/getevent.pid
READER_PID_FILE=$LOCK_DIR/reader.pid
WRITER_PID_FILE=$LOCK_DIR/writer.pid
MONITOR_ERROR_FILE=$LOCK_DIR/monitor.error
DURATION_FILE=$BASE.duration
DURATION_REQUEST=$BASE.duration.request
DURATION_ACK=$BASE.duration.ack
DURATION_COMMAND_LOCK=$BASE.duration.command.lock
PROC_ROOT=/proc
KEYLAYOUT_PATH=/system/usr/keylayout/Generic.kl
STABLE_SECONDS=2
COMMAND_INTERVAL=2
TRANSITION_TIMEOUT=45
ACK_GRACE=15
MAX_REPAIR_CYCLES=2
DEFAULT_DURATION=300

guard_clock() {
    # Uptime includes screen sleep. Changing the wall clock cannot renew time.
    read -r clock_uptime clock_idle < "$PROC_ROOT/uptime" || return 1
    NOW=${clock_uptime%%.*}
    case "$NOW" in ''|*[!0-9]*) return 1 ;; esac
}

guard_init() {
    PHASE=WAIT_SWITCH
    PHYSICAL=UNKNOWN
    RAW_SEQ=0
    OFF_SEQ=0
    ON_SEQ=0
    ON_AT=0
    FIRST_OFF_SEQ=0
    ARM_SEQ=0
    SESSION_START=0
    DEADLINE=0
    DURATION=$DEFAULT_DURATION
    NEXT_DURATION=$DEFAULT_DURATION
    REPAIR_CYCLES=0
    NATIVE_READ_FAILURES=0
    LOGGED_SIGNATURE=
    PHASE_AT=$NOW
    LAST_COMMAND=-100
    PENDING=
    PENDING_AT=0
    RECOVERY_AT=0
    NATIVE_SIGNATURE=
    STABLE_AT=$NOW
    STABLE=0
    ERROR_CODE=
    STOP_REQUESTED=0
    GETEVENT_PID=
    READER_PID=
    OWN_LOCK=0
    RESTORE_REASON=
}

guard_log() {
    printf '[uptime=%s] %s\n' "$NOW" "$*" >> "$LOG_FILE"
}

guard_state() {
    remaining=0
    if [ "$PHASE" = COMMITTED ]; then
        remaining=$((DEADLINE - NOW))
        [ "$remaining" -ge 0 ] || remaining=0
    fi
    printf '%s:%s:%s:%s:%s:%s:%s:%s\n' "$PHASE" "$remaining" \
        "$SESSION_START" "$DEADLINE" "$NOW" "$PHYSICAL" "$ERROR_CODE" "$NEXT_DURATION"
}

guard_publish() {
    val=$(guard_state)
    if ! { printf '%s\n' "$val" > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"; }; then
        guard_fail STATE_WRITE_FAILED
        return 1
    fi
    # A cache for the UI, never proof that the daemon is alive.
    if [ "$val" != "$PUBLISHED_STATE" ]; then
        settings put system nxtpaper_guard_state "$val" >/dev/null 2>&1
        PUBLISHED_STATE=$val
    fi
    guard_notify
    return 0
}

guard_notify() {
    # Update on phase changes / minute changes only, not on every poll or retry.
    notification_language=$(cat "$LANGUAGE_FILE" 2>/dev/null)
    [ "$notification_language" = ar ] || notification_language=en
    notification_key=$notification_language:$PHASE
    if [ "$PHASE" = COMMITTED ]; then
        notification_remaining=$((DEADLINE - NOW))
        [ "$notification_remaining" -ge 0 ] || notification_remaining=0
        notification_key=$notification_language:$PHASE:$((notification_remaining / 60))
    fi
    [ "$notification_key" != "$LAST_NOTIFICATION" ] || return 0
    LAST_NOTIFICATION=$notification_key
    if [ "$notification_language" = ar ]; then
        notification_title='E-Ink Pre-commitment Mode'
        case "$PHASE" in
          INITIALIZING) notification_text='جارٍ التحقق من وضع الحبر وزر الجهاز.' ;;
          WAIT_SWITCH) notification_text='حرّك المفتاح إلى Max Ink للبدء. إذا كان هناك بالفعل، حرّكه إلى العادي أولًا.' ;;
          STARTING) notification_text='بانتظار اكتمال الدخول إلى وضع الحبر.' ;;
          COMMITTED) notification_text="الوقت المتبقي: $((notification_remaining / 60)) دقيقة و$((notification_remaining % 60)) ثانية." ;;
          EXTENDED) notification_text='انتهى الالتزام. واصل القراءة، وأعد الزر إلى الوضع العادي عندما تنتهي.' ;;
          RESTORING) notification_text='جارٍ العودة إلى الوضع العادي.' ;;
          ERROR) notification_text='تعذّر تشغيل الحماية. افتح التطبيق لإعادة المحاولة.' ;;
          *) cmd notification cancel guard_commit >/dev/null 2>&1; return 0 ;;
        esac
    else
        notification_title='E-Ink Pre-commitment Mode'
        case "$PHASE" in
          INITIALIZING) notification_text='Checking native controls and the physical slider monitor.' ;;
          WAIT_SWITCH) notification_text='Move the slider to Max Ink to begin. If already there, move to Normal first.' ;;
          STARTING) notification_text='Waiting for Max Ink to finish starting.' ;;
          COMMITTED) notification_text="Focus commitment: $((notification_remaining / 60))m $((notification_remaining % 60))s remaining." ;;
          EXTENDED) notification_text='Commitment complete. Keep reading; move the physical slider to Normal when finished.' ;;
          RESTORING) notification_text='Restoring Normal mode. Please wait.' ;;
          ERROR) notification_text='Guard unavailable. Open E-Ink Pre-commitment Mode to retry.' ;;
          *) cmd notification cancel guard_commit >/dev/null 2>&1; return 0 ;;
        esac
    fi
    cmd notification post -S bigtext -t "$notification_title" guard_commit "$notification_text" >/dev/null 2>&1
}

guard_fail() {
    ERROR_CODE=$1
    guard_log "ERROR $ERROR_CODE"
    return 1
}

guard_native_read() {
    native_values=$(settings list secure 2>/dev/null) || return 1
    # Read all fields in one snapshot, explicitly validating transition flags.
    native_parsed=$(printf '%s\n' "$native_values" | awk -F= '
      BEGIN {
        k[1]="TSWT_state"; k[2]="nxtpaper_ink_style_state";
        k[3]="nxtpaper_book_style_state"; k[4]="nxtpaper_is_applying_theme";
        k[5]="nxtpaper_animation_state"; k[6]="tct_nxtpaper_mode_select";
        k[7]="tct_nxtpaper_switch_imm"
      }
      { for (i=1;i<=7;i++) if ($1==k[i]) { count[i]++; v[i]=$2 } }
      END {
        if ((count[6]==1 && v[6]!="3") || (count[7]==1 && v[7]!="1")) exit 2;
        for (i=1;i<=7;i++) if (count[i]!=1) exit 1;
        # TCL initializes TSWT_state to -1 on every boot. This exact sentinel
        # is an unknown desired mode, not physical position or a settled mode.
        if ((v[1]!="-1" && v[1]!~/^[01]$/) || v[2]!~/^[012]$/ || v[3]!~/^[01]$/ ||
            v[4]!~/^[01]$/ || v[5]!~/^[01]$/) exit 1;
        print v[1],v[2],v[3],v[4],v[5]
      }') || return $?
    read -r TSWT INK BOOK APPLYING ANIMATION <<EOF
$native_parsed
EOF
}

guard_stability() {
    STABLE=0
    native_signature=$TSWT:$INK:$BOOK:$APPLYING:$ANIMATION
    if [ "$native_signature" != "$LOGGED_SIGNATURE" ]; then
        guard_log "native snapshot=$native_signature phase=$PHASE pending=$PENDING deadline=$DEADLINE"
        LOGGED_SIGNATURE=$native_signature
    fi
    if [ "$APPLYING" != 0 ] || [ "$ANIMATION" != 0 ]; then
        NATIVE_SIGNATURE=
        STABLE_AT=$NOW
    elif [ "$native_signature" != "$NATIVE_SIGNATURE" ]; then
        NATIVE_SIGNATURE=$native_signature
        STABLE_AT=$NOW
    elif [ $((NOW - STABLE_AT)) -ge "$STABLE_SECONDS" ]; then
        STABLE=1
    fi
}

guard_is_ink() {
    [ "$TSWT" = 1 ] && [ "$INK" = 2 ] && [ "$BOOK" = 1 ] && [ "$STABLE" = 1 ]
}

guard_is_normal() {
    [ "$TSWT" = 0 ] && [ "$INK" = 0 ] && [ "$BOOK" = 0 ] && [ "$STABLE" = 1 ]
}

guard_physical_read() {
    [ -f "$PHYSICAL_FILE" ] || return 0
    IFS=: read -r raw_seq raw_position raw_at raw_off raw_on raw_on_at raw_first_off < "$PHYSICAL_FILE" || return 1
    case "$raw_seq:$raw_at:$raw_off:$raw_on:$raw_on_at:$raw_first_off" in *[!0-9:]*|'') return 1 ;; esac
    [ -n "$raw_seq" ] && [ -n "$raw_at" ] && [ -n "$raw_off" ] &&
        [ -n "$raw_on" ] && [ -n "$raw_on_at" ] && [ -n "$raw_first_off" ] || return 1
    case "$raw_position" in OFF|ON) ;; *) return 1 ;; esac
    if [ "$raw_seq" -gt "$RAW_SEQ" ]; then
        RAW_SEQ=$raw_seq
        PHYSICAL=$raw_position
        OFF_SEQ=$raw_off
        ON_SEQ=$raw_on
        ON_AT=$raw_on_at
        FIRST_OFF_SEQ=$raw_first_off
        guard_log "raw slider $PHYSICAL sequence=$RAW_SEQ"
    fi
}

guard_issue() {
    key=$1
    purpose=$2
    [ $((NOW - LAST_COMMAND)) -ge "$COMMAND_INTERVAL" ] || return 0
    # ON arriving during the settings read wins before automatic restoration.
    guard_physical_read || return 1
    if [ "$purpose" = EXIT ] && [ "$RESTORE_REASON" != STOP ] && [ "$PHYSICAL" = ON ]; then
        PHASE=EXTENDED
        RESTORE_REASON=
        RECOVERY_AT=0
        return 0
    fi
    [ "$TSWT" != -1 ] || return 0
    input keyevent "$key" >/dev/null 2>&1 || return 1
    LAST_COMMAND=$NOW
    PENDING=$purpose
    PENDING_AT=$NOW
    NATIVE_SIGNATURE=
    STABLE=0
    guard_log "native key=$key purpose=$purpose deadline=$DEADLINE"
}

guard_acknowledge() {
    [ -z "$PENDING" ] || guard_log "native acknowledged purpose=$PENDING elapsed=$((NOW - PENDING_AT)) deadline=$DEADLINE"
    PENDING=
}

guard_repair() {
    [ "$TSWT" != -1 ] || return 0
    [ "$REPAIR_CYCLES" -lt "$MAX_REPAIR_CYCLES" ] || return 0
    [ $((NOW - LAST_COMMAND)) -ge "$COMMAND_INTERVAL" ] || return 0
    REPAIR_CYCLES=$((REPAIR_CYCLES + 1))
    guard_log "repair attempt=$REPAIR_CYCLES purpose=$2 deadline=$DEADLINE"
    guard_issue "$1" "$2"
}

guard_ensure_ink() {
    if guard_is_ink; then
        guard_acknowledge
        RECOVERY_AT=0
        REPAIR_CYCLES=0
        return 0
    fi
    [ "$RECOVERY_AT" -ne 0 ] || RECOVERY_AT=$NOW
    if [ $((NOW - RECOVERY_AT)) -gt "$TRANSITION_TIMEOUT" ]; then
        guard_fail NATIVE_RECOVERY_TIMEOUT
        return 1
    fi
    # A genuine raw event can precede the framework updating its boot sentinel.
    # Wait for a concrete desired mode; never repair using an unknown snapshot.
    [ "$TSWT" != -1 ] || return 0
    # Opposite keys wait for the OEM transition and a stable native snapshot.
    [ "$STABLE" = 1 ] || return 0
    if [ "$PENDING" = RESET ]; then
        if guard_is_normal; then
            guard_acknowledge
            guard_issue 343 ENTER
        elif [ $((NOW - PENDING_AT)) -ge "$ACK_GRACE" ]; then
            guard_repair 344 RESET
        fi
    elif [ "$PENDING" = ENTER ]; then
        [ $((NOW - PENDING_AT)) -ge "$ACK_GRACE" ] || return 0
        if guard_is_normal; then guard_repair 343 ENTER
        else guard_repair 344 RESET; fi
    elif [ "$TSWT" = 0 ]; then
        # Physical OFF may have reversed the framework during pending entry.
        guard_is_normal || return 0
        guard_issue 343 ENTER
    else
        # Desired ON with a stable wrong mode needs a serialized OFF/ON edge.
        # Neither repair command changes the original commitment deadline.
        guard_repair 344 RESET
    fi
}

guard_begin_restore() {
    PHASE=RESTORING
    PHASE_AT=$NOW
    RESTORE_REASON=$1
    RECOVERY_AT=0
    REPAIR_CYCLES=0
    if [ "$1" = STOP ]; then guard_clear_duration || return 1; fi
    guard_log "restoring reason=$RESTORE_REASON deadline=$DEADLINE"
}

guard_duration_valid() {
    case "$1" in 300|7200|14400|21600|43200) return 0 ;; *) return 1 ;; esac
}

guard_duration_boot() {
    cat "$PROC_ROOT/sys/kernel/random/boot_id" 2>/dev/null
}

guard_duration_load() {
    NEXT_DURATION=$DEFAULT_DURATION
    DURATION_BOOT=$(guard_duration_boot) || return 1
    [ -r "$DURATION_FILE" ] || return 0
    IFS=: read -r saved_duration_boot saved_duration < "$DURATION_FILE" || return 0
    if [ "$saved_duration_boot" = "$DURATION_BOOT" ] && guard_duration_valid "$saved_duration"; then
        NEXT_DURATION=$saved_duration
    fi
}

guard_duration_save() {
    [ -n "$DURATION_BOOT" ] || DURATION_BOOT=$(guard_duration_boot) || return 1
    printf '%s:%s\n' "$DURATION_BOOT" "$NEXT_DURATION" > "$DURATION_FILE.tmp" &&
        mv "$DURATION_FILE.tmp" "$DURATION_FILE"
}

guard_clear_duration() {
    NEXT_DURATION=$DEFAULT_DURATION
    guard_duration_save || { guard_fail DURATION_WRITE_FAILED; return 1; }
}

guard_duration_error() {
    printf 'ERROR:0:0:0:%s:%s:%s:%s\n' "$NOW" "$PHYSICAL" "$1" "$NEXT_DURATION"
}

guard_duration_request() {
    [ -r "$DURATION_REQUEST" ] || return 0
    IFS=: read -r duration_request_id duration_request_boot duration_request_value < "$DURATION_REQUEST" || return 0
    case "$duration_request_id" in ''|*[!0-9-]*) rm -f "$DURATION_REQUEST"; return 0 ;; esac
    if [ "$duration_request_boot" != "$DURATION_BOOT" ]; then
        duration_reply=$(guard_duration_error DURATION_STALE)
    elif ! guard_duration_valid "$duration_request_value"; then
        duration_reply=$(guard_duration_error DURATION_INVALID)
    else
        case "$PHASE" in
          WAIT_SWITCH|IDLE|WAIT_OFF)
            previous_duration=$NEXT_DURATION
            NEXT_DURATION=$duration_request_value
            if guard_duration_save; then
                guard_log "next duration selected=$NEXT_DURATION request=$duration_request_id"
                guard_publish || return 1
                duration_reply=$(guard_state)
            else
                NEXT_DURATION=$previous_duration
                duration_reply=$(guard_duration_error DURATION_WRITE_FAILED)
            fi ;;
          *) duration_reply=$(guard_duration_error DURATION_BUSY) ;;
        esac
    fi
    # Transaction errors are replies only; they never replace daemon state.
    printf '%s:%s\n' "$duration_request_id" "$duration_reply" > "$DURATION_ACK.tmp" &&
        mv "$DURATION_ACK.tmp" "$DURATION_ACK" || { guard_fail DURATION_ACK_FAILED; return 1; }
    rm -f "$DURATION_REQUEST"
}

guard_duration_owner_live() {
    # An unreadable identity for a still-existing process is not proof of death.
    [ "$3" = "$DURATION_BOOT" ] || return 1
    if guard_process_info "$1"; then
        [ "$process_started" = "$2" ] && [ "$process_boot" = "$3" ]
    else
        [ -e "$PROC_ROOT/$1" ]
    fi
}

guard_set_duration() (
    guard_duration_load || { guard_duration_error CLOCK_UNAVAILABLE; return 0; }
    guard_duration_valid "${1:-}" || { guard_duration_error DURATION_INVALID; return 0; }
    duration_value=$1
    guard_process_info "$$" || { guard_duration_error PROCESS_IDENTITY_UNAVAILABLE; return 0; }
    case "$process_started" in ''|*[!0-9]*) guard_duration_error PROCESS_IDENTITY_UNAVAILABLE; return 0 ;; esac
    case "$process_boot" in ''|*[!a-zA-Z0-9-]*) guard_duration_error PROCESS_IDENTITY_UNAVAILABLE; return 0 ;; esac
    # The container may outlive a killed caller. Identity is part of each
    # atomic reservation name, so there is no mkdir-to-owner-file crash gap.
    duration_claim=$DURATION_COMMAND_LOCK/claim.$$.$process_started.$process_boot
    mkdir "$DURATION_COMMAND_LOCK" 2>/dev/null || [ -d "$DURATION_COMMAND_LOCK" ] || {
        guard_duration_error DURATION_WRITE_FAILED; return 0;
    }
    mkdir "$duration_claim" 2>/dev/null || { guard_duration_error DURATION_BUSY; return 0; }
    trap 'rmdir "$duration_claim" 2>/dev/null; rmdir "$DURATION_COMMAND_LOCK" 2>/dev/null || :' EXIT
    trap 'exit 1' TERM INT HUP
    # Older controllers wrote a shared owner file. Check it conservatively,
    # but never delete or overwrite it: a concurrent legacy owner may replace
    # that record. A confirmed stale record does not block new reservations.
    if [ -e "$DURATION_COMMAND_LOCK/owner" ]; then
        IFS=: read -r owner_pid owner_started owner_boot < "$DURATION_COMMAND_LOCK/owner" || {
            guard_duration_error DURATION_BUSY; return 0;
        }
        case "$owner_pid" in ''|*[!0-9]*) guard_duration_error DURATION_BUSY; return 0 ;; esac
        case "$owner_started" in ''|*[!0-9]*) guard_duration_error DURATION_BUSY; return 0 ;; esac
        case "$owner_boot" in ''|*[!a-zA-Z0-9-]*) guard_duration_error DURATION_BUSY; return 0 ;; esac
        duration_legacy_owner=$owner_pid:$owner_started:$owner_boot
        if guard_duration_owner_live "$owner_pid" "$owner_started" "$owner_boot"; then
            guard_duration_error DURATION_BUSY; return 0
        fi
        IFS=: read -r owner_pid owner_started owner_boot < "$DURATION_COMMAND_LOCK/owner" || {
            guard_duration_error DURATION_BUSY; return 0;
        }
        [ "$duration_legacy_owner" = "$owner_pid:$owner_started:$owner_boot" ] || {
            guard_duration_error DURATION_BUSY; return 0;
        }
    fi
    for duration_other in "$DURATION_COMMAND_LOCK"/claim.*; do
        [ -e "$duration_other" ] || continue
        [ "$duration_other" != "$duration_claim" ] || continue
        claim_identity=${duration_other##*/claim.}
        claim_pid=${claim_identity%%.*}
        claim_tail=${claim_identity#*.}
        claim_started=${claim_tail%%.*}
        claim_boot=${claim_tail#*.}
        case "$claim_pid" in ''|*[!0-9]*) guard_duration_error DURATION_BUSY; return 0 ;; esac
        case "$claim_started" in ''|*[!0-9]*) guard_duration_error DURATION_BUSY; return 0 ;; esac
        case "$claim_boot" in ''|*[!a-zA-Z0-9-]*) guard_duration_error DURATION_BUSY; return 0 ;; esac
        if [ "$claim_identity" != "$claim_pid.$claim_started.$claim_boot" ] ||
            guard_duration_owner_live "$claim_pid" "$claim_started" "$claim_boot"; then
            guard_duration_error DURATION_BUSY; return 0
        fi
        # Only this dead identity's unique reservation is eligible for removal.
        rmdir "$duration_other" 2>/dev/null || { guard_duration_error DURATION_BUSY; return 0; }
    done
    if ! guard_live_pid; then
        previous_duration=$NEXT_DURATION
        NEXT_DURATION=$duration_value
        guard_duration_save || {
            NEXT_DURATION=$previous_duration
            guard_duration_error DURATION_WRITE_FAILED; return 0;
        }
        PHASE=STOPPED
        ERROR_CODE=
        guard_state
        return 0
    fi
    duration_request_token=$$-$NOW
    rm -f "$DURATION_ACK"
    printf '%s:%s:%s\n' "$duration_request_token" "$DURATION_BOOT" "$duration_value" > "$DURATION_REQUEST.tmp" &&
        mv "$DURATION_REQUEST.tmp" "$DURATION_REQUEST" || { guard_duration_error DURATION_WRITE_FAILED; return 0; }
    duration_wait=0
    while [ "$duration_wait" -le 5 ]; do
        if [ -r "$DURATION_ACK" ]; then
            IFS=: read -r duration_ack_token duration_ack_status < "$DURATION_ACK"
            if [ "$duration_ack_token" = "$duration_request_token" ]; then
                printf '%s\n' "$duration_ack_status"
                return 0
            fi
        fi
        [ "$duration_wait" -lt 5 ] || break
        sleep 1
        duration_wait=$((duration_wait + 1))
    done
    # Cancel only our still-pending request; an unrelated transaction is never
    # removed. Acknowledgment may already have consumed this request.
    if [ -r "$DURATION_REQUEST" ]; then
        IFS=: read -r pending_duration_token rest < "$DURATION_REQUEST"
        [ "$pending_duration_token" != "$duration_request_token" ] || rm -f "$DURATION_REQUEST"
    fi
    guard_duration_error DURATION_TIMEOUT
)

guard_duration() {
    DURATION=$NEXT_DURATION
    # Consume the one-shot choice before issuing a native command. Neither a
    # later app launch nor a recovery command may renew it or the deadline.
    guard_clear_duration
}

guard_tick() {
    guard_stability
    case "$PHASE" in
      WAIT_SWITCH)
        # Never infer an initial physical position from framework/native mode.
        # The first fresh ON is a real entry even without a preceding OFF.
        # Counters preserve ON followed by OFF between two controller polls.
        if [ "$ON_SEQ" -gt 0 ]; then PHASE=IDLE; ARM_SEQ=0
        elif [ "$FIRST_OFF_SEQ" -gt 0 ]; then PHASE=IDLE; ARM_SEQ=$FIRST_OFF_SEQ; fi
        ;;
      WAIT_OFF)
        if [ "$PHYSICAL" = OFF ]; then PHASE=IDLE; ARM_SEQ=$RAW_SEQ; fi
        ;;
    esac
    if [ "$PHASE" = IDLE ] && [ "$ON_SEQ" -gt "$ARM_SEQ" ]; then
        PHASE=STARTING
        PHASE_AT=$NOW
        RECOVERY_AT=0
        PENDING=
        REPAIR_CYCLES=0
        NATIVE_SIGNATURE=
        STABLE_AT=$NOW
        STABLE=0
        guard_duration || return 1
        guard_log "physical entry; waiting for stable Max Ink duration=$DURATION"
    fi
    case "$PHASE" in
      STARTING)
        if guard_is_ink; then
            SESSION_START=$NOW
            DEADLINE=$((NOW + DURATION))
            PHASE=COMMITTED
            guard_acknowledge
            RECOVERY_AT=0
            guard_log "commitment confirmed deadline=$DEADLINE"
        else guard_ensure_ink || return 1; fi
        ;;
      COMMITTED)
        if [ "$NOW" -ge "$DEADLINE" ]; then
            guard_physical_read || return 1
            if [ "$PHYSICAL" = ON ]; then
                PHASE=EXTENDED
                guard_log "commitment complete; physical ON continues reading"
                guard_ensure_ink || return 1
            elif [ "$PHYSICAL" = OFF ]; then guard_begin_restore EXPIRED
            else guard_fail UNKNOWN_SWITCH_DURING_SESSION; return 1; fi
        else guard_ensure_ink || return 1; fi
        ;;
      EXTENDED)
        if [ "$PHYSICAL" = OFF ]; then guard_begin_restore USER_OFF
        else guard_ensure_ink || return 1; fi
        ;;
    esac
    if [ "$PHASE" = RESTORING ]; then
        guard_physical_read || return 1
        if [ "$RESTORE_REASON" != STOP ] && [ "$PHYSICAL" = ON ]; then
            PHASE=EXTENDED
            RESTORE_REASON=
            [ "$PENDING" != EXIT ] || PENDING=
            return 0
        fi
        if guard_is_normal; then
            SESSION_START=0
            DEADLINE=0
            guard_acknowledge
            RECOVERY_AT=0
            REPAIR_CYCLES=0
            if [ "$STOP_REQUESTED" = 1 ]; then PHASE=STOPPED
            elif [ "$PHYSICAL" = OFF ]; then PHASE=IDLE; ARM_SEQ=$RAW_SEQ
            else PHASE=WAIT_OFF; fi
            RESTORE_REASON=
            guard_log "normal mode fully settled"
        elif [ $((NOW - PHASE_AT)) -gt "$TRANSITION_TIMEOUT" ]; then
            guard_fail NORMAL_RESTORE_TIMEOUT
            return 1
        elif [ "$TSWT" = -1 ]; then
            : # Known boot/unknown mode: bounded wait, no corrective key.
        elif [ "$STABLE" = 1 ]; then
            if [ "$PENDING" = RESTORE_ON ]; then
                if guard_is_ink; then
                    guard_acknowledge
                    guard_issue 344 EXIT || return 1
                elif [ $((NOW - PENDING_AT)) -ge "$ACK_GRACE" ]; then
                    if [ "$TSWT" = 1 ]; then
                        guard_log "restore ON edge settled in incomplete mode; requesting OFF deadline=$DEADLINE"
                        PENDING=
                        guard_issue 344 EXIT || return 1
                    else guard_repair 343 RESTORE_ON || return 1; fi
                fi
            elif [ "$PENDING" = EXIT ]; then
                if [ $((NOW - PENDING_AT)) -ge "$ACK_GRACE" ]; then
                    if [ "$TSWT" = 1 ]; then guard_repair 344 EXIT || return 1
                    else guard_repair 343 RESTORE_ON || return 1; fi
                fi
            elif [ "$TSWT" = 1 ]; then guard_issue 344 EXIT || return 1
            else guard_repair 343 RESTORE_ON || return 1; fi
        fi
    fi
}

guard_discover() {
    capabilities=$(getevent -lp 2>/dev/null) || return 1
    SWITCH_NODE=$(printf '%s\n' "$capabilities" | awk '
      function finish() {
        if (name=="tswt") { count++; if (min && max) found=node; else bad=1 }
      }
      /^add device [0-9]+: \/dev\/input\/event[0-9]+[[:space:]]*$/ {
        finish(); node=$4; name=""; min=0; max=0
      }
      /^[[:space:]]*name:/ { line=$0; sub(/^[^"]*"/,"",line); sub(/".*$/,"",line); name=line }
      /KEY_BRIGHTNESS_MIN/ { min=1 }
      /KEY_BRIGHTNESS_MAX/ { max=1 }
      END { finish(); if (count!=1 || bad || found=="") exit 1; print found }
    ') || return 1
    awk '
      { sub(/#.*/,"") }
      $1=="key" && ($2=="592" || $2=="593") { count[$2]++; map[$2]=$3 }
      END { if (count[592]!=1 || count[593]!=1 || map[592]!="TSWT_ON" || map[593]!="TSWT_OFF") exit 1 }
    ' "$KEYLAYOUT_PATH" || return 1
}

guard_validate() {
    [ "$(id -u)" = 2000 ] || { guard_fail SHELL_PRIVILEGE_REQUIRED; return 1; }
    [ "$(getprop ro.product.model)" = T807D ] &&
    [ "$(getprop ro.build.version.release)" = 16 ] &&
    [ "$(getprop ro.build.version.sdk)" = 36 ] &&
    [ "$(getprop ro.build.fingerprint)" = 'TCL/T807D_EEA/Frida:16/BP2A.250605.031.A3/AMD9:user/release-keys' ] || {
        guard_fail UNSUPPORTED_FIRMWARE; return 1;
    }
    validation_reads=0
    while :; do
        if guard_native_read; then break; else native_result=$?; fi
        [ "$native_result" != 2 ] || { guard_fail NATIVE_PRESET_MISMATCH; return 1; }
        validation_reads=$((validation_reads + 1))
        guard_log "native startup read unavailable attempt=$validation_reads"
        [ "$validation_reads" -lt 3 ] || { guard_fail NATIVE_STATE_READ_FAILED; return 1; }
        sleep 1
    done
    guard_discover || { guard_fail PHYSICAL_SWITCH_UNAVAILABLE; return 1; }
}

guard_tools() {
    for required_tool in awk sed tr grep getprop settings input getevent id cmd; do
        command -v "$required_tool" >/dev/null 2>&1 || {
            guard_fail "REQUIRED_TOOL_UNAVAILABLE_$required_tool"
            return 1
        }
    done
}

guard_initializing() {
    PHASE=INITIALIZING
    guard_publish
}

guard_raw_reader() {
    seq=0; last_off=0; last_on=0; last_on_at=0; first_off=0
    while IFS= read -r raw_line; do
        # Accept only the final three event tokens: EV_KEY, MIN/MAX, DOWN.
        event_type=; event_key=; event_value=
        for token in $raw_line; do
            event_type=$event_key; event_key=$event_value; event_value=$token
        done
        [ "$event_type" = EV_KEY ] && [ "$event_value" = DOWN ] || continue
        case "$event_key" in
          KEY_BRIGHTNESS_MIN) position=ON ;;
          KEY_BRIGHTNESS_MAX) position=OFF ;;
          *) continue ;;
        esac
        guard_clock || break
        seq=$((seq + 1))
        if [ "$position" = OFF ]; then
            last_off=$seq
            [ "$first_off" -ne 0 ] || first_off=$seq
        else last_on=$seq; last_on_at=$NOW; fi
        printf '%s:%s:%s:%s:%s:%s:%s\n' "$seq" "$position" "$NOW" \
            "$last_off" "$last_on" "$last_on_at" "$first_off" > "$PHYSICAL_FILE.tmp" &&
            mv "$PHYSICAL_FILE.tmp" "$PHYSICAL_FILE" || break
    done
}

guard_process_info() {
    process_pid=$1
    case "$process_pid" in ''|*[!0-9]*) return 1 ;; esac
    [ -r "$PROC_ROOT/$process_pid/stat" ] && [ -r "$PROC_ROOT/$process_pid/cmdline" ] || return 1
    # Skip the parenthesized comm before selecting stat field 22 (starttime).
    process_started=$(sed 's/^.*) //' "$PROC_ROOT/$process_pid/stat" | awk '{print $20}')
    case "$process_started" in ''|*[!0-9]*) return 1 ;; esac
    process_boot=$(cat "$PROC_ROOT/sys/kernel/random/boot_id" 2>/dev/null) || return 1
}

guard_process_identity() {
    guard_process_info "$1" || return 1
    tr '\000' '\n' < "$PROC_ROOT/$process_pid/cmdline" | grep -Fx "$SCRIPT_PATH" >/dev/null
}

guard_self_pid() {
    # Unlike $$ inside a pipeline, this is the actual fork's PID. The shell
    # builtin opens /proc/self, so there is no intermediate cat/subshell PID.
    read -r self_stat < "$PROC_ROOT/self/stat" || return 1
    SELF_PID=${self_stat%% *}
    case "$SELF_PID" in ''|*[!0-9]*) return 1 ;; esac
}

guard_monitor_save() {
    guard_process_info "$1" || return 1
    printf '%s:%s:%s:%s\n' "$1" "$process_started" "$process_boot" "$SWITCH_NODE" > "$2.tmp" &&
        mv "$2.tmp" "$2"
}

guard_monitor_valid() {
    [ -r "$1" ] || return 1
    IFS=: read -r monitor_pid monitor_started monitor_boot monitor_node < "$1" || return 1
    case "$monitor_node" in /dev/input/event*) ;;
      *) return 1 ;; esac
    monitor_number=${monitor_node#/dev/input/event}
    case "$monitor_number" in ''|*[!0-9]*) return 1 ;; esac
    guard_process_info "$monitor_pid" || return 1
    [ "$process_started" = "$monitor_started" ] && [ "$process_boot" = "$monitor_boot" ] || return 1
    if [ "$2" = getevent ]; then
        tr '\000' '\n' < "$PROC_ROOT/$monitor_pid/cmdline" | grep -Eq '(^|/)getevent$' || return 1
        tr '\000' '\n' < "$PROC_ROOT/$monitor_pid/cmdline" | grep -Fx "$monitor_node" >/dev/null || return 1
    else
        tr '\000' '\n' < "$PROC_ROOT/$monitor_pid/cmdline" | grep -Fx "$SCRIPT_PATH" >/dev/null || return 1
    fi
    kill -0 "$monitor_pid" 2>/dev/null
}

guard_monitor_signal() {
    guard_monitor_valid "$1" "$2" || return 0
    kill -TERM "$monitor_pid" 2>/dev/null
}

guard_stream_writer_cleanup() {
    # The writer owns this child even when recording its token failed. Compare
    # the saved start time and boot before signaling; never kill a reused PID.
    [ -n "$stream_pid" ] && [ -n "$stream_started" ] || return 0
    guard_process_info "$stream_pid" || return 0
    [ "$process_started" = "$stream_started" ] && [ "$process_boot" = "$stream_boot" ] || return 0
    kill -TERM "$stream_pid" 2>/dev/null
    wait "$stream_pid" 2>/dev/null
}

guard_stream_writer() {
    stream_pid=; stream_started=; stream_boot=
    trap 'guard_stream_writer_cleanup; exit 0' TERM INT HUP
    guard_self_pid && guard_monitor_save "$SELF_PID" "$WRITER_PID_FILE" || {
        printf 'MONITOR_PID_WRITE_FAILED\n' > "$MONITOR_ERROR_FILE"
        return 1
    }
    getevent -lt "$SWITCH_NODE" 2>> "$LOG_FILE" &
    stream_pid=$!
    if ! guard_process_info "$stream_pid"; then
        printf 'PHYSICAL_MONITOR_FAILED\n' > "$MONITOR_ERROR_FILE"
        return 1
    fi
    stream_started=$process_started
    stream_boot=$process_boot
    if ! guard_monitor_save "$stream_pid" "$GETEVENT_PID_FILE"; then
        printf 'MONITOR_PID_WRITE_FAILED\n' > "$MONITOR_ERROR_FILE"
        guard_stream_writer_cleanup
        return 1
    fi
    wait "$stream_pid"
}

guard_stream_reader() {
    trap 'exit 0' TERM INT HUP
    guard_self_pid && guard_monitor_save "$SELF_PID" "$READER_PID_FILE" || {
        printf 'MONITOR_PID_WRITE_FAILED\n' > "$MONITOR_ERROR_FILE"
        return 1
    }
    guard_raw_reader
}

guard_monitor_alive() {
    [ ! -e "$MONITOR_ERROR_FILE" ] &&
        guard_monitor_valid "$GETEVENT_PID_FILE" getevent &&
        guard_monitor_valid "$READER_PID_FILE" reader &&
        guard_monitor_valid "$WRITER_PID_FILE" writer
}

guard_monitor_cleanup() {
    # Anonymous pipe wrappers terminate their own children. Tokens additionally
    # allow cleanup after a previous controller died, without touching other
    # getevent processes or signaling an unrelated reused PID.
    guard_monitor_signal "$WRITER_PID_FILE" writer
    guard_monitor_signal "$GETEVENT_PID_FILE" getevent
    guard_monitor_signal "$READER_PID_FILE" reader
}

guard_start_monitor() {
    # Named FIFO creation is denied to UID 2000 on the stock TCL firmware.
    # An anonymous kernel pipe works without a filesystem FIFO or root.
    guard_stream_writer | guard_stream_reader &
    READER_PID=$!
    sleep 1
    if ! guard_monitor_alive; then
        if [ -r "$MONITOR_ERROR_FILE" ]; then
            read -r ERROR_CODE < "$MONITOR_ERROR_FILE"
        else ERROR_CODE=PHYSICAL_MONITOR_FAILED; fi
        return 1
    fi
}

guard_live_pid() {
    [ -r "$PID_FILE" ] || return 1
    IFS=: read -r live_pid saved_started saved_boot < "$PID_FILE" || return 1
    guard_process_identity "$live_pid" || return 1
    [ "$process_started" = "$saved_started" ] && [ "$process_boot" = "$saved_boot" ] || return 1
    kill -0 "$live_pid" 2>/dev/null
}

guard_status() {
    if guard_live_pid; then
        guard_clock || { printf 'ERROR:0:0:0:0:UNKNOWN:CLOCK_UNAVAILABLE:300\n'; return 0; }
        if [ -r "$STATE_FILE" ]; then
            IFS=: read -r status_phase status_remaining status_start status_deadline status_at status_physical status_error < "$STATE_FILE"
            case "$status_at" in ''|*[!0-9]*) status_at=0 ;; esac
            if [ $((NOW - status_at)) -le 15 ] && [ "$NOW" -ge "$status_at" ]; then
                cat "$STATE_FILE"
                return 0
            fi
        fi
        printf 'ERROR:0:0:0:%s:UNKNOWN:DAEMON_UNRESPONSIVE:%s\n' "$NOW" "$NEXT_DURATION"
        return 0
    fi
    if [ -r "$STATE_FILE" ] && grep -q '^ERROR:' "$STATE_FILE"; then cat "$STATE_FILE"; return 0; fi
    printf 'STOPPED:0:0:0:0:UNKNOWN::%s\n' "$NEXT_DURATION"
}

guard_stop() {
    if ! guard_live_pid; then
        # Acknowledge a stale error without touching native mode or another PID.
        PHASE=STOPPED
        ERROR_CODE=
        SESSION_START=0
        DEADLINE=0
        guard_clear_duration || return 1
        guard_publish
        guard_state
        return 0
    fi
    stop_pid=$live_pid
    kill -TERM "$stop_pid" 2>/dev/null || return 1
    stop_wait=0
    while [ "$stop_wait" -le $((TRANSITION_TIMEOUT + 5)) ]; do
        if ! guard_live_pid; then
            # The daemon consumed/reset its choice while this Stop subprocess
            # waited. Return the persisted authority, never our pre-Stop copy.
            guard_duration_load || { guard_duration_error CLOCK_UNAVAILABLE; return 1; }
            guard_status
            return
        fi
        sleep 1
        stop_wait=$((stop_wait + 1))
    done
    printf 'ERROR:0:0:0:0:UNKNOWN:STOP_TIMEOUT:%s\n' "$NEXT_DURATION"
    return 1
}

guard_remove_lock() {
    [ "$OWN_LOCK" = 1 ] || return
    guard_monitor_cleanup
    [ -z "$READER_PID" ] || wait "$READER_PID" 2>/dev/null
    rm -f "$LOCK_DIR/input.fifo" "$PHYSICAL_FILE" "$PHYSICAL_FILE.tmp" \
        "$GETEVENT_PID_FILE" "$GETEVENT_PID_FILE.tmp" "$READER_PID_FILE" \
        "$READER_PID_FILE.tmp" "$WRITER_PID_FILE" "$WRITER_PID_FILE.tmp" "$MONITOR_ERROR_FILE"
    rmdir "$LOCK_DIR" 2>/dev/null
    rm -f "$PID_FILE"
}

guard_main() {
    guard_clock || { printf 'ERROR:0:0:0:0:UNKNOWN:CLOCK_UNAVAILABLE\n'; return 1; }
    guard_init
    guard_duration_load || { printf 'ERROR:0:0:0:0:UNKNOWN:CLOCK_UNAVAILABLE:300\n'; return 1; }
    case "${1:-start}" in
      status) guard_status; return ;;
      stop) guard_stop; return ;;
      set-duration)
        [ "$#" = 2 ] || { guard_duration_error DURATION_INVALID; return 0; }
        guard_set_duration "$2"; return ;;
      start) ;;
      *) printf 'Usage: nxtpaper_guard.sh [start|status|stop|set-duration <seconds>]\n'; return 2 ;;
    esac
    if guard_live_pid; then guard_status; return; fi
    if ! mkdir "$LOCK_DIR" 2>/dev/null; then
        sleep 1
        if guard_live_pid; then guard_status; return; fi
        guard_monitor_cleanup
        rm -f "$LOCK_DIR/input.fifo" "$PHYSICAL_FILE" "$PHYSICAL_FILE.tmp" \
            "$GETEVENT_PID_FILE" "$GETEVENT_PID_FILE.tmp" "$READER_PID_FILE" \
            "$READER_PID_FILE.tmp" "$WRITER_PID_FILE" "$WRITER_PID_FILE.tmp" "$MONITOR_ERROR_FILE"
        rmdir "$LOCK_DIR" 2>/dev/null
        mkdir "$LOCK_DIR" 2>/dev/null || { printf 'ERROR:0:0:0:0:UNKNOWN:START_LOCK_FAILED\n'; return 1; }
    fi
    OWN_LOCK=1
    rm -f "$DURATION_REQUEST" "$DURATION_ACK"
    trap 'STOP_REQUESTED=1' TERM INT
    trap '' HUP
    if ! guard_tools; then :
    elif ! guard_process_identity "$$"; then ERROR_CODE=PROCESS_IDENTITY_UNAVAILABLE
    elif ! printf '%s:%s:%s\n' "$$" "$process_started" "$process_boot" > "$PID_FILE"; then ERROR_CODE=PID_WRITE_FAILED
    elif ! guard_initializing; then :
    elif ! guard_validate; then :
    elif ! guard_start_monitor; then :
    fi
    if [ -n "$ERROR_CODE" ]; then
        guard_clear_duration || :
        PHASE=ERROR
        guard_publish
        guard_state
        guard_remove_lock
        return 1
    fi
    PHASE=WAIT_SWITCH
    guard_log "started; input=$SWITCH_NODE; position UNKNOWN until physical OFF/ON"
    guard_clock
    guard_publish || { guard_remove_lock; return 1; }
    while :; do
        guard_clock || { ERROR_CODE=CLOCK_UNAVAILABLE; break; }
        if [ "$STOP_REQUESTED" = 1 ]; then
            guard_clear_duration || break
            case "$PHASE" in
              WAIT_SWITCH|IDLE|WAIT_OFF) PHASE=STOPPED ;;
              RESTORING) RESTORE_REASON=STOP ;;
              STOPPED) ;;
              *) guard_begin_restore STOP ;;
            esac
        fi
        if [ "$PHASE" = STOPPED ]; then break; fi
        guard_monitor_alive || {
            ERROR_CODE=PHYSICAL_MONITOR_FAILED; break;
        }
        guard_physical_read || { ERROR_CODE=PHYSICAL_STATE_INVALID; break; }
        if guard_native_read; then NATIVE_READ_FAILURES=0
        else
            native_result=$?
            [ "$native_result" != 2 ] || { ERROR_CODE=NATIVE_PRESET_MISMATCH; break; }
            NATIVE_READ_FAILURES=$((NATIVE_READ_FAILURES + 1))
            guard_log "native read unavailable attempt=$NATIVE_READ_FAILURES phase=$PHASE deadline=$DEADLINE"
            [ "$NATIVE_READ_FAILURES" -lt 3 ] || { ERROR_CODE=NATIVE_STATE_READ_FAILED; break; }
            # A stale snapshot must never authorize a native mode command.
            guard_publish || break
            guard_duration_request || break
            sleep 1
            continue
        fi
        guard_clock && guard_physical_read || { ERROR_CODE=PHYSICAL_STATE_INVALID; break; }
        case "$PHASE" in
          WAIT_SWITCH|IDLE|WAIT_OFF) guard_duration_load || { ERROR_CODE=CLOCK_UNAVAILABLE; break; } ;;
        esac
        guard_tick || { [ -n "$ERROR_CODE" ] || ERROR_CODE=NATIVE_COMMAND_FAILED; break; }
        guard_duration_request || break
        guard_publish || break
        sleep 1
    done
    if [ -n "$ERROR_CODE" ]; then guard_clear_duration || :; PHASE=ERROR; fi
    guard_publish
    guard_state
    guard_remove_lock
    [ "$PHASE" != ERROR ]
}

# Host regressions source these exact functions with fake Android commands.
if [ "${NXTPAPER_GUARD_SOURCE_ONLY:-0}" != 1 ]; then
    guard_main "$@"
fi
