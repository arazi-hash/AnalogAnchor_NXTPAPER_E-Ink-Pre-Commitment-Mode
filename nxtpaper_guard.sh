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
STOP_REQUEST=$BASE.stop.request
STOP_ACK=$BASE.stop.ack
STOP_COMMAND_LOCK=$BASE.stop.command.lock
PROC_ROOT=/proc
KEYLAYOUT_PATH=/system/usr/keylayout/Generic.kl
STABLE_SECONDS=2
COMMAND_INTERVAL=2
TRANSITION_TIMEOUT=45
ACK_GRACE=15
MAX_REPAIR_CYCLES=2
DEFAULT_DURATION=300
EXIT_DELAY=300
PROFILE_FILE=$BASE.profile
PROFILE_LOADED=0

# Parse reviewed data, never source/eval it. Schema 1 fixes the native protocol;
# another build may reuse it only after its own qualification and source review.
guard_profile_load() {
    [ "$PROFILE_LOADED" = 1 ] && return 0
    if [ "${NXTPAPER_PROFILE_DATA+x}" = x ]; then
        profile_text=$NXTPAPER_PROFILE_DATA
    else
        profile_text=$(cat "$PROFILE_FILE" 2>/dev/null) || return 1
    fi
    profile_record=$(printf '%s\n' "$profile_text" | awk -F= '
      BEGIN {
        n=split("schema id qualification model device android sdk fingerprint input_name linux_on linux_off raw_on raw_off keylayout layout_on layout_off enter_key exit_key tswt_key ink_key book_key applying_key animation_key preset_key preset immediate_key immediate evidence", keys, " ");
        for (i=1;i<=n;i++) allowed[keys[i]]=1;
        split("schema=1 qualification=verified input_name=tswt linux_on=592 linux_off=593 raw_on=KEY_BRIGHTNESS_MIN raw_off=KEY_BRIGHTNESS_MAX keylayout=/system/usr/keylayout/Generic.kl layout_on=TSWT_ON layout_off=TSWT_OFF enter_key=343 exit_key=344 tswt_key=TSWT_state ink_key=nxtpaper_ink_style_state book_key=nxtpaper_book_style_state applying_key=nxtpaper_is_applying_theme animation_key=nxtpaper_animation_state preset_key=tct_nxtpaper_mode_select preset=3 immediate_key=tct_nxtpaper_switch_imm immediate=1", fixed, " ");
        for (i in fixed) { split(fixed[i], pair, "="); expected[pair[1]]=pair[2] }
      }
      { if (index($0,"\r")) bad=1 }
      /^#/ || /^$/ { next }
      { if (NF!=2 || !allowed[$1] || seen[$1]++ || $2!~/^[A-Za-z0-9_.\/:+-]+$/) bad=1; value[$1]=$2 }
      END {
        for (i=1;i<=n;i++) if (!seen[keys[i]]) bad=1;
        for (k in expected) if (value[k]!=expected[k]) bad=1;
        if (value["id"]!~/^[a-z0-9]+(-[a-z0-9]+)*$/ ||
            value["model"]!~/^[A-Za-z0-9_-]+$/ || value["device"]!~/^[A-Za-z0-9_-]+$/ ||
            value["android"]!~/^[1-9][0-9]*$/ || value["sdk"]!~/^[1-9][0-9]*$/ ||
            index(value["fingerprint"],":")==0 || index(value["fingerprint"],"/")==0 ||
            index(value["evidence"],"..") || value["evidence"]~/^\//) bad=1;
        if (bad) exit 1;
        for (i=1;i<=n;i++) printf "%s%s",value[keys[i]],(i==n ? "\n" : " ");
      }') || return 1
    read -r PROFILE_SCHEMA PROFILE_ID PROFILE_QUALIFICATION PROFILE_MODEL PROFILE_DEVICE \
        PROFILE_ANDROID PROFILE_SDK PROFILE_FINGERPRINT PROFILE_INPUT_NAME PROFILE_LINUX_ON \
        PROFILE_LINUX_OFF PROFILE_RAW_ON PROFILE_RAW_OFF PROFILE_KEYLAYOUT PROFILE_LAYOUT_ON \
        PROFILE_LAYOUT_OFF PROFILE_ENTER_KEY PROFILE_EXIT_KEY PROFILE_TSWT_KEY PROFILE_INK_KEY \
        PROFILE_BOOK_KEY PROFILE_APPLYING_KEY PROFILE_ANIMATION_KEY PROFILE_PRESET_KEY \
        PROFILE_PRESET PROFILE_IMMEDIATE_KEY PROFILE_IMMEDIATE PROFILE_EVIDENCE <<EOF
$profile_record
EOF
    PROFILE_LOADED=1
    unset profile_text profile_record
}

guard_identity_matches() {
    COMPAT_VERDICT=CAPABILITY_MISSING; COMPAT_REASON=PROFILE_INVALID
    guard_profile_load || return 1
    COMPAT_VERDICT=PRIVILEGE_UNAVAILABLE; COMPAT_REASON=SHELL_PRIVILEGE_REQUIRED
    [ "$(id -u 2>/dev/null)" = 2000 ] || return 1
    COMPAT_VERDICT=UNVERIFIED_BUILD; COMPAT_REASON=UNSUPPORTED_FIRMWARE
    [ "$(getprop ro.product.model)" = "$PROFILE_MODEL" ] &&
        [ "$(getprop ro.product.device)" = "$PROFILE_DEVICE" ] &&
        [ "$(getprop ro.build.version.release)" = "$PROFILE_ANDROID" ] &&
        [ "$(getprop ro.build.version.sdk)" = "$PROFILE_SDK" ] &&
        [ "$(getprop ro.build.fingerprint)" = "$PROFILE_FINGERPRINT" ] || return 1
    COMPAT_VERDICT=VERIFIED; COMPAT_REASON=$PROFILE_ID
}

# This entry point has no logging, notifications, settings writes, deployment,
# duration loading, process cleanup, or native commands. Reports are observations.
guard_compatibility_check() {
    COMPAT_VERDICT=CAPABILITY_MISSING; COMPAT_REASON=REQUIRED_TOOL_UNAVAILABLE
    for compatibility_tool in awk getprop settings getevent id; do
        command -v "$compatibility_tool" >/dev/null 2>&1 || return 1
    done
    guard_identity_matches || return 1
    COMPAT_VERDICT=CAPABILITY_MISSING; COMPAT_REASON=NATIVE_STATE_READ_FAILED
    if guard_native_read; then :
    else
        compatibility_native_result=$?
        [ "$compatibility_native_result" != 2 ] || COMPAT_REASON=NATIVE_PRESET_MISMATCH
        return 1
    fi
    COMPAT_REASON=PHYSICAL_SWITCH_UNAVAILABLE
    guard_discover || return 1
    COMPAT_VERDICT=VERIFIED; COMPAT_REASON=$PROFILE_ID
}

guard_compatibility_report() {
    guard_compatibility_check || :
    printf '%s:%s\n' "$COMPAT_VERDICT" "$COMPAT_REASON"
}

# Only the dedicated, stopped-controller native tests use this action. The
# Android caller serializes it with Start. Existing/ambiguous controller files
# block tests conservatively; diagnosis itself never deletes stale evidence.
guard_test_mode() {
    guard_compatibility_check || { printf '%s:%s\n' "$COMPAT_VERDICT" "$COMPAT_REASON"; return 0; }
    if [ -e "$PID_FILE" ] || [ -d "$LOCK_DIR" ]; then
        printf 'CAPABILITY_MISSING:CONTROLLER_NOT_STOPPED\n'; return 0
    fi
    if [ "$TSWT" = -1 ] || [ "$APPLYING" != 0 ] || [ "$ANIMATION" != 0 ]; then
        printf 'CAPABILITY_MISSING:NATIVE_STATE_NOT_SETTLED\n'; return 0
    fi
    if [ "$1" = test-ink ]; then compatibility_key=$PROFILE_ENTER_KEY
    else compatibility_key=$PROFILE_EXIT_KEY; fi
    input keyevent "$compatibility_key" >/dev/null 2>&1 || {
        printf 'PRIVILEGE_UNAVAILABLE:NATIVE_COMMAND_DENIED\n'; return 0;
    }
    printf 'COMMAND_SENT:%s\n' "$PROFILE_ID"
}

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
    EXIT_DEADLINE=0
    DAEMON_STARTED=
    DAEMON_BOOT=
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
    exit_remaining=0
    if [ "$EXIT_DEADLINE" -gt 0 ]; then
        exit_remaining=$((EXIT_DEADLINE - NOW))
        [ "$exit_remaining" -ge 0 ] || exit_remaining=0
    fi
    printf '%s:%s:%s:%s:%s:%s:%s:%s:%s:%s\n' "$PHASE" "$remaining" \
        "$SESSION_START" "$DEADLINE" "$NOW" "$PHYSICAL" "$ERROR_CODE" "$NEXT_DURATION" \
        "$EXIT_DEADLINE" "$exit_remaining"
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

ANCHOR_ICON_LARGE='data:base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAMAAABg3Am1AAAAYFBMVEXp9Pe14Oyktb9Txe9Sos9vjqNgd4gvgrknbqFDXGw4SVgUTX4TMUsKITYSGB0SFhsRFhsRFhoQFx0KFyMRFRsRFRoRFRkQFRsQFRoQFRkLFR0TFBYQFBkPFBkMExkHDxec783+AAAEPklEQVR42mVWi7arKAzlISAC1uKFix2r//+XsxO07axhnUMR2SHZeSm2UretNUyYS8HPTsvSaKIlfvBPi4LNKvb+QKexvNYFm+Xz1DqgNsglQB+FBPU3BaJwWbneVP7bSscJ3ttpr9x3Aft8XgK2+/09rhtwdK+XCji6LDkvz/YF7D+AfSu/MqDLkmcay1K+gI9c8V8RpM2c59e5nueMS8rPFThdtl2w8P3ehKl0flLKTEDkBaTv/d0l8gfA+iz5yOukhFLDtGL9p/0avhPgx6CNrI1pVTK4YFRKce12VOaVXLyLy56L9pzXwYxSusEpNZohvRfSHLbV1lkXpFxld8MzZT78MGhjNCY7aDcd+dbpEkl++CjVFgCc004Jrcw4jC4cc3cHux4ksUoMIAVLzufkRugjoZgbxzGcOZfuHVIK2pBK+03D8k4+hOCGwWiCYe3jsUDfT2jt39BAMM1nEEpKKfrAchD+nCkWe+TXy2gAKomZj2D6UMZiGOtsgNkUjpQM0Hu//dAo8uZ3hN7OWQtHe89WQCU6+YQXWC/xdTqIW15wVgyjkxA+hhhTOpikSmdxR0MC7YVTjEiq7fl8v9YUnTDGxXXNjUO2didw2okehYWN2NoTiUAA5e2YEEvneTwI0k34Bh+hCiUZAPOawqDEQIA4TfHYHhT19U6g935H00LhDECKoxRG6HhaReN8P8r/UhQ7Sz4zIHSBFgoRPq7Kz7MX6p+6XArhnttx5fFONq4zWYAL4AJcYXxKk5Lm9fjmNwMQJeVxRKlDAq10gRkMrgAgzlENqbLh7QMAqwjsOBgZ4AYnpdFaW6npBi/tGN9Lu2sLVw3imAFKj3QBfjWSQuopWWk8ASC0VjooOPPxmAHwykjnJGYaBpnqpTETAE/yRKkcGtANJZNVmqx0WktEHQ1r5eDgwtgBT4bAcajIlVg9onMeukiI5GEnMgVPLu0LR9OlUuOqgOSJo5uUVh7nBh+ctsAbZGBcObQL1w7RiwJoQkVKCH8cg1yFhdbeDsG7dHJdLj2exE9Nml/RDWYaNOlFADcZyH/lheObIUWU9mkLCI6gvXdWwdWTtd55q1EGlso6dKJE7QlNiGVJg52GcfJKmAljBG8OSdGJr4Uagtiu5gIYEUX0OOuNiZMfAz2g+HGX4yqAG678IUBbcgrIyjDCEo8UTWsM6e9fzncmBhMBGvkOZiF/3udBKReccTie83G8+TUnBHy3lU9TJHYb7qBulSE5ri/OJ4Rd5S7MnfKHVtaTC9AfQP6+6Hj3ENWH1n/wLD42MxONquITmU2iO+G1d4eLe2ooVwfrhYSLNMdlY1t5vf2MW6XWetOD7ZXcyhOJedatfBp8r0u3gHZtXXFzF7xyH+h7naX66Yt3eegNt3w/IPoHyBfQPl8szN9Wyk+bYtsLEwAbSueTkqL2NsAthz9ivuYyBbT1L9pmrZ0wPl2AAAAAAElFTkSuQmCC'
ANCHOR_ICON_SMALL='data:base64,iVBORw0KGgoAAAANSUhEUgAAACQAAAAkCAYAAADhAJiYAAABS0lEQVR42mNgGAWjYJgBRkoN+P///3+4YYyMFJvHRC3HYOPTxUH///8P+w8BO3A5Egq20SXKSAkFcqKQabAlanIc9IaE0Eynqev/kwd20CSE/v//H0+mP97SMoRW/P///yeOkPiGhX+ebonv////kTgcFjlgOeL///8v0BzzYSAdgzWEoHJL0cXo4aCDSHZeR3PQ/////5/5//9/CtUdBTMcTSyJiOyeAlU7hRRHEZvtjZF8H8bAwNBHhB5xKC1I68JwHzGlIVTvUzThJFpUHY4kVMJSUO5VelSu7xgYGP5gEb+MRew5lP5LjSh7BA3uz2TWZbdokdO2oVlyl4Aj/qHzaVHukBpCl8gJGVLS0FcofQFHu2gnAwPDFgYGhtlQvi6tS+Z/BEJkPr4igFaOSvr//38ggdJ6PpL6rIGoZGEh82i0mzsKRsFQAAChzOuhleDHFAAAAABJRU5ErkJggg=='

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
    if [ "$EXIT_DEADLINE" -gt 0 ]; then
        notification_exit_remaining=$((EXIT_DEADLINE - NOW))
        [ "$notification_exit_remaining" -ge 0 ] || notification_exit_remaining=0
        notification_key=$notification_key:exit:$((notification_exit_remaining / 60))
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
    if [ "$EXIT_DEADLINE" -gt 0 ]; then
        if [ "$notification_language" = ar ]; then
            notification_text="الخروج خلال $((notification_exit_remaining / 60)) دقيقة و$((notification_exit_remaining % 60)) ثانية. الالتزام مستمر حتى ذلك الوقت."
        else
            notification_text="Exit in $((notification_exit_remaining / 60))m $((notification_exit_remaining % 60))s. Your commitment stays active until then."
        fi
    fi
    cmd notification post -S bigtext -t "$notification_title" -I "$ANCHOR_ICON_LARGE" -i "$ANCHOR_ICON_SMALL" guard_commit "$notification_text" >/dev/null 2>&1
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

guard_command_gate() {
    # PROFILE_* is loaded once and remains immutable in this controller process.
    # A report from an earlier check cannot authorize this command.
    guard_identity_matches || { guard_fail "$COMPAT_REASON"; return 1; }
    gate_switch_node=$SWITCH_NODE
    guard_discover || { guard_fail PHYSICAL_SWITCH_UNAVAILABLE; return 1; }
    if [ -n "$gate_switch_node" ] && [ "$gate_switch_node" != "$SWITCH_NODE" ]; then
        guard_fail PHYSICAL_SWITCH_CHANGED; return 1
    fi
    gate_snapshot=$TSWT:$INK:$BOOK:$APPLYING:$ANIMATION
    if guard_native_read; then :
    else
        gate_native_result=$?
        if [ "$gate_native_result" = 2 ]; then guard_fail NATIVE_PRESET_MISMATCH
        else guard_fail NATIVE_STATE_READ_FAILED; fi
        return 1
    fi
    if [ "$gate_snapshot" != "$TSWT:$INK:$BOOK:$APPLYING:$ANIMATION" ] ||
        [ "$TSWT" = -1 ] || [ "$APPLYING" != 0 ] || [ "$ANIMATION" != 0 ]; then
        NATIVE_SIGNATURE=; STABLE=0
        return 2 # A fresh transition must settle in the ordinary tick loop.
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
    case "$key" in "$PROFILE_ENTER_KEY"|"$PROFILE_EXIT_KEY") ;;
        *) guard_fail INVALID_NATIVE_COMMAND; return 1 ;; esac
    if guard_command_gate; then :
    else
        gate_result=$?
        [ "$gate_result" = 2 ] && return 0
        return 1
    fi
    guard_clock || { guard_fail CLOCK_UNAVAILABLE; return 1; }
    guard_exit_due || return 1
    if [ "$PHASE" = RESTORING ] && { [ "$purpose" = ENTER ] || [ "$purpose" = RESET ]; }; then
        return 0
    fi
    # The raw reader may have advanced while the compatibility observations ran.
    guard_physical_read || return 1
    if [ "$purpose" = EXIT ] && [ "$RESTORE_REASON" != STOP ] && [ "$PHYSICAL" = ON ]; then
        PHASE=EXTENDED; RESTORE_REASON=; RECOVERY_AT=0; return 0
    fi
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
    if [ "$1" = STOP ]; then
        EXIT_DEADLINE=0
        guard_clear_duration || return 1
    fi
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
    printf 'ERROR:0:0:0:%s:%s:%s:%s:0:0\n' "$NOW" "$PHYSICAL" "$1" "$NEXT_DURATION"
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

guard_stop_transition() {
    # Internal shutdown and an elapsed public request share the proven native
    # restoration path. A pending request alone never sets STOP_REQUESTED.
    STOP_REQUESTED=1
    EXIT_DEADLINE=0
    guard_clear_duration || return 1
    case "$PHASE" in
      WAIT_SWITCH|IDLE|WAIT_OFF) PHASE=STOPPED ;;
      RESTORING) RESTORE_REASON=STOP ;;
      STOPPED) ;;
      *) guard_begin_restore STOP ;;
    esac
}

