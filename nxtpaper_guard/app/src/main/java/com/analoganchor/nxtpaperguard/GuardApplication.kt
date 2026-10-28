package com.analoganchor.nxtpaperguard

import android.app.Application
import rikka.shizuku.Shizuku

class GuardApplication : Application() {
    private val binderReady = Shizuku.OnBinderReceivedListener {
        if (GuardRuntime.isAuthorized()) {
            // An explicit delayed stop leaves desired=false while the daemon
            // keeps enforcing. Querying status can reconcile a saved Continue
            // request without automatically restarting a completed stop.
            val action = if (GuardRuntime.desired(this)) GuardRuntime.Action.START else GuardRuntime.Action.STATUS
            GuardRuntime.runAsync(this, action) { result ->
                if (result.error != null && GuardRuntime.desired(this)) BootReminder.show(this)
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        Shizuku.addBinderReceivedListenerSticky(binderReady)
    }
}
