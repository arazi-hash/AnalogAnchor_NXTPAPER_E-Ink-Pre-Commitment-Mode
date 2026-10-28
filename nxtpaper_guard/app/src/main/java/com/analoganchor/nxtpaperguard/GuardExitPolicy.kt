package com.analoganchor.nxtpaperguard

/** A cancellation intent applies only to the exact live daemon and exit request. */
internal object GuardExitPolicy {
    enum class CancelRecovery { CLEAR, CONFIRM, RETRY }

    private val continuingPhases = setOf("STARTING", "COMMITTED")

    fun continuationConfirmed(phase: String, exitDeadline: Long): Boolean =
        phase in continuingPhases && exitDeadline == 0L

    fun stopAcknowledged(phase: String, exitDeadline: Long): Boolean =
        phase in setOf("STOPPED", "RESTORING") || (phase in continuingPhases && exitDeadline > 0L)

    // Without the command acknowledgement, RESTORING might belong to ordinary
    // expiry, which returns to monitoring rather than stopping the daemon.
    fun stopConfirmedFromStatus(phase: String, exitDeadline: Long): Boolean =
        phase == "STOPPED" || (phase in continuingPhases && exitDeadline > 0L)

    fun cancelRecovery(
        phase: String,
        exitDeadline: Long,
        savedIdentity: String,
        liveIdentity: String?,
        savedExitDeadline: Long
    ): CancelRecovery = when {
        savedIdentity != liveIdentity || savedExitDeadline <= 0L -> CancelRecovery.CLEAR
        phase !in continuingPhases -> CancelRecovery.CLEAR
        exitDeadline == 0L -> CancelRecovery.CONFIRM
        exitDeadline == savedExitDeadline -> CancelRecovery.RETRY
        else -> CancelRecovery.CLEAR
    }
}