guard_exit_due() {
    if [ "$EXIT_DEADLINE" -gt 0 ] && [ "$NOW" -ge "$EXIT_DEADLINE" ]; then
        guard_log "exit wait complete exit_deadline=$EXIT_DEADLINE commitment_deadline=$DEADLINE"
        guard_stop_transition || return 1
    fi
}

guard_stop_request() {
    [ -r "$STOP_REQUEST" ] || return 0
    IFS=: read -r stop_request_id stop_request_boot stop_request_pid stop_request_started stop_request_action < "$STOP_REQUEST" || return 0
    case "$stop_request_id" in ''|*[!0-9-]*) rm -f "$STOP_REQUEST"; return 0 ;; esac
    if [ "$stop_request_boot" != "$DURATION_BOOT" ] ||
        [ "$stop_request_boot" != "$DAEMON_BOOT" ] ||
        [ "$stop_request_pid" != "$$" ] || [ "$stop_request_started" != "$DAEMON_STARTED" ]; then
        stop_reply=$(guard_duration_error STOP_STALE)
    elif [ "$stop_request_action" != request-stop ] && [ "$stop_request_action" != cancel-stop ]; then
        stop_reply=$(guard_duration_error STOP_INVALID)
    else
        # Expiry wins over a cancellation received in the same poll. Do not
        # let COMMITTED become EXTENDED before honoring a pending exit.
        guard_exit_due || return 1
        if [ "$stop_request_action" = cancel-stop ]; then
            if [ "$STOP_REQUESTED" = 1 ] || [ "$PHASE" = RESTORING ] ||
                [ "$PHASE" = STOPPED ] || [ "$PHASE" = ERROR ]; then
                stop_reply=$(guard_duration_error STOP_TOO_LATE)
            else
                [ "$EXIT_DEADLINE" = 0 ] || guard_log "exit wait cancelled request=$stop_request_id"
                EXIT_DEADLINE=0
                guard_publish || return 1
                stop_reply=$(guard_state)
            fi
        else
            case "$PHASE" in
              STARTING|COMMITTED)
                if [ "$STOP_REQUESTED" != 1 ] && [ "$EXIT_DEADLINE" = 0 ]; then
                    EXIT_DEADLINE=$((NOW + EXIT_DELAY))
                    if [ "$PHASE" = COMMITTED ] && [ "$DEADLINE" -lt "$EXIT_DEADLINE" ]; then
                        EXIT_DEADLINE=$DEADLINE
                    fi
                    guard_log "exit wait requested exit_deadline=$EXIT_DEADLINE request=$stop_request_id"
                fi
                guard_exit_due || return 1 ;;
              *) guard_stop_transition || return 1 ;;
            esac
            guard_publish || return 1
            stop_reply=$(guard_state)
        fi
    fi
    printf '%s:%s\n' "$stop_request_id" "$stop_reply" > "$STOP_ACK.tmp" &&
        mv "$STOP_ACK.tmp" "$STOP_ACK" || { guard_fail STOP_ACK_FAILED; return 1; }
    # A slow publication may outlive the caller's timeout. Remove only the
    # consumed request, never a newer caller's replacement mailbox entry.
    if [ -r "$STOP_REQUEST" ]; then
        IFS=: read -r consumed_stop_id rest < "$STOP_REQUEST"
        [ "$consumed_stop_id" != "$stop_request_id" ] || rm -f "$STOP_REQUEST"
    fi
}

