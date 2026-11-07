package com.analoganchor.nxtpaperguard

/** Main-thread queue: polling must never consume an owner's confirmation or cancellation. */
internal class SetupCommandQueue {
    private var running: GuardRuntime.SetupAction? = null
    private val pending = ArrayDeque<GuardRuntime.SetupAction>()
    val cancelling: Boolean get() = running == GuardRuntime.SetupAction.ABORT || GuardRuntime.SetupAction.ABORT in pending
    val ownerWorkPending: Boolean get() =
        (running != null && running !in setOf(GuardRuntime.SetupAction.CHECK, GuardRuntime.SetupAction.STATUS)) ||
            pending.any { it !in setOf(GuardRuntime.SetupAction.CHECK, GuardRuntime.SetupAction.STATUS) }

    /** Returns work to dispatch now. Null means it was queued or a redundant observation was coalesced. */
    fun request(action: GuardRuntime.SetupAction): GuardRuntime.SetupAction? {
        if (running == null) {
            running = action
            return action
        }
        when (action) {
            GuardRuntime.SetupAction.STATUS -> Unit
            GuardRuntime.SetupAction.CHECK -> if (running == GuardRuntime.SetupAction.STATUS && pending.isEmpty()) pending.addLast(action)
            GuardRuntime.SetupAction.ABORT -> {
                // Cancellation also invalidates a stale consent dialog's queued Start/Qualify.
                pending.clear()
                if (running != GuardRuntime.SetupAction.ABORT) pending.addLast(action)
            }
            else -> if (!cancelling && action != running && action !in pending) {
                pending.remove(GuardRuntime.SetupAction.CHECK)
                pending.addLast(action)
            }
        }
        return null
    }

    fun finished(): GuardRuntime.SetupAction? {
        check(running != null)
        running = pending.removeFirstOrNull()
        return running
    }
}
