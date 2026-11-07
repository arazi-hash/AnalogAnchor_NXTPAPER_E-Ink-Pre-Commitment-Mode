package com.analoganchor.nxtpaperguard;

import android.view.KeyEvent;

/** Read-only app_process entry point for the PC observer. No Context or writes. */
public final class KeySymbolProbe {
    private KeySymbolProbe() {}

    public static void main(String[] args) {
        int enter = KeyEvent.keyCodeFromString("KEYCODE_TSWT_ON");
        int exit = KeyEvent.keyCodeFromString("KEYCODE_TSWT_OFF");
        System.out.println("symbol_on=KEYCODE_TSWT_ON");
        System.out.println("enter_key=" + enter);
        System.out.println("resolved_on=" + KeyEvent.keyCodeToString(enter));
        System.out.println("symbol_off=KEYCODE_TSWT_OFF");
        System.out.println("exit_key=" + exit);
        System.out.println("resolved_off=" + KeyEvent.keyCodeToString(exit));
    }
}