guard_change_stop() (
    guard_duration_load || { guard_duration_error CLOCK_UNAVAILABLE; return 0; }
    stop_action=$1
    guard_process_info "$$" || { guard_duration_error PROCESS_IDENTITY_UNAVAILABLE; return 0; }
    case "$process_started" in ''|*[!0-9]*) guard_duration_error PROCESS_IDENTITY_UNAVAILABLE; return 0 ;; esac
    case "$process_boot" in ''|*[!a-zA-Z0-9-]*) guard_duration_error PROCESS_IDENTITY_UNAVAILABLE; return 0 ;; esac
    stop_claim=$STOP_COMMAND_LOCK/claim.$$.$process_started.$process_boot
    stop_request_token=$$-$process_started-$NOW
    mkdir "$STOP_COMMAND_LOCK" 2>/dev/null || [ -d "$STOP_COMMAND_LOCK" ] || {
        guard_duration_error STOP_WRITE_FAILED; return 0;
    }
    mkdir "$stop_claim" 2>/dev/null || { guard_duration_error STOP_BUSY; return 0; }
    trap 'rmdir "$stop_claim" 2>/dev/null; rmdir "$STOP_COMMAND_LOCK" 2>/dev/null || :' EXIT
    trap 'exit 1' TERM INT HUP
    for stop_other in "$STOP_COMMAND_LOCK"/claim.*; do
        [ -e "$stop_other" ] || continue
        [ "$stop_other" != "$stop_claim" ] || continue
        stop_identity=${stop_other##*/claim.}
        stop_owner_pid=${stop_identity%%.*}
        stop_owner_tail=${stop_identity#*.}
        stop_owner_started=${stop_owner_tail%%.*}
        stop_owner_boot=${stop_owner_tail#*.}
        case "$stop_owner_pid" in ''|*[!0-9]*) guard_duration_error STOP_BUSY; return 0 ;; esac
        case "$stop_owner_started" in ''|*[!0-9]*) guard_duration_error STOP_BUSY; return 0 ;; esac
        case "$stop_owner_boot" in ''|*[!a-zA-Z0-9-]*) guard_duration_error STOP_BUSY; return 0 ;; esac
        if [ "$stop_identity" != "$stop_owner_pid.$stop_owner_started.$stop_owner_boot" ] ||
            guard_duration_owner_live "$stop_owner_pid" "$stop_owner_started" "$stop_owner_boot"; then
            guard_duration_error STOP_BUSY; return 0
        fi
        rmdir "$stop_other" 2>/dev/null || { guard_duration_error STOP_BUSY; return 0; }
    done
    if ! guard_live_pid; then
        if [ "$stop_action" = request-stop ]; then guard_stop
        else guard_status; fi
        return
    fi
    stop_target_pid=$live_pid
    stop_target_started=$process_started
    stop_target_boot=$process_boot
    rm -f "$STOP_ACK"
    printf '%s:%s:%s:%s:%s\n' "$stop_request_token" "$stop_target_boot" "$stop_target_pid" "$stop_target_started" "$stop_action" > "$STOP_REQUEST.tmp" &&
        mv "$STOP_REQUEST.tmp" "$STOP_REQUEST" || { guard_duration_error STOP_WRITE_FAILED; return 0; }
    stop_request_wait=0
    while [ "$stop_request_wait" -le 5 ]; do
        if [ -r "$STOP_ACK" ]; then
            IFS=: read -r stop_ack_token stop_ack_status < "$STOP_ACK"
            if [ "$stop_ack_token" = "$stop_request_token" ]; then
                printf '%s\n' "$stop_ack_status"
                return 0
            fi
        fi
        [ "$stop_request_wait" -lt 5 ] || break
        sleep 1
        stop_request_wait=$((stop_request_wait + 1))
    done
    if [ -r "$STOP_REQUEST" ]; then
        IFS=: read -r pending_stop_token rest < "$STOP_REQUEST"
        [ "$pending_stop_token" != "$stop_request_token" ] || rm -f "$STOP_REQUEST"
    fi
    guard_duration_error STOP_TIMEOUT
)

