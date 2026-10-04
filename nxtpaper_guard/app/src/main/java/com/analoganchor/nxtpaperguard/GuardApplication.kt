package com.analoganchor.nxtpaperguard

import android.app.Application
import rikka.shizuku.Shizuku

class GuardApplication : Application() {
    private val binderReady = Shizuku.OnBinderReceivedListener {
        if (GuardRuntime.desired(this) && GuardRuntime.isAuthorized()) {
            GuardRuntime.runAsync(this, GuardRuntime.Action.START) { result ->
                if (result.error != null) BootReminder.show(this)
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        Shizuku.addBinderReceivedListenerSticky(binderReady)
    }
}
