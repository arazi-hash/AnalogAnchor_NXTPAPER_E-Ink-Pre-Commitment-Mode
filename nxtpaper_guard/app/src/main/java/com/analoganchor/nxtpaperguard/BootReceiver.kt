package com.analoganchor.nxtpaperguard

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action !in setOf(Intent.ACTION_BOOT_COMPLETED, Intent.ACTION_MY_PACKAGE_REPLACED)) return
        if (!GuardRuntime.desired(context)) return
        // Keep the broadcast short. Shizuku binder delivery (GuardApplication) or
        // opening the activity resumes protection without a long boot broadcast.
        BootReminder.show(context)
    }
}

object BootReminder {
    private const val CHANNEL = "guard_recovery"
    private const val ID = 9978

    fun show(context: Context) {
        if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(
                context, Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED) return
        val manager = context.getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= 26) manager.createNotificationChannel(
            NotificationChannel(CHANNEL, context.getString(R.string.boot_channel_name), NotificationManager.IMPORTANCE_DEFAULT)
        )
        val open = PendingIntent.getActivity(context, 0, Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        manager.notify(ID, NotificationCompat.Builder(context, CHANNEL)
            .setSmallIcon(R.drawable.ic_guard_lock)
            .setContentTitle(context.getString(R.string.boot_title))
            .setContentText(context.getString(R.string.boot_short))
            .setStyle(NotificationCompat.BigTextStyle().bigText(
                context.getString(R.string.boot_detail)
            ))
            .setContentIntent(open)
            .setAutoCancel(true)
            .build())
    }

    fun cancel(context: Context) = context.getSystemService(NotificationManager::class.java).cancel(ID)
}