guard_duration() {
    DURATION=$NEXT_DURATION
    # Consume the one-shot choice before issuing a native command. Neither a
    # later app launch nor a recovery command may renew it or the deadline.
    guard_clear_duration
}

guard_tick() {
    guard_stability
    guard_exit_due || return 1
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
            if [ "$EXIT_DEADLINE" -gt 0 ] && [ "$DEADLINE" -lt "$EXIT_DEADLINE" ]; then
                EXIT_DEADLINE=$DEADLINE
            fi
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
    guard_identity_matches || { guard_fail "$COMPAT_REASON"; return 1; }
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

guard_controller_absent() {
    # False means possibly live as well as confirmed live. Failed /proc access
    # is not evidence that it is safe to delete/replace a controller.
    [ -e "$PID_FILE" ] || return 0
    [ -r "$PID_FILE" ] || return 1
    presence_record=$(cat "$PID_FILE" 2>/dev/null) || return 1
    presence_pid=${presence_record%%:*}
    case "$presence_pid" in ''|*[!0-9]*) return 1 ;; esac
    presence_rest=${presence_record#*:}
    presence_started=${presence_rest%%:*}
    presence_boot=${presence_rest#*:}
    presence_token_valid=0
    printf '%s\n' "$presence_record" | grep -Eq '^[0-9]+:[0-9]+:[a-zA-Z0-9-]+$' && presence_token_valid=1
    presence_actual_boot=$(cat "$PROC_ROOT/sys/kernel/random/boot_id" 2>/dev/null)
    if [ "$presence_token_valid" = 1 ] && [ -n "$presence_actual_boot" ] &&
        [ "$presence_boot" != "$presence_actual_boot" ]; then return 0; fi
    if [ ! -d "$PROC_ROOT/$presence_pid" ] && [ -d "$PROC_ROOT/1" ] &&
        ! kill -0 "$presence_pid" 2>/dev/null; then return 0; fi
    guard_process_info "$presence_pid" || return 1
    presence_command=$(tr '\000' '\n' < "$PROC_ROOT/$presence_pid/cmdline" 2>/dev/null)
    [ -n "$presence_command" ] || return 1
    if ! printf '%s\n' "$presence_command" | grep -Fx "$SCRIPT_PATH" >/dev/null; then return 0; fi
    if [ "$presence_token_valid" = 1 ] &&
        { [ "$presence_started" != "$process_started" ] || [ "$presence_boot" != "$process_boot" ]; }; then return 0; fi
    return 1
}

guard_status() {
    if guard_live_pid; then
        guard_clock || { printf 'ERROR:0:0:0:0:UNKNOWN:CLOCK_UNAVAILABLE:300:0:0\n'; return 0; }
        if [ -r "$STATE_FILE" ]; then
            IFS=: read -r status_phase status_remaining status_start status_deadline status_at status_physical status_error < "$STATE_FILE"
            case "$status_at" in ''|*[!0-9]*) status_at=0 ;; esac
            if [ $((NOW - status_at)) -le 15 ] && [ "$NOW" -ge "$status_at" ]; then
                cat "$STATE_FILE"
                return 0
            fi
        fi
        printf 'ERROR:0:0:0:%s:UNKNOWN:DAEMON_UNRESPONSIVE:%s:0:0\n' "$NOW" "$NEXT_DURATION"
        return 0
    fi
    if ! guard_controller_absent; then
        printf 'ERROR:0:0:0:0:UNKNOWN:CONTROLLER_IDENTITY_UNAVAILABLE:%s:0:0\n' "$NEXT_DURATION"
        return 0
    fi
    if [ -r "$STATE_FILE" ] && grep -q '^ERROR:' "$STATE_FILE"; then cat "$STATE_FILE"; return 0; fi
    printf 'STOPPED:0:0:0:0:UNKNOWN::%s:0:0\n' "$NEXT_DURATION"
}

guard_stop() {
    if ! guard_live_pid; then
        if ! guard_controller_absent; then
            printf 'ERROR:0:0:0:0:UNKNOWN:CONTROLLER_IDENTITY_UNAVAILABLE:%s:0:0\n' "$NEXT_DURATION"
            return 1
        fi
        # Acknowledge a stale error without touching native mode or another PID.
        PHASE=STOPPED
        ERROR_CODE=
        SESSION_START=0
        DEADLINE=0
        EXIT_DEADLINE=0
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
    printf 'ERROR:0:0:0:0:UNKNOWN:STOP_TIMEOUT:%s:0:0\n' "$NEXT_DURATION"
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
    # These branches intentionally precede every stateful daemon operation.
    case "${1:-start}" in
      check-compatibility) guard_compatibility_report; return 0 ;;
      test-ink|test-normal) guard_test_mode "$1"; return 0 ;;
    esac
    guard_clock || { printf 'ERROR:0:0:0:0:UNKNOWN:CLOCK_UNAVAILABLE:300:0:0\n'; return 1; }
    guard_init
    guard_duration_load || { printf 'ERROR:0:0:0:0:UNKNOWN:CLOCK_UNAVAILABLE:300:0:0\n'; return 1; }
    case "${1:-start}" in
      status) guard_status; return ;;
      stop) guard_stop; return ;;
      request-stop|cancel-stop) guard_change_stop "$1"; return ;;
      set-duration)
        [ "$#" = 2 ] || { guard_duration_error DURATION_INVALID; return 0; }
        guard_set_duration "$2"; return ;;
      start) ;;
      *) printf 'Usage: nxtpaper_guard.sh [start|status|request-stop|cancel-stop|stop|set-duration <seconds>]\n'; return 2 ;;
    esac
    if guard_live_pid; then guard_status; return; fi
    if ! guard_controller_absent; then
        printf 'ERROR:0:0:0:0:UNKNOWN:CONTROLLER_IDENTITY_UNAVAILABLE:%s:0:0\n' "$NEXT_DURATION"
        return 1
    fi
    if ! mkdir "$LOCK_DIR" 2>/dev/null; then
        sleep 1
        if guard_live_pid; then guard_status; return; fi
        guard_monitor_cleanup
        rm -f "$LOCK_DIR/input.fifo" "$PHYSICAL_FILE" "$PHYSICAL_FILE.tmp" \
            "$GETEVENT_PID_FILE" "$GETEVENT_PID_FILE.tmp" "$READER_PID_FILE" \
            "$READER_PID_FILE.tmp" "$WRITER_PID_FILE" "$WRITER_PID_FILE.tmp" "$MONITOR_ERROR_FILE"
        rmdir "$LOCK_DIR" 2>/dev/null
        mkdir "$LOCK_DIR" 2>/dev/null || { printf 'ERROR:0:0:0:0:UNKNOWN:START_LOCK_FAILED:300:0:0\n'; return 1; }
    fi
    OWN_LOCK=1
    rm -f "$DURATION_REQUEST" "$DURATION_ACK" "$STOP_REQUEST" "$STOP_ACK"
    trap 'STOP_REQUESTED=1' TERM INT
    trap '' HUP
    if ! guard_tools; then :
    elif ! guard_process_identity "$$"; then ERROR_CODE=PROCESS_IDENTITY_UNAVAILABLE
    elif ! { DAEMON_STARTED=$process_started; DAEMON_BOOT=$process_boot;
        printf '%s:%s:%s\n' "$$" "$DAEMON_STARTED" "$DAEMON_BOOT" > "$PID_FILE"; }; then ERROR_CODE=PID_WRITE_FAILED
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
        guard_exit_due || break
        if [ "$STOP_REQUESTED" = 1 ]; then
            guard_stop_transition || break
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
            guard_clock || { ERROR_CODE=CLOCK_UNAVAILABLE; break; }
            guard_stop_request || break
            sleep 1
            continue
        fi
        guard_clock && guard_physical_read || { ERROR_CODE=PHYSICAL_STATE_INVALID; break; }
        case "$PHASE" in
          WAIT_SWITCH|IDLE|WAIT_OFF) guard_duration_load || { ERROR_CODE=CLOCK_UNAVAILABLE; break; } ;;
        esac
        guard_tick || { [ -n "$ERROR_CODE" ] || ERROR_CODE=NATIVE_COMMAND_FAILED; break; }
        guard_duration_request || break
        # Native calls and publication can take time. Cancellation must be
        # judged against fresh uptime rather than the preceding tick's time.
        guard_clock || { ERROR_CODE=CLOCK_UNAVAILABLE; break; }
        guard_stop_request || break
        guard_publish || break
        sleep 1
    done
    if [ -n "$ERROR_CODE" ]; then guard_clear_duration || :; EXIT_DEADLINE=0; PHASE=ERROR; fi
    guard_publish
    guard_state
    guard_remove_lock
    [ "$PHASE" != ERROR ]
}

# Host regressions source these exact functions with fake Android commands.
if [ "${NXTPAPER_GUARD_SOURCE_ONLY:-0}" != 1 ]; then
    guard_main "$@"
fi
