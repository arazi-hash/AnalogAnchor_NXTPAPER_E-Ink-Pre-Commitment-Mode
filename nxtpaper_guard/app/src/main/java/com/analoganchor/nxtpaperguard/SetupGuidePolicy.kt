package com.analoganchor.nxtpaperguard

/** A reading acknowledgement is separate from device qualification. */
internal class SetupGuidePolicy(var handledThisVisit: Boolean = false) {
    fun shouldShow(required: Boolean, blocked: Boolean, key: String, acknowledgedKey: String?): Boolean =
        required && !blocked && !handledThisVisit && key.isNotBlank() && key != acknowledgedKey

    fun shown() { handledThisVisit = true }
    fun beginVisit() { handledThisVisit = false }

    companion object {
        fun restoreHandled(savedHandled: Boolean, savedVisit: String?, currentVisit: String): Boolean =
            savedHandled && currentVisit.isNotBlank() && savedVisit == currentVisit

        fun acknowledgementKey(build: String, bindingDigest: String?): String =
            if (bindingDigest?.matches(Regex("[0-9a-f]{64}")) == true) "binding:$bindingDigest" else "build:$build"
    }
}
